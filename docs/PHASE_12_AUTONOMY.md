# MITRA — Phase 12: Human-in-the-Loop & Controlled Autonomy Engine

> **Paytm Build for India AI Hackathon — Delhi Edition**  
> **Track:** Track 3 — Autonomous AI Teammates  
> **Team:** Pica pica  
> **Repository:** `C:\project\Paytm\MITRA`  
> **Phase Status:** COMPLETE & FROZEN  

---

## 1. Architectural Philosophy & Safety Invariants

Phase 12 introduces deterministic, policy-governed autonomy to MITRA while establishing an unbreakable safety baseline:

$$\mathbf{AUTONOMY\ CONTROLS\ APPROVAL\ FLOW.\ AUTONOMY\ NEVER\ OVERRIDES\ SAFETY.}$$

### Non-Negotiable Invariants:
1. **Zero LLM Authority**: Neither the LLM nor AI agents have the authority to grant execution approval, alter policy thresholds, or bypass guardrails. Autonomy verdicts are computed via a 100% deterministic Python rule matrix.
2. **Hard Guardrail BLOCK is Absolute**:
   $$\text{BLOCK} + \text{FULL\_AUTONOMY} \equiv \text{BLOCKED}$$
   Neither merchant human sign-off nor full autonomy policies can ever authorize execution for a `BLOCK` decision.
3. **Escalations Require Human Intervention**:
   $$\text{ESCALATE} + \text{ANY\_MODE} \equiv \text{ESCALATED}$$
   Any decision marked with `ESCALATE` (or risk/budget boundary exceedances) requires human review and is ineligible for autonomous approval.
4. **MODIFY Parameter Invariant**:
   If guardrails clamp an action (e.g. ₹150 discount clamped to ₹100), the autonomy engine strictly evaluates and authorizes the clamped ₹100 parameters. The original unsafe ₹150 is **NEVER executed**.
5. **Cryptographic State Binding**:
   Evaluations are tied to the SHA-256 hash of the proposal and guardrail evaluation. Any mid-flight alteration of proposal parameters raises a `409 Conflict` (Stale Decision/Proposal).
6. **Digital Twin Prototype Boundary**:
   All operations remain in simulation mode (`simulation_mode=True`), operating strictly on simulated digital-twin merchant state.

---

## 2. Autonomy Modes & Policy Engine

MITRA supports three deterministic autonomy operating modes per merchant:

| Mode | Allowed Risk Threshold | Human Sign-off Required? | Description |
| :--- | :---: | :---: | :--- |
| **`APPROVAL_REQUIRED`** *(Default)* | 0.00 | **YES** | Every action requires explicit merchant sign-off before becoming execution-eligible. Default demo mode. |
| **`AUTO_APPROVE_SAFE`** | $\le 0.30$ | **NO** (if all 16 checks pass) | Deterministically auto-approves low-risk campaigns within daily budget and discount constraints. |
| **`FULL_AUTONOMY`** | $\le 0.50$ | **NO** (if all 16 checks pass) | Deterministically auto-approves moderate-risk actions. Hard guardrail `BLOCK` and `ESCALATE` still strictly prevent execution. |

---

## 3. The 16-Point Deterministic Safety Policy

Before granting `AUTO_APPROVED` status, MITRA verifies 16 explicit conditions:

```text
[C1]  Guardrail status is PASS or clamped MODIFY
[C2]  No BLOCK condition in guardrail evaluation
[C3]  No ESCALATE condition requiring manual review
[C4]  Approved action satisfies merchant limits (minimum margin, max discount)
[C5]  Action risk score <= merchant policy risk threshold
[C6]  Target customer count within eligible bounds (1 to 1,000)
[C7]  Campaign cost <= daily budget limit (INR 12,000)
[C8]  Clamped discount <= max discount ceiling (INR 100)
[C9]  Campaign duration <= allowed range (7 days)
[C10] Action type recognized in catalog (OFFER_CAMPAIGN, LOYALTY_PUSH, etc.)
[C11] Proposal integrity valid (action_id and signal_id verified)
[C12] Cryptographic proposal SHA-256 matches evaluation hash
[C13] Merchant ID matches authorized store tenant
[C14] No prior execution has occurred for this decision
[C15] Simulation mode flag is active (True)
[C16] Actor permissions valid for policy level
```

If **any single condition fails**, auto-approval is denied, and the action defaults to `APPROVAL_REQUIRED` or `ESCALATED`.

---

## 4. API Endpoints Reference

### Evaluation & Approval Routes
- `POST /api/autonomy/evaluate/{action_id}`: Evaluates action against merchant policy, returning verdict, passed/failed checks, and risk calculation.
- `GET /api/autonomy/{action_id}`: Retrieves latest autonomy evaluation record.
- `GET /api/autonomy/workflow/{correlation_id}`: Retrieves autonomy evaluation by correlation ID.
- `POST /api/autonomy/{action_id}/approve`: Explicit human merchant sign-off (`HUMAN_APPROVED`).
- `POST /api/autonomy/{action_id}/reject`: Merchant explicit rejection (`REJECTED`), permanently barring execution.

### Merchant Policy Routes
- `GET /api/merchants/{merchant_id}/autonomy`: Fetches current autonomy policy and thresholds.
- `PUT /api/merchants/{merchant_id}/autonomy`: Updates policy mode (`APPROVAL_REQUIRED`, `AUTO_APPROVE_SAFE`, `FULL_AUTONOMY`) and threshold ceilings.

---

## 5. Verification Results

### Backend Pytest Suite
- **Total Tests:** 331 passing (45 dedicated Phase 12 tests)
- **Failures:** 0
- **Regressions:** 0
- **Execution Time:** ~15s - 35s

### Live E2E Scenarios (8/8 PASS)
1. **`APPROVAL_REQUIRED`**: Execution barred until human approval received; execution succeeds upon approval.
2. **`AUTO_APPROVE_SAFE`**: Risk 0.20 $\le$ 0.30 auto-approved; execution eligible immediately.
3. **`FULL_AUTONOMY`**: Risk 0.42 $\le$ 0.50 auto-approved.
4. **`BLOCK OVERRIDES AUTONOMY`**: Severe violation (discount ₹5,000) stays BLOCKED even under `FULL_AUTONOMY`; manual approval rejected with 400 Bad Request.
5. **`MODIFY CLAMPING`**: Proposed ₹150 clamped to ₹100; executed parameters strictly contain ₹100.
6. **`HUMAN REJECTION`**: Merchant explicit rejection marks status `REJECTED` and halts execution.
7. **`ESCALATION`**: Risk 0.85 > 0.50 halts auto-approval even in `FULL_AUTONOMY`.
8. **`STALE STATE`**: Alteration of proposal parameters triggers SHA-256 hash mismatch with 409 Conflict.

### Frontend Quality
- **ESLint:** PASS (0 errors, 0 warnings)
- **Next.js Production Build:** PASS (Static prerendering complete)
