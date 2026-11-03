"""
Phase 10 — Tenant Security Hardening & Membership Validation Test Suite
Verifies genuine multi-tenant authorization, preventing raw unauthenticated header spoofing
and enforcing strict membership verification across API endpoints, copilot actions,
conversations, and multi-agent tools.

Test Matrix (9 Adversarial Security Tests):
1. Alpha user accesses Alpha resources -> 200 OK
2. Beta user accesses Beta resources -> 200 OK
3. Alpha user attempts to access Beta resources -> 403 Forbidden
4. Beta user attempts to access Alpha resources -> 403 Forbidden
5. Unauthenticated user spoofing X-Organization-ID header -> 401 Unauthorized
6. Cross-tenant approval attempt -> 403 Forbidden
7. Cross-tenant copilot conversation access -> 403 Forbidden
8. Cross-tenant tool execution / data retrieval -> blocked / strictly isolated
9. Missing or invalid auth credentials -> 401 Unauthorized
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database.session import SessionLocal
from app.models.entities import (
    Organization, User, Material, Inventory, AgentRun,
    PendingAgentAction, CopilotConversation
)
from app.agents.tools.registry import ToolRegistry


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def tenants_setup():
    """Sets up two isolated tenant organizations with distinct owners and resources."""
    db = SessionLocal()

    # 1. Tenant Alpha
    org_alpha = db.query(Organization).filter(Organization.id == "org_alpha_test").first()
    if not org_alpha:
        org_alpha = Organization(
            id="org_alpha_test",
            name="Alpha Aerospace Ltd",
            slug="alpha-aerospace-test"
        )
        db.add(org_alpha)

    user_alpha = db.query(User).filter(User.id == "user_alpha_test").first()
    if not user_alpha:
        user_alpha = User(
            id="user_alpha_test",
            organization_id="org_alpha_test",
            email="owner@alpha-aero.com",
            hashed_password="hashed_pw_alpha_2026",
            full_name="Col. Alpha Sharma",
            role="OWNER",
            is_active=True
        )
        db.add(user_alpha)

    mat_alpha = db.query(Material).filter(Material.id == "mat_alpha_titanium").first()
    if not mat_alpha:
        mat_alpha = Material(
            id="mat_alpha_titanium",
            organization_id="org_alpha_test",
            code="MAT-TI-6AL4V",
            name="Titanium Aerospace Alloy",
            grade="Ti-6Al-4V",
            category="Raw Materials",
            unit="kg",
            density_g_cm3=4.43
        )
        db.add(mat_alpha)

    # 2. Tenant Beta
    org_beta = db.query(Organization).filter(Organization.id == "org_beta_test").first()
    if not org_beta:
        org_beta = Organization(
            id="org_beta_test",
            name="Beta Marine Engineering",
            slug="beta-marine-test"
        )
        db.add(org_beta)

    user_beta = db.query(User).filter(User.id == "user_beta_test").first()
    if not user_beta:
        user_beta = User(
            id="user_beta_test",
            organization_id="org_beta_test",
            email="director@beta-marine.com",
            hashed_password="hashed_pw_beta_2026",
            full_name="Capt. Beta Deshmukh",
            role="OWNER",
            is_active=True
        )
        db.add(user_beta)

    mat_beta = db.query(Material).filter(Material.id == "mat_beta_bronze").first()
    if not mat_beta:
        mat_beta = Material(
            id="mat_beta_bronze",
            organization_id="org_beta_test",
            code="MAT-BRZ-NAB",
            name="Nickel Aluminium Bronze",
            grade="C95800",
            category="Raw Materials",
            unit="kg",
            density_g_cm3=7.64
        )
        db.add(mat_beta)

    db.commit()
    db.close()

    yield {
        "org_alpha": "org_alpha_test",
        "org_beta": "org_beta_test",
        "user_alpha": "user_alpha_test",
        "user_beta": "user_beta_test",
        "mat_alpha": "mat_alpha_titanium",
        "mat_beta": "mat_beta_bronze"
    }


def test_1_alpha_user_accesses_alpha_resources(client: TestClient, tenants_setup):
    """Test 1: User Alpha successfully accesses Alpha's resources."""
    headers = {
        "Authorization": f"Bearer {tenants_setup['user_alpha']}",
        "X-Organization-ID": tenants_setup["org_alpha"]
    }
    res = client.get("/api/v1/materials", headers=headers)
    assert res.status_code == 200
    data = res.json()
    items = data if isinstance(data, list) else data.get("items", [])
    codes = [m["code"] for m in items]
    assert "MAT-TI-6AL4V" in codes
    assert "MAT-BRZ-NAB" not in codes


def test_2_beta_user_accesses_beta_resources(client: TestClient, tenants_setup):
    """Test 2: User Beta successfully accesses Beta's resources."""
    headers = {
        "Authorization": f"Bearer {tenants_setup['user_beta']}",
        "X-Organization-ID": tenants_setup["org_beta"]
    }
    res = client.get("/api/v1/materials", headers=headers)
    assert res.status_code == 200
    data = res.json()
    items = data if isinstance(data, list) else data.get("items", [])
    codes = [m["code"] for m in items]
    assert "MAT-BRZ-NAB" in codes
    assert "MAT-TI-6AL4V" not in codes


def test_3_alpha_user_denied_beta_resources(client: TestClient, tenants_setup):
    """Test 3: User Alpha attempting to access Beta's organization receives 403 Forbidden."""
    headers = {
        "Authorization": f"Bearer {tenants_setup['user_alpha']}",
        "X-Organization-ID": tenants_setup["org_beta"]
    }
    res = client.get("/api/v1/materials", headers=headers)
    assert res.status_code == 403
    assert "not an authorized member" in res.json().get("detail", "")


def test_4_beta_user_denied_alpha_resources(client: TestClient, tenants_setup):
    """Test 4: User Beta attempting to access Alpha's organization receives 403 Forbidden."""
    headers = {
        "Authorization": f"Bearer {tenants_setup['user_beta']}",
        "X-Organization-ID": tenants_setup["org_alpha"]
    }
    res = client.get("/api/v1/materials", headers=headers)
    assert res.status_code == 403
    assert "not an authorized member" in res.json().get("detail", "")


def test_5_unauthenticated_header_spoofing_rejected(client: TestClient, tenants_setup):
    """Test 5: An unauthenticated caller passing an arbitrary X-Organization-ID is rejected with 401 Unauthorized."""
    headers = {
        "X-Organization-ID": tenants_setup["org_beta"]
    }
    res = client.get("/api/v1/materials", headers=headers)
    assert res.status_code == 401
    assert "Authentication credentials required" in res.json().get("detail", "")


import uuid


def test_6_cross_tenant_approval_rejected(client: TestClient, tenants_setup, db_session: Session):
    """Test 6: User Beta cannot approve a pending commercial action belonging to Alpha."""
    uid = uuid.uuid4().hex[:8]
    run_alpha = AgentRun(
        id=f"run_alpha_{uid}",
        organization_id=tenants_setup["org_alpha"],
        objective="Confidential aerospace bracket supply approval",
        status="RUNNING"
    )
    db_session.add(run_alpha)

    action_alpha = PendingAgentAction(
        id=f"act_alpha_{uid}",
        run_id=run_alpha.id,
        organization_id=tenants_setup["org_alpha"],
        action_type="DISPATCH_CUSTOMER_QUOTE",
        agent_name="Customer Quotation Agent",
        title="Alpha Defense Quotation",
        description="Confidential aerospace bracket supply",
        proposed_payload_json={"val": 1000000},
        status="PENDING"
    )
    db_session.add(action_alpha)
    db_session.commit()

    # User Beta tries to approve Alpha's action
    headers_beta = {
        "Authorization": f"Bearer {tenants_setup['user_beta']}",
        "X-Organization-ID": tenants_setup["org_beta"]
    }
    res = client.post(
        f"/api/v1/copilot/actions/{action_alpha.id}/approve",
        json={"reason": "Malicious unauthorized authorization attempt"},
        headers=headers_beta
    )
    assert res.status_code == 403
    assert "Cross-tenant action forbidden" in res.json().get("detail", "")


def test_7_cross_tenant_conversation_access_rejected(client: TestClient, tenants_setup, db_session: Session):
    """Test 7: User Beta cannot view or post to an Alpha conversation thread."""
    uid = uuid.uuid4().hex[:8]
    conv_alpha = CopilotConversation(
        id=f"conv_alpha_{uid}",
        organization_id=tenants_setup["org_alpha"],
        title="Classified Alpha Metallurgy Consultation"
    )
    db_session.add(conv_alpha)
    db_session.commit()

    headers_beta = {
        "Authorization": f"Bearer {tenants_setup['user_beta']}",
        "X-Organization-ID": tenants_setup["org_beta"]
    }

    # Attempt to read conversation
    res_get = client.get(
        f"/api/v1/copilot/conversations/{conv_alpha.id}",
        headers=headers_beta
    )
    assert res_get.status_code == 403
    assert "Cross-tenant access forbidden" in res_get.json().get("detail", "")

    # Attempt to post message to conversation
    res_post = client.post(
        f"/api/v1/copilot/conversations/{conv_alpha.id}/messages",
        json={"content": "Malicious eavesdropping injection"},
        headers=headers_beta
    )
    assert res_post.status_code == 403
    assert "Cross-tenant access forbidden" in res_post.json().get("detail", "")


def test_8_cross_tenant_tool_data_isolation(tenants_setup, db_session: Session):
    """Test 8: Multi-agent ToolRegistry queries execute strictly scoped to org_id, never leaking rival data."""
    # Ensure inventory items exist for each tenant
    inv_a = db_session.query(Inventory).filter(Inventory.material_id == tenants_setup["mat_alpha"]).first()
    if not inv_a:
        inv_a = Inventory(
            id=f"inv_alpha_{uuid.uuid4().hex[:8]}",
            organization_id=tenants_setup["org_alpha"],
            material_id=tenants_setup["mat_alpha"],
            current_stock=150.0,
            reserved_stock=10.0,
            warehouse_location="ALPHA-WH-1"
        )
        db_session.add(inv_a)

    inv_b = db_session.query(Inventory).filter(Inventory.material_id == tenants_setup["mat_beta"]).first()
    if not inv_b:
        inv_b = Inventory(
            id=f"inv_beta_{uuid.uuid4().hex[:8]}",
            organization_id=tenants_setup["org_beta"],
            material_id=tenants_setup["mat_beta"],
            current_stock=250.0,
            reserved_stock=20.0,
            warehouse_location="BETA-WH-1"
        )
        db_session.add(inv_b)
    db_session.commit()

    tools = ToolRegistry()

    # Check inventory for Alpha
    alpha_res = tools.execute_tool(
        name="check_inventory",
        arguments={},
        org_id=tenants_setup["org_alpha"],
        db=db_session
    )
    assert alpha_res["success"] is True
    alpha_codes = [i["material_code"] for i in alpha_res["data"]["inventory"]]
    assert "MAT-TI-6AL4V" in alpha_codes
    assert "MAT-BRZ-NAB" not in alpha_codes

    # Check inventory for Beta
    beta_res = tools.execute_tool(
        name="check_inventory",
        arguments={},
        org_id=tenants_setup["org_beta"],
        db=db_session
    )
    assert beta_res["success"] is True
    beta_codes = [i["material_code"] for i in beta_res["data"]["inventory"]]
    assert "MAT-BRZ-NAB" in beta_codes
    assert "MAT-TI-6AL4V" not in beta_codes


def test_9_invalid_or_missing_auth_credentials_rejected(client: TestClient, tenants_setup):
    """Test 9: Invalid tokens or inactive users receive 401 or 403."""
    res_bad = client.get(
        "/api/v1/materials",
        headers={"Authorization": "Bearer non_existent_token_9999"}
    )
    assert res_bad.status_code == 401
    assert "Invalid authentication credentials" in res_bad.json().get("detail", "")
