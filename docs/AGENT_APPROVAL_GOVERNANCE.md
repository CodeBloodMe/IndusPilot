# IndusPilot Commercial Approval Governance & Human-in-the-Loop Policies

## Principles of Agentic Governance

In manufacturing procurement, autonomous software cannot be permitted to execute unilateral commercial actions that commit company funds, alter inventory valuation, or issue legally binding quotes to clients without human executive oversight.

IndusPilot enforces **Human-in-the-Loop (HITL) Checkpoints** directly into its LangGraph state graph.

```mermaid
sequenceDiagram
    autonumber
    actor User as Factory Owner / Lead
    participant Copilot as IndusPilot Supervisor
    participant Graph as LangGraph Engine
    participant Checkpoint as HITL Governance Gate
    participant DB as System Database

    User->>Copilot: "Prepare order for 500 brackets and draft quote"
    Copilot->>Graph: Execute End-to-End Workflow
    Graph->>Graph: Explode BOM & Net Stock
    Graph->>Graph: Solve OR-Tools MILP
    Graph->>Graph: Compute 14-Factor Production Cost
    Graph->>Graph: Draft Customer Quote ($P_{\text{sell}} \ge P_{\text{cost}}$)
    
    Graph->>Checkpoint: Intercept Sensitive Mutation / External Dispatch
    Checkpoint->>DB: Create PendingAgentAction (Status: PENDING)
    Checkpoint->>Copilot: Pause Execution (Status: AWAITING_APPROVAL)
    Copilot-->>User: Present Summary Card & Authorization Banner
    
    alt User Clicks Authorize
        User->>Copilot: POST /api/v1/copilot/actions/{id}/approve
        Copilot->>DB: Mark Action APPROVED & Finalize Quote
        Copilot-->>User: Dispatch Confirmed (Status: COMPLETED)
    else User Clicks Reject
        User->>Copilot: POST /api/v1/copilot/actions/{id}/reject
        Copilot->>DB: Mark Action REJECTED with Reason
        Copilot-->>User: Action Cancelled (Status: CANCELLED)
    end
```

---

## Operations Requiring Mandatory Executive Approval

1. **Customer Quotation Dispatch (`EXTERNAL_ACTION`)**:
   - Any quote dispatched to an external client requires approval from the Commercial Director or Plant Head.
2. **Loss-Making or Below-Target Margin Contracts**:
   - If projected gross margin falls below the executive minimum threshold (e.g., $< 15\%$) or break-even price, the quotation is automatically locked in `APPROVAL_REQUIRED` state.
3. **Purchase Requisition Commitment (`SENSITIVE_MUTATION`)**:
   - Committing funds above ₹1,00,000 for raw material purchase orders requires confirmation.
4. **Physical Inventory Stock Overrides (`SENSITIVE_MUTATION`)**:
   - Manual inventory adjustments require written audit rationale.

---

## Audit Ledger Schema (`pending_agent_actions`)

```sql
CREATE TABLE pending_agent_actions (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES agent_runs(id),
    organization_id VARCHAR NOT NULL REFERENCES organisations(id),
    conversation_id VARCHAR,
    action_type VARCHAR(100) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    proposed_payload_json JSON NOT NULL,
    financial_impact_summary VARCHAR(255),
    status VARCHAR(50) DEFAULT 'PENDING',
    decision_by VARCHAR(100),
    decision_reason TEXT,
    decided_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

