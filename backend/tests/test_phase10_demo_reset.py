import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.entities import (
    Base, Organization, User, Material, Inventory,
    CopilotConversation, CopilotMessage, Supplier
)
from app.services.seed_data import seed_induspilot_demonstration_data

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

def test_demo_seed_baseline(test_db):
    """Verify initial seeding creates expected demonstration baseline."""
    res = seed_induspilot_demonstration_data(test_db, force_reset=False)
    assert res["status"] == "SUCCESS"
    assert res["suppliers_count"] == 10
    assert res["materials_count"] == 20

    # Verify MAT-SS-304 inventory baseline
    mat = test_db.query(Material).filter_by(code="MAT-SS-304").first()
    assert mat is not None
    inv = test_db.query(Inventory).filter_by(material_id=mat.id).first()
    assert inv is not None
    assert inv.current_stock == 400.0
    assert inv.reserved_stock == 50.0
    assert inv.safety_stock == 50.0

def test_demo_seed_idempotency(test_db):
    """Calling seed without force_reset on an already seeded DB is idempotent and returns ALREADY_SEEDED."""
    res1 = seed_induspilot_demonstration_data(test_db, force_reset=False)
    assert res1["status"] == "SUCCESS"

    res2 = seed_induspilot_demonstration_data(test_db, force_reset=False)
    assert res2["status"] == "ALREADY_SEEDED"

def test_demo_reset_restores_baseline_and_cleans_mutations(test_db):
    """Mutating state then calling force_reset restores clean demo baseline."""
    seed_induspilot_demonstration_data(test_db, force_reset=False)

    # Mutate inventory
    mat = test_db.query(Material).filter_by(code="MAT-SS-304").first()
    inv = test_db.query(Inventory).filter_by(material_id=mat.id).first()
    inv.current_stock = 150.0
    inv.reserved_stock = 100.0

    # Add a demo copilot conversation
    org = test_db.query(Organization).filter_by(slug="apex-precision-fab").first()
    conv = CopilotConversation(
        id="conv-demo-mutation-test",
        organization_id=org.id,
        user_id="user_rajesh_sharma",
        title="Test Ephemeral Chat"
    )
    test_db.add(conv)
    test_db.commit()

    assert inv.current_stock == 150.0
    assert test_db.query(CopilotConversation).filter_by(id="conv-demo-mutation-test").first() is not None

    # Reset demo data
    res_reset = seed_induspilot_demonstration_data(test_db, force_reset=True)
    assert res_reset["status"] == "SUCCESS"

    # Verify inventory is restored to baseline
    mat_after = test_db.query(Material).filter_by(code="MAT-SS-304").first()
    inv_after = test_db.query(Inventory).filter_by(material_id=mat_after.id).first()
    assert inv_after.current_stock == 400.0
    assert inv_after.reserved_stock == 50.0

    # Verify mutation conversation is removed
    assert test_db.query(CopilotConversation).filter_by(id="conv-demo-mutation-test").first() is None

def test_demo_reset_preserves_non_demo_tenant_data(test_db):
    """force_reset strictly deletes demo org data without harming any other tenant's records."""
    seed_induspilot_demonstration_data(test_db, force_reset=False)

    # Create a non-demo tenant with supplier and material
    other_org = Organization(
        id="org_defense_private_tenant",
        name="AeroDefense India Pvt Ltd",
        slug="aerodefense-india",
        manufacturing_category="Aerospace & Defense",
        currency="INR"
    )
    test_db.add(other_org)
    test_db.flush()

    other_user = User(
        id="user_defense_admin",
        organization_id=other_org.id,
        email="admin@aerodefense.in",
        hashed_password="hashed_pw",
        full_name="Col. Vikram Singh",
        role="ADMIN"
    )
    test_db.add(other_user)

    other_mat = Material(
        id="mat_titanium_spec_01",
        organization_id=other_org.id,
        code="MAT-TI-6AL4V",
        name="Titanium Ti-6Al-4V Grade 5",
        category="Aerospace Alloys",
        grade="Grade 5",
        unit="kg"
    )
    test_db.add(other_mat)

    other_sup = Supplier(
        id="sup_aero_specialty",
        organization_id=other_org.id,
        name="Hindustan Aeronautics Alloy Div",
        contact_person="Ramesh Gupta",
        email="ramesh@hal.in",
        phone="+91-80-2222-3333",
        city="Bengaluru",
        state="Karnataka"
    )
    test_db.add(other_sup)
    test_db.commit()

    # Now execute force_reset for demo data
    res_reset = seed_induspilot_demonstration_data(test_db, force_reset=True)
    assert res_reset["status"] == "SUCCESS"

    # Verify the non-demo tenant and its entities are 100% intact
    assert test_db.query(Organization).filter_by(id="org_defense_private_tenant").first() is not None
    assert test_db.query(User).filter_by(id="user_defense_admin").first() is not None
    assert test_db.query(Material).filter_by(id="mat_titanium_spec_01").first() is not None
    assert test_db.query(Supplier).filter_by(id="sup_aero_specialty").first() is not None
