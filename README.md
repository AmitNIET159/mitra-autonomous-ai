# MITRA — Autonomous AI Teammate for Paytm Merchants

> **Paytm Build for India AI Hackathon — Delhi Edition**  
> **Track:** Track 3 — Autonomous AI Teammates  
> **Team:** Pica pica  
> **Core Statement:** *"An AI teammate that doesn't just recommend actions — it safely executes them and measures their impact."*

---

## 1. Project Overview

**MITRA** is an autonomous AI teammate designed specifically for Paytm merchants. Unlike chatbots that offer conversational suggestions, analytics dashboards that demand merchant interpretation, or unbounded LLM agents that risk catastrophic operational mistakes, MITRA executes an end-to-end autonomous business workflow:

$$\mathbf{DETECT} \longrightarrow \mathbf{INVESTIGATE} \longrightarrow \mathbf{DECIDE} \longrightarrow \mathbf{GUARD} \longrightarrow \mathbf{ACT} \longrightarrow \mathbf{LEARN}$$

MITRA is built upon the foundational engineering principle:
> **"Deterministic systems calculate truth; the LLM interprets it."**

The LLM is utilized for context understanding, signal investigation, and candidate action synthesis. However, **the LLM is strictly prohibited from directly executing actions, overriding business guardrails, or calculating financial constraints.** All actions pass through a deterministic guardrail and decision engine before reaching execution.

---

## 🌐 Live Cloud Deployment

MITRA is production-ready and configured for zero-friction cloud deployment:
- **Backend (FastAPI)**: Automated CI/CD deployment on [Render](https://render.com) using [`render.yaml`](render.yaml) Blueprint with dynamic port binding and automated SQLite digital-twin seeding.
- **Frontend (Next.js 16)**: Native Edge deployment on [Vercel](https://vercel.com) using [`frontend/vercel.json`](frontend/vercel.json).
- **Step-by-Step Deployment Guide**: Complete walkthrough in [**DEPLOYMENT_GUIDE.md**](DEPLOYMENT_GUIDE.md).

---

## 2. Core Architecture

```
Business Signal (Soundbox / QR / Digital-Twin Telemetry)
         │
         ▼
    SignalEngine (Anomaly & Opportunity Detection)
         │
         ▼
 InvestigationEngine (LLM Reasoning + Data Correlation)
         │
         ▼
   PlanningEngine (Action Proposals & Hypotheses)
         │
         ▼
Deterministic GuardrailEngine (Hard Budget, Discount & Risk Ceilings)
         │
         ▼
 DecisionEngine ───► Authoritative States: [PASS | MODIFY | BLOCK | ESCALATE]
         │
    ┌────┴──────────────────────────┐
    │ State in (PASS, MODIFY)       │ State in (BLOCK, ESCALATE)
    ▼                               ▼
ExecutionEngine (Simulated)    Execution Prevented / Held for Merchant
    │
    ▼
MonitoringEngine (Baseline vs Observed GMV / Footfall Lift)
    │
    ▼
AuditEngine (SHA-256 Chained Tamper-Evident Ledger)
```

### Safety & Decision States Contract
MITRA enforces exactly four primary decision states:
1. **`PASS`**: All deterministic constraints satisfied. Safe for automated execution.
2. **`MODIFY`**: Minor constraints exceeded (e.g., proposed discount > 25%). Guardrails automatically clamp parameters to compliant thresholds.
3. **`BLOCK`**: High operational risk or severe budget overshoot (>2x max limit). Execution strictly prevented.
4. **`ESCALATE`**: Moderate budget overshoot or high uncertainty. Action paused and flagged for merchant manual sign-off.

**Execution Safety Guarantee:**  
`ExecutionEngine` enforces hard type-level and state checks. Any attempt to pass a raw LLM response, an unchecked `ActionProposal`, or a decision in `BLOCK`/`ESCALATE` state immediately triggers an `ExecutionSafetyError`.

---

## 3. Digital Twin & Primary Demo Scenario (Phase 2)

MITRA incorporates an authentic, 100% local SQLite digital twin sandbox modeling a real Delhi NCR merchant.

### Primary Demo Merchant Profile
- **Business Name:** Sharma Kirana & General Store
- **Simulated Merchant ID:** `MID-DEMO-98234` (Strictly marked as simulated)
- **Category:** Retail / Grocery
- **Location:** Delhi NCR
- **Merchant Rules:**
  - Minimum Margin: 10%
  - Daily Campaign Budget: ₹12,000
  - Maximum Discount: ₹100
  - Max Campaign Frequency: 3
  - Autonomy Level: `APPROVAL_REQUIRED`

### Main Scenario: Evening Orders Decline (~29% Drop)
- **Historical Evening Baseline:** 410 orders
- **Observed Evening Orders:** 291 orders
- **Variance:** **-29.02% (~29% drop)**
- **Root Cause Context:** Repeat-customer conversion dropped from **18.2% to 14.8%** after previous evening marketing campaign (*"Evening Rush Cashback"*) expired 3 days ago.
- **Derived Campaign Target Segment:** **486 eligible customers** (out of 520 total customers).
- **Aggregated Window Revenue:** ₹4.82L across 1,284 total orders.

---

## 4. Technology Stack

- **Backend:** FastAPI, Python 3.14, Pydantic v2, SQLite (`mitra_local.db`), Uvicorn
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS v4, Lucide Icons
- **AI / LLM Layer:** Google Gemini Flash 3.8 High (`gemini-2.5-flash`) with deterministic `FallbackClient`
- **Cost:** **$0.00 / Free**. Zero paid databases, zero paid third-party dependencies, runs 100% locally.

---

## 5. Local Setup Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.14.3)
- Node.js 18+ (Tested on Node.js v24.14.1, npm 11.18.0)

### 1. Backend Setup & Database Seeding
Navigate to `backend/`:
```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
python -m app.database.seed
```

### 2. Run Backend
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Key endpoints:
- `GET /api/health` — Health check
- `GET /api/merchant` — Digital-twin merchant profile
- `GET /api/merchant/metrics` — Seeded business health and evening anomaly metrics
- `GET /api/merchant/customers/summary` — Customer segmentation and 486 campaign target
- `GET /api/merchant/campaigns` — Marketing campaigns history
- `GET /api/simulation/status` — Digital twin simulation telemetry
- `POST /api/simulation/reset` — Reset database to deterministic baseline

### 3. Run Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the MITRA Merchant Dashboard.

---

## 6. Running Automated Tests

Run the complete backend test suite:
```bash
python -m pytest backend/tests -v
```

Verification suite includes:
- `test_health.py`: Health endpoint (`GET /api/health` -> `{"status": "ok", "service": "MITRA"}`) and system status.
- `test_contracts.py`: Strongly typed Pydantic contracts and strict 4 decision states.
- `test_llm_fallback.py`: Zero-crash offline fallback behavior.
- `test_safety_boundary.py`: Raw proposals and blocked/escalated decisions can NEVER execute.
- `test_orchestrator_contract.py`: End-to-end simulation of compliant and blocked execution pipelines.
- `test_database.py`: All 13 relational tables, repository queries, and reset endpoint.
- `test_seed_scenario.py`: Verifies primary merchant, 520 customers, 486 target segment, 410 baseline vs 291 observed evening orders (-29.02%), repeat conversion drop (18.2% -> 14.8%), and expired campaign.

Frontend checks:
```bash
cd frontend
npm run lint
npm run build
```

---

## 7. Current Implementation Status

- [x] **Phase 0 & 1: Foundation & Safety Architecture** (18 tests passing)
- [x] **Phase 2: Database + Digital Twin + Realistic Seed Data** (28 tests passing)
- [x] **Phase 3: Signal Detection Engine** (10 tests passing)
- [x] **Phase 4: Root Cause Investigation Engine** (14 tests passing)
- [x] **Phase 5: Action Planning Engine** (17 tests passing)
- [x] **Phase 6: Deterministic Guardrail Engine** (35 tests passing)
- [x] **Phase 7: Authoritative Decision Derivation Engine** (35 tests passing)
- [x] **Phase 8: Simulated Execution Engine** (35 tests passing)
- [x] **Phase 9: Outcome Measurement Engine** (40 tests passing)
- [x] **Phase 10: ROI & Business Impact Analysis** (40 tests passing)
- [x] **Phase 11: Audit Trail & Explainability System** (44 tests passing)
- [x] **Phase 12: Human-in-the-Loop & Controlled Autonomy Engine** (45 tests passing)
- [x] **Phase 13: Command Center AI & Live MITRA Experience** (33 tests passing, 6/6 E2E verified)
- [x] **Phase 14: Final Demo Reliability, Scenario Reset & Hackathon Polish** (23 tests passing, 12/12 live checks verified)
  - **Overall Backend Test Suite:** **387 tests passing, 0 failures, 0 regressions**
  - **Frontend:** Next.js 16.3.5 Turbopack production build passing, 0 ESLint errors/warnings
  - **Live Verification Scripts:** `scratch_verify_e2e.py` (Phase 12, 8/8 PASS), `scratch_verify_phase13.py` (Phase 13, 6/6 PASS), `scratch_verify_phase14.py` (Phase 14, 12/12 PASS)
  - **Demo Runbook:** See [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) for judge narrative and live presentation script.

---

## 8. Simulation / Digital-Twin Disclaimer

> [!WARNING]
> **PROTOTYPE SIMULATION NOTICE:**  
> All merchant profiles, transaction streams, Paytm Soundbox/POS telemetry, and projected financial outcomes are synthetic simulations running in a digital-twin sandbox created for the Paytm Build for India Hackathon. No real Paytm production APIs or confidential merchant accounts are accessed or represented.

