# MITRA — Hackathon Demo Runbook & Judge Presentation Guide

> **Paytm Build for India AI Hackathon – Delhi Edition**  
> **Track:** Track 3 — Autonomous AI Teammates  
> **Team:** Pica pica  
> **Core Mission Statement:** *"Merchants don't need another dashboard. They need a teammate."*

---

## 1. Executive Summary & The Core Thesis

### The Problem with Status-Quo Solutions
Small and medium Paytm merchants (kiranas, retail outlets, local eateries) are inundated with dashboards and alerts:
- **Dashboards demand cognitive labor**: A busy merchant at a counter does not have 30 minutes to dissect order drop-offs, compute margins, or configure discount campaign segmentations.
- **Chatbots only chat**: Generic LLM assistants offer vague generic advice ("Have you tried running promotions?") without knowing inventory, margins, or customer transaction history.
- **Unbounded AI agents are dangerous**: Handing operational execution directly to a raw LLM creates existential risk—hallucinating 100% discounts, blowing merchant budgets, or violating minimum profit margins.

### The MITRA Solution
**MITRA** is an **Autonomous AI Teammate** that pairs real-time data monitoring with a non-negotiable safety architecture:
1. **Detects** business anomalies automatically (e.g. 29.02% evening order slump).
2. **Investigates** data provenance using verified SQLite digital-twin telemetry.
3. **Proposes** high-probability recovery actions.
4. **Guards** every parameter through deterministic mathematical bounds (never an LLM).
5. **Gates Autonomy** based on merchant-configured risk policies (`APPROVAL_REQUIRED`, `AUTO_APPROVE_SAFE`, `FULL_AUTONOMY`).
6. **Simulates Execution** with zero live Paytm API side effects.
7. **Measures Real Lift** against baseline cohorts.
8. **Records an Immutable SHA-256 Chained Audit Trail** that persists forever across demo resets.

### The Core Architectural Invariant
$$\mathbf{AI\ Intelligence\ Without\ AI\ Authority}$$
> **"The LLM interprets; deterministic systems decide; guardrails enforce; the execution barrier acts."**

---

## 2. 6-Pillar System Health Bar (Telemetry)

Located at the top of the MITRA Command Center UI:

| Pillar | Subsystem | Status | Guarantee |
| :--- | :--- | :--- | :--- |
| **1. Backend** | FastAPI Asynchronous Server (:8000) | `ONLINE` | Sub-50ms deterministic pipeline execution |
| **2. Database** | SQLite Digital-Twin Sandbox | `ONLINE` | 520 customers, 1,284 calibrated orders |
| **3. AI Reasoner** | Google Gemini 2.5 Flash (`gemini-2.5-flash`) | `ACTIVE` | Grounded facts only; non-authoritative advisory |
| **4. Guardrails** | Phase 6 Deterministic Policy Engine | `ACTIVE` | Hard ₹100 discount, ₹12,000 budget, 10% margin floors |
| **5. Audit Ledger** | Phase 11 Cryptographic SHA-256 Ledger | `ACTIVE` | Unbroken hash chain starting at `AUDIT-INIT-001` |
| **6. Execution Barrier** | Phase 8 Safe Execution Sandbox | `SIMULATED` | Zero live financial side effects; strictly gated |

---

## 3. Judge Presentation: 6 Live Demo Scenarios

In the Command Center UI under **Live Scenario Orchestrator**, select and execute each scenario in sequence:

### Scenario 1: Standard Autonomous Flow (Normal Flow)
- **Demonstrates:** Complete 8-stage teammate pipeline from telemetry to decision.
- **What Happens:** Signal `SIG-EVN-DECLINE-01` (-29.02% drop) is detected. Investigation confirms regular evening drop. Action proposal is generated, evaluated by guardrails (`PASS`), and placed in `PENDING_APPROVAL` under merchant's `APPROVAL_REQUIRED` policy.
- **Judge Takeaway:** MITRA operates proactively without waiting for the merchant to ask.

### Scenario 2: Guardrail Parameter Clamping (Modify Flow)
- **Demonstrates:** Deterministic safety override of excessive AI/candidate proposals.
- **What Happens:** An action proposing an unsafe ₹150 discount per customer is submitted. Phase 6 Guardrails detect this exceeds the merchant's ₹100 maximum discount ceiling.
- **Result:** Instead of crashing or rejecting completely, the engine applies a **`₹150 → ₹100 SAFETY CLAMP`**, modifying the action to compliant bounds before sign-off.
- **Judge Takeaway:** Guardrails are deterministic code, not prompts that an LLM can ignore.

### Scenario 3: Hard Safety Boundary (Block Flow)
- **Demonstrates:** Absolute halt on high-risk, catastrophic proposals.
- **What Happens:** An adversarial or runaway proposal attempts a 99% discount with a ₹999,999 budget.
- **Result:** Guardrail engine triggers a hard **`BLOCK`**. The decision is marked `BLOCKED`, and the execution barrier permanently bars dispatch under any autonomy level.
- **Judge Takeaway:** MITRA guarantees safety first—runaway actions cannot execute.

### Scenario 4: Safe Controlled Autonomy (Auto-Approve Flow)
- **Demonstrates:** Safe autonomous dispatch without human bottleneck.
- **What Happens:** The merchant enables `AUTO_APPROVE_SAFE` mode (risk threshold $\le 0.30$). A low-risk promotional campaign (evaluated risk = 0.20, budget = ₹800) is submitted.
- **Result:** Autonomy Engine automatically verifies policy compliance and auto-approves the campaign (`AUTO_APPROVED`). Execution proceeds to simulated dispatch immediately.
- **Judge Takeaway:** Routine, low-risk tasks execute autonomously, freeing the merchant.

### Scenario 5: Human-in-the-Loop Review Gate (Unapproved Flow)
- **Demonstrates:** Strict review gate holding actions until explicit merchant sign-off.
- **What Happens:** Action is generated in `APPROVAL_REQUIRED` mode. Direct simulated execution is attempted without merchant approval.
- **Result:** Execution barrier rejects the dispatch with **`HTTP 400 Bad Request`** (`approval_status is PENDING`). Only clicking **"APPROVE ACTION"** permits execution.
- **Judge Takeaway:** The merchant retains ultimate authority whenever they choose.

### Scenario 6: Graceful Degradation / Insufficient Data (Zero Hallucination)
- **Demonstrates:** Complete avoidance of fabricated numbers on sparse data.
- **What Happens:** An unmeasured or incomplete telemetry workflow is evaluated.
- **Result:** MITRA returns `status: UNAVAILABLE` with clear advisory text and **zero hallucinated metrics or phantom revenue claims**.
- **Judge Takeaway:** MITRA never guesses when facts are unavailable.

---

## 4. Reset Demo & Cryptographic Audit Preservation

In the header bar, click **"RESET DEMO"**:
1. **Deterministic Baseline Restored:**
   - Reseeds digital-twin merchant: Sharma Kirana & General Store (`MID-DEMO-98234`).
   - Reseeds 520 customers and 1,284 transactions totaling ₹481,849.82.
   - Restores autonomy policy to baseline `APPROVAL_REQUIRED`.
   - Clears ephemeral scenario-local actions and in-memory AI cache.
2. **AUDIT LEDGER PRESERVED (Critical Invariant):**
   - Historical audit records are **NEVER purged**.
   - The genesis block (`AUDIT-INIT-001`, `previous_hash: GENESIS`) is permanently preserved.
   - Records a new `DEMO_RESET_PERFORMED` event into the unbroken SHA-256 hash chain.
   - The UI displays `Baseline Restored (X Audits Kept)`.

---

## 5. Multi-Provider AI Architecture & Failover

MITRA uses a 3-tier failover hierarchy:
```
Primary: Google Gemini 2.5 Flash (gemini-2.5-flash)
    │
    ▼ (on timeout / 429 quota exhaustion)
Secondary: Hugging Face Inference API
    │
    ▼ (on network outage / unconfigured keys)
Safety Net: Deterministic Fallback Client (100% Offline Safe)
```

### Safety Features
- **Prompt Injection Defense:** Unsafe commands (`APPROVE`, `EXECUTE`, `BYPASS_GUARDRAILS`) in user prompts or LLM completions are stripped and replaced with `[ADVISORY_ONLY]`.
- **Zero Secret Exposure:** Telemetry, logs, and API responses never expose API keys or credentials.
- **Fact-Grounding:** Every AI explanation references verified fact IDs (`F1`, `F2`) from the SQLite database.

---

## 6. Verification Proof & Quality Metrics

```bash
# 1. Full Backend Test Suite (387 tests, 0 failures, 0 regressions)
cd backend
python -m pytest tests/ -q
# Output: 387 passed in ~34s

# 2. Phase 14 Comprehensive Live E2E Verification (12/12 checks)
python scratch_verify_phase14.py
# Output: ALL 12/12 PHASE 14 LIVE E2E CHECKS PASSED WITH 100% COMPLIANCE!

# 3. Phase 12 Controlled Autonomy Verification (8/8 scenarios)
python scratch_verify_e2e.py
# Output: ALL 8/8 PHASE 12 LIVE E2E SCENARIOS SUCCEEDED!

# 4. Phase 13 Command Center Verification (6/6 scenarios)
python scratch_verify_phase13.py
# Output: ALL PHASE 13 LIVE E2E SCENARIOS VERIFIED SUCCESSFULLY!

# 5. Frontend Production Build & Lint
cd ../frontend
npm run lint    # 0 errors, 0 warnings
npm run build   # Compiled successfully (Turbopack, Next.js 16.3.5)
```
