# IndusPilot Negotiation State Machine Specification

## 1. Overview

The IndusPilot Autonomous Supplier Negotiation Engine is governed by a rigorous 16-state deterministic finite state machine (FSM). This structure guarantees full audit compliance, prevents illegal skips, ensures human commercial oversight, and handles deadlocks, concessions, and formal agreement concluding.

---

## 2. State Definitions

The 16 states are defined in `NegotiationState`:

| # | State Enum Value | Category | Description |
|---|---|---|---|
| 1 | `DRAFT` | Initiation | Session created; initial baseline parameters recorded. |
| 2 | `OPPORTUNITY_IDENTIFIED` | Initiation | Potential landed savings or pricing benchmark spread verified. |
| 3 | `STRATEGY_SELECTED` | Preparation | Negotiation lever formulated (`VOLUME_COMMITMENT`, `BENCHMARK_PARITY`, etc.). |
| 4 | `COUNTEROFFER_GENERATED` | Drafting | Agent has drafted formal counteroffer text in chosen language. |
| 5 | `AWAITING_APPROVAL` | Governance | Mandatory human gate; message draft queued for buyer sign-off. |
| 6 | `APPROVED_TO_SEND` | Governance | Human buyer authorized message transmission without alteration or with edits. |
| 7 | `MESSAGE_TRANSMITTED` | Transmission | Communication dispatched via API, simulated channel, or email integration. |
| 8 | `SUPPLIER_READ` | Telemetry | Supplier acknowledged receipt or opened electronic counteroffer. |
| 9 | `RESPONSE_RECEIVED` | Feedback | Inbound response captured and ready for term extraction. |
| 10 | `CONCESSION_OFFERED` | Evaluation | Supplier decreased unit price, waived freight, or accelerated terms. |
| 11 | `COUNTER_REJECTED` | Evaluation | Supplier refused proposed target price and held firm or counter-offered high. |
| 12 | `MULTI_ROUND_ACTIVE` | Iteration | Additional negotiation round required (up to round ceiling). |
| 13 | `ACCEPTANCE_PROPOSED` | Decision | Favorable terms arrived within target band; buyer agent recommends closing. |
| 14 | `AGREEMENT_REACHED` | Terminal | Formal contract terms concluded; creates quotation revision `v2`. |
| 15 | `ESCALATED_TO_HUMAN` | Terminal / Exception | Impasse reached or deviation exceeds policy limits; manual override required. |
| 16 | `ABANDONED_WALKAWAY` | Terminal | Supplier firm at unviable price exceeding walk-away ceiling; session closed. |

---

## 3. Transition Rules & Sequence Diagram

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> OPPORTUNITY_IDENTIFIED: Identify Price / Benchmark Delta
    OPPORTUNITY_IDENTIFIED --> STRATEGY_SELECTED: Select 1 of 5 Commercial Strategies
    STRATEGY_SELECTED --> COUNTEROFFER_GENERATED: AI Drafts Multilingual Message
    COUNTEROFFER_GENERATED --> AWAITING_APPROVAL: Mandatory Commercial Gate
    
    AWAITING_APPROVAL --> APPROVED_TO_SEND: Human Approver Sign-off
    AWAITING_APPROVAL --> STRATEGY_SELECTED: Re-strategize / Change Target
    AWAITING_APPROVAL --> ABANDONED_WALKAWAY: Cancel Session
    
    APPROVED_TO_SEND --> MESSAGE_TRANSMITTED: Transmit via Webhook / Sandbox
    MESSAGE_TRANSMITTED --> SUPPLIER_READ: Receipt Logged
    SUPPLIER_READ --> RESPONSE_RECEIVED: Supplier Reply Captured
    
    RESPONSE_RECEIVED --> CONCESSION_OFFERED: Rate Decreased / Terms Improved
    RESPONSE_RECEIVED --> COUNTER_REJECTED: Rate Maintained / Rejected
    
    CONCESSION_OFFERED --> ACCEPTANCE_PROPOSED: Rate <= Target + Tolerance
    CONCESSION_OFFERED --> MULTI_ROUND_ACTIVE: Rate > Target but Improving
    
    COUNTER_REJECTED --> MULTI_ROUND_ACTIVE: Rounds < Max Rounds
    COUNTER_REJECTED --> ABANDONED_WALKAWAY: Price > Walkaway Ceiling
    COUNTER_REJECTED --> ESCALATED_TO_HUMAN: Deadline Critical / Shortage High
    
    MULTI_ROUND_ACTIVE --> COUNTEROFFER_GENERATED: Increment Round & Formulate
    
    ACCEPTANCE_PROPOSED --> AGREEMENT_REACHED: Conclude Agreement & Revise Quote
    ACCEPTANCE_PROPOSED --> ESCALATED_TO_HUMAN: High-Value Order Sign-off
    
    AGREEMENT_REACHED --> [*]
    ABANDONED_WALKAWAY --> [*]
    ESCALATED_TO_HUMAN --> [*]
```

---

## 4. State Validation Enforcement

The Python state transition controller validates every status mutation:
- Any jump directly from `COUNTEROFFER_GENERATED` to `MESSAGE_TRANSMITTED` without passing `AWAITING_APPROVAL` and `APPROVED_TO_SEND` raises an `InvalidStateTransitionError`.
- Transitioning to `AGREEMENT_REACHED` requires `current_offered_price <= max_walkaway_price`.
- Terminal states (`AGREEMENT_REACHED`, `ABANDONED_WALKAWAY`, `ESCALATED_TO_HUMAN`) cannot transition back to active rounds without an administrative re-opening action.

