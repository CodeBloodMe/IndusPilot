import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.entities import (
    CopilotConversation, CopilotMessage, AgentRun, AgentRunStep,
    AgentToolCall, PendingAgentAction, Organization, User, Material, Product
)
from app.agents.tools.registry import CentralToolRegistry, ToolPermissionTier
from app.agents.llm_provider import DemoNLUProvider
from app.core.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


# ============================================================================
# 1. CONVERSATION MANAGEMENT & MULTI-TENANCY TESTS
# ============================================================================

def test_copilot_conversation_lifecycle(client):
    """Test full CRUD lifecycle of a Copilot conversation."""
    # 1. Create Conversation
    create_res = client.post("/api/v1/copilot/conversations", json={
        "title": "Industrial Bracket Procurement Sprint"
    })
    assert create_res.status_code in (200, 201)
    conv = create_res.json()
    assert conv["title"] == "Industrial Bracket Procurement Sprint"
    conv_id = conv["id"]
    assert conv["is_archived"] is False

    # 2. List Conversations
    list_res = client.get("/api/v1/copilot/conversations")
    assert list_res.status_code == 200
    conv_list = list_res.json()
    assert any(c["id"] == conv_id for c in conv_list)

    # 3. Get Conversation Details
    get_res = client.get(f"/api/v1/copilot/conversations/{conv_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["id"] == conv_id
    assert "messages" in details
    assert len(details["messages"]) >= 1

    # 4. Update Conversation Title
    patch_res = client.patch(f"/api/v1/copilot/conversations/{conv_id}", json={
        "title": "Renamed: Industrial Bracket Q2 Sprint",
        "is_archived": False
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Renamed: Industrial Bracket Q2 Sprint"

    # 5. Delete (Archive) Conversation
    del_res = client.delete(f"/api/v1/copilot/conversations/{conv_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 6. Verify conversation excluded from default list
    list_after_res = client.get("/api/v1/copilot/conversations")
    assert not any(c["id"] == conv_id for c in list_after_res.json())


def test_copilot_multi_tenant_isolation(client, db_session):
    """Verify that conversations created by Org A cannot be accessed by Org B."""
    # Ensure tenant organizations and users exist
    org_a = db_session.query(Organization).filter(Organization.id == "org-tenant-alpha").first()
    if not org_a:
        org_a = Organization(id="org-tenant-alpha", name="Org Alpha", slug="org-alpha-slug")
        db_session.add(org_a)
    user_a = db_session.query(User).filter(User.id == "user_tenant_alpha").first()
    if not user_a:
        user_a = User(id="user_tenant_alpha", organization_id="org-tenant-alpha", email="a@alpha.com", hashed_password="pw", full_name="User Alpha")
        db_session.add(user_a)

    org_b = db_session.query(Organization).filter(Organization.id == "org-tenant-beta").first()
    if not org_b:
        org_b = Organization(id="org-tenant-beta", name="Org Beta", slug="org-beta-slug")
        db_session.add(org_b)
    user_b = db_session.query(User).filter(User.id == "user_tenant_beta").first()
    if not user_b:
        user_b = User(id="user_tenant_beta", organization_id="org-tenant-beta", email="b@beta.com", hashed_password="pw", full_name="User Beta")
        db_session.add(user_b)
    db_session.commit()

    # Create conversation under Org A
    org_a_res = client.post(
        "/api/v1/copilot/conversations",
        json={"title": "Org A Secret Procurement"},
        headers={"Authorization": "Bearer user_tenant_alpha", "X-Organization-ID": "org-tenant-alpha"}
    )
    assert org_a_res.status_code in (200, 201)
    conv_a_id = org_a_res.json()["id"]

    # Attempt to retrieve under Org B -> should return 403 or 404
    org_b_get = client.get(
        f"/api/v1/copilot/conversations/{conv_a_id}",
        headers={"Authorization": "Bearer user_tenant_beta", "X-Organization-ID": "org-tenant-beta"}
    )
    assert org_b_get.status_code in (403, 404)


# ============================================================================
# 2. MULTI-AGENT SUPERVISOR & INTENT ROUTING TESTS
# ============================================================================

def test_copilot_end_to_end_manufacturing_workflow(client):
    """
    Test Master User Workflow:
    'I have received an order for 500 stainless steel industrial brackets.
     Check inventory, find required materials, optimise procurement within 5 lakh
     and calculate profit at 20% margin.'
    """
    # Create fresh conversation
    conv_res = client.post("/api/v1/copilot/conversations", json={
        "title": "End-to-End Bracket Order Processing"
    })
    conv_id = conv_res.json()["id"]

    # Send multi-step instruction
    msg_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "I have received an order for 500 stainless steel industrial brackets. "
                   "Check inventory, find required materials, optimise procurement within 5 lakh "
                   "and calculate expected profit at a 20% gross margin."
    })
    assert msg_res.status_code == 200
    data = msg_res.json()

    # 1. Message assertions
    msg = data["message"]
    assert msg["role"] == "assistant"
    assert "Supervisor Agent" in msg["agent_name"]
    assert "Complete Manufacturing & Procurement Workflow Executed" in msg["content"]
    assert "1,050.0 kg" in msg["content"] # gross required
    assert "750.0 kg" in msg["content"]   # net shortage
    assert "Apex Steel & Alloys" in msg["content"]

    # 2. Structured Card assertions
    card = msg["structured_data"]
    assert card is not None
    assert card["card_type"] == "END_TO_END_SUMMARY"
    assert card["production_quantity"] == 500.0
    assert card["shortage_kg"] == 750.0
    assert card["procurement_cost"] > 0
    assert card["gross_margin_pct"] == 20.0
    assert card["projected_profit"] > 0

    # 3. Governance / Approval Assertion
    assert msg["requires_human_approval"] is True
    assert msg["pending_action"] is not None
    assert msg["pending_action"]["action_type"] in ("DISPATCH_CUSTOMER_QUOTE", "DISPATCH_CUSTOMER_QUOTATION")

    # 4. Telemetry Run assertions
    run = data["run"]
    assert run["status"] in ("AWAITING_APPROVAL", "COMPLETED")
    assert len(run["selected_agents"]) >= 5

    # 5. Step Trace assertions
    trace = data["step_trace"]
    assert len(trace) >= 5
    agent_names_invoked = [s["agent_name"] for s in trace]
    assert "Supervisor Agent" in agent_names_invoked
    assert "Inventory and BOM Agent" in agent_names_invoked
    assert "Supplier Intelligence Agent" in agent_names_invoked
    assert "Procurement Optimisation Agent" in agent_names_invoked
    assert "Manufacturing Cost Agent" in agent_names_invoked
    assert "Customer Quotation Agent" in agent_names_invoked


def test_copilot_supplier_comparison_intent(client):
    """Test routing to Supplier Intelligence Agent for quotation evaluation."""
    res = client.post("/api/v1/copilot/chat", json={
        "query": "Compare supplier quotations and identify the top candidate for SS304"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Supplier Intelligence Agent" in data["agent_name"]
    assert "Apex Steel & Alloys" in data["response_text"]
    assert data["data"] is not None
    assert data["data"]["card_type"] == "SUPPLIER_COMPARISON"


def test_copilot_inventory_shortage_intent(client):
    """Test routing to Procurement Planning / Inventory Agent for stock audit."""
    res = client.post("/api/v1/copilot/chat", json={
        "query": "Check inventory shortage and available stock for 500 brackets"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Procurement Planning Agent" in data["agent_name"]
    assert "750.0 kg" in data["response_text"]
    assert data["data"]["card_type"] == "INVENTORY_SHORTAGE"


def test_copilot_manufacturing_costing_intent(client):
    """Test routing to Manufacturing Cost Agent for 14-factor breakdown."""
    res = client.post("/api/v1/copilot/chat", json={
        "query": "Calculate 14-factor manufacturing cost breakdown for 500 units"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Manufacturing Cost Agent" in data["agent_name"]
    assert "Total Audited Cost" in data["response_text"]
    assert "Unit Break-Even Cost" in data["response_text"]
    assert data["data"]["card_type"] == "COST_BREAKDOWN"


def test_copilot_procurement_optimization_intent(client):
    """Test routing to Procurement Optimisation Agent for Google OR-Tools allocation."""
    res = client.post("/api/v1/copilot/chat", json={
        "query": "Optimize procurement allocation for stainless steel using OR-Tools MILP solver"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Procurement Optimisation Agent" in data["agent_name"]
    assert "Google OR-Tools" in data["response_text"]
    assert data["data"]["card_type"] == "PROCUREMENT_PLAN"


def test_copilot_multilingual_hindi_and_hinglish(client):
    """Test NLU handling of Hindi and Hinglish queries."""
    # Hindi Stock Query
    hi_res = client.post("/api/v1/copilot/chat", json={
        "query": "500 bracket ke liye stock check karo aur shortage batao kitna material chahiye"
    })
    assert hi_res.status_code == 200
    assert "Procurement Planning Agent" in hi_res.json()["agent_name"]
    assert "750.0 kg" in hi_res.json()["response_text"]

    # Hinglish Supplier Query
    hinglish_res = client.post("/api/v1/copilot/chat", json={
        "query": "Stainless steel 304 ke liye kaunsa supplier best hai compare karke batao"
    })
    assert hinglish_res.status_code == 200
    assert "Supplier Intelligence Agent" in hinglish_res.json()["agent_name"]
    assert "Apex Steel" in hinglish_res.json()["response_text"]


# ============================================================================
# 3. TYPED TOOL REGISTRY & PERMISSION GOVERNANCE TESTS
# ============================================================================

def test_tool_registry_schemas_and_permissions(db_session):
    """Verify tool registry maintains typed schemas and 4 permission tiers."""
    registry = CentralToolRegistry()
    tools = registry.list_tools()

    assert len(tools) >= 20

    tiers = {t.permission_tier for t in tools}
    assert ToolPermissionTier.READ_ONLY in tiers
    assert ToolPermissionTier.DRAFT_CREATION in tiers
    assert ToolPermissionTier.SENSITIVE_MUTATION in tiers
    assert ToolPermissionTier.EXTERNAL_ACTION in tiers

    # Verify specific tool permission tiers
    list_quotes_tool = registry.get_tool("list_supplier_quotations")
    assert list_quotes_tool is not None
    assert list_quotes_tool.permission_tier == ToolPermissionTier.READ_ONLY

    cost_tool = registry.get_tool("calculate_manufacturing_cost")
    assert cost_tool is not None
    assert cost_tool.permission_tier == ToolPermissionTier.READ_ONLY

    quote_draft_tool = registry.get_tool("create_customer_quotation_draft")
    assert quote_draft_tool is not None
    assert quote_draft_tool.permission_tier == ToolPermissionTier.DRAFT_CREATION

    inv_adj_tool = registry.get_tool("adjust_inventory_level")
    assert inv_adj_tool is not None
    assert inv_adj_tool.permission_tier == ToolPermissionTier.SENSITIVE_MUTATION


def test_tool_registry_input_validation_and_execution(db_session):
    """Test tool execution validation for valid vs invalid inputs."""
    registry = CentralToolRegistry()

    # 1. Valid execution
    valid_res = registry.execute_tool(
        name="list_supplier_quotations",
        arguments={"status": "VERIFIED"},
        org_id="00000000-0000-0000-0000-000000000001",
        db=db_session
    )
    assert valid_res["success"] is True
    assert "quotations" in valid_res["data"]

    # 2. Missing tool execution
    missing_res = registry.execute_tool(
        name="non_existent_tool_xyz",
        arguments={},
        org_id="00000000-0000-0000-0000-000000000001",
        db=db_session
    )
    assert missing_res["success"] is False
    assert "not registered" in missing_res["error"]

    # 3. Invalid argument types
    invalid_res = registry.execute_tool(
        name="calculate_bom_requirements",
        arguments={"product_id": "P1", "production_quantity": -50.0}, # negative quantity rejected
        org_id="00000000-0000-0000-0000-000000000001",
        db=db_session
    )
    assert invalid_res["success"] is False


# ============================================================================
# 4. HUMAN APPROVAL CHECKPOINT & GOVERNANCE TESTS
# ============================================================================

def test_copilot_approval_checkpoint_and_execution(client, db_session):
    """Test human approval lifecycle for sensitive agent actions."""
    # 1. Trigger action creation via multi-step workflow
    conv_res = client.post("/api/v1/copilot/conversations", json={
        "title": "Approval Testing Session"
    })
    conv_id = conv_res.json()["id"]

    msg_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "Prepare full order workflow for 500 brackets and draft customer quote"
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()["message"]
    assert msg_data["requires_human_approval"] is True
    pending_action = msg_data["pending_action"]
    assert pending_action is not None
    action_id = pending_action["id"]

    # 2. Verify Action in Pending List
    pending_list = client.get("/api/v1/copilot/actions?status=PENDING")
    assert pending_list.status_code == 200
    actions = pending_list.json()
    assert any(a["id"] == action_id for a in actions)

    # 3. Approve Action
    approve_res = client.post(f"/api/v1/copilot/actions/{action_id}/approve", json={
        "reason": "Verified landed cost savings and margin targets. Approved for commercial dispatch.",
        "approver_name": "Admin / Plant Head"
    })
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "APPROVED"
    assert approved_data["decision_by"] == "Admin / Plant Head"
    assert approved_data["execution_result"] is not None

    # 4. Reject Action test with a new action
    action_record = PendingAgentAction(
        run_id=msg_data["run_id"],
        organization_id=settings.DEFAULT_ORGANIZATION_ID,
        conversation_id=conv_id,
        action_type="DISPATCH_CUSTOMER_QUOTE",
        agent_name="Customer Quotation Agent",
        title="Test Quote Action",
        description="Draft customer quotation ready for commercial dispatch",
        proposed_payload_json={"quote_id": "cq-test-01"},
        status="PENDING"
    )
    db_session.add(action_record)
    db_session.commit()

    reject_res = client.post(f"/api/v1/copilot/actions/{action_record.id}/reject", json={
        "reason": "Margin must be at least 25% for this customer. Revise costing."
    })
    assert reject_res.status_code == 200
    rejected_data = reject_res.json()
    assert rejected_data["status"] == "REJECTED"
    assert "25%" in rejected_data["rejection_reason"]


# ============================================================================
# 5. CONTEXT RETENTION ACROSS TURNS TESTS
# ============================================================================

def test_copilot_context_retention_across_turns(client):
    """
    Test that parameters established in Turn 1 (quantity 500, SS304 bracket)
    are retained in Turn 2 when the user asks a follow-up query.
    """
    conv_res = client.post("/api/v1/copilot/conversations", json={
        "title": "Context Continuity Test"
    })
    conv_id = conv_res.json()["id"]

    # Turn 1: Establish context
    t1_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "Check inventory shortage for 500 stainless steel industrial brackets"
    })
    assert t1_res.status_code == 200
    assert "750.0 kg" in t1_res.json()["message"]["content"]

    # Turn 2: Follow-up query without re-stating product
    t2_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "Calculate manufacturing costing breakdown for this batch"
    })
    assert t2_res.status_code == 200
    msg2 = t2_res.json()["message"]
    assert "500 Units" in msg2["content"]
    assert "Direct Raw Material" in msg2["content"]
    assert msg2["structured_data"]["card_type"] == "COST_BREAKDOWN"


# ============================================================================
# 6. TELEMETRY & RUN TRACE TESTS
# ============================================================================

def test_copilot_run_telemetry_and_events(client):
    """Test retrieving execution step traces and tool telemetry by run ID."""
    conv_res = client.post("/api/v1/copilot/conversations", json={
        "title": "Telemetry Sprint"
    })
    conv_id = conv_res.json()["id"]

    msg_res = client.post(f"/api/v1/copilot/conversations/{conv_id}/messages", json={
        "content": "Compare supplier quotations for SS304"
    })
    assert msg_res.status_code == 200
    run_id = msg_res.json()["message"]["run_id"]
    assert run_id is not None

    # Retrieve Run Trace
    run_res = client.get(f"/api/v1/copilot/runs/{run_id}")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["id"] == run_id
    assert run_data["status"] == "COMPLETED"
    assert len(run_data["steps"]) >= 2

    # Retrieve Run Step Events
    events_res = client.get(f"/api/v1/copilot/runs/{run_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 2
    assert any((e.get("step_type") or e.get("event_type")) in ("PLANNING", "TOOL_EXECUTION", "SYNTHESIS") for e in events)
