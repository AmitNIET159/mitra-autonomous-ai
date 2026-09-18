# MITRA — Phase 13: AI-Powered Command Center + Live MITRA Experience

**Paytm Build for India AI Hackathon – Delhi Edition**  
**Track 3: Autonomous AI Teammates**  
**Team: Pica pica**  

---

## 1. Executive Summary

Phase 13 establishes the production-grade **Autonomous Merchant Command Center** for MITRA, coupling deterministic safety enforcement with multi-provider AI reasoning.

Prior phases (1–12) established deterministic signal detection, evidence collection, candidate planning, 10-point guardrail evaluation, authoritative decision gateways, cryptographically chained audit trails, post-execution outcome telemetry, business impact calculation, and controlled autonomy.

Phase 13 delivers:
1. **Multi-Provider AI Intelligence Layer**: Native integration with Google Gemini Flash 3.8 High (`gemini-2.5-flash`), Hugging Face Inference API (`meta-llama/Llama-3.2-3B-Instruct`), and a 100% offline Deterministic Fallback.
2. **Deterministic Failover Hierarchy**: Gemini $\to$ Hugging Face $\to$ Local Deterministic Fallback. Zero service interruption in hackathon Wi-Fi or offline environments.
3. **Strict Non-Authoritative LLM Boundary**: The LLM interprets data and generates merchant hypotheses and explanations. **The LLM has ZERO execution, approval, or guardrail-override authority**.
4. **Prompt Injection Defense**: Neutralizes prompt-injection attacks that attempt operational directives (`APPROVE`, `EXECUTE`, `BYPASS_GUARDRAILS`).
5. **Interactive Hackathon Scenario Controller**: 6 real-time backend scenario demonstrations (`NORMAL_FLOW`, `MODIFY_FLOW`, `BLOCK_FLOW`, `AUTO_APPROVE_FLOW`, `UNAPPROVED_FLOW`, `INSUFFICIENT_DATA_FLOW`).
6. **Command Center UI**: Graphite/slate styled dashboard with real-time Copilot Q&A, grounding fact pills (`[E1]`, `[F1]`, etc.), telemetry status badges, and digital-twin simulation indicators.

---

## 2. Multi-Provider AI Architecture

```text
               +----------------------------------+
               | Merchant Query / Workflow Event  |
               +----------------------------------+
                                |
                                v
              +------------------------------------+
              |        AIProviderManager           |
              | - Prompt Injection Neutralization  |
              | - Verified Fact Context Builder    |
              | - In-Memory SHA Caching            |
              +------------------------------------+
                                |
         +----------------------+----------------------+
         | (1. Primary)         | (2. Secondary)       | (3. Offline Fallback)
         v                      v                      v
+------------------+   +-------------------+   +--------------------+
|  Google Gemini   |   |   Hugging Face    |   | Deterministic      |
|  2.5 Flash High  |---| Inference API     |---| Fallback Client    |
| (Active Provider)|   | (Llama 3.2 3B)    |   | (100% Offline SLA) |
+------------------+   +-------------------+   +--------------------+
         |                      |                      |
         +----------------------+----------------------+
                                |
                                v
              +------------------------------------+
              | Standardized Advisory AIResponse   |
              | - Natural language explanation     |
              | - Verified Grounding Fact IDs      |
              | - Non-Causal Advisory Disclaimer   |
              | - Telemetry & Cache Metadata       |
              +------------------------------------+
                                |
                                v
             +--------------------------------------+
             |   Strict Non-Authoritative Boundary  |
             | CANNOT approve, modify, or execute   |
             | All actions gate through Phase 6-12  |
             +--------------------------------------+
```

---

## 3. Core Principles & Safety Invariants

1. **Deterministic Truth vs. Advisory Interpretation**:
   - Deterministic systems calculate truth and enforce hard boundaries (Phase 1–12).
   - The LLM interprets the truth for merchant clarity and generates hypotheses (Phase 13).
2. **Zero Operational Authority**:
   - The LLM cannot mutate database records, approve decisions, or execute campaigns.
   - Any LLM attempt to output operational directives is blocked by prompt defense and architectural separation.
3. **No Unproven Causality**:
   - LLM responses strictly carry non-causal disclaimers: *"Advisory only. Causality is not established; deterministic safety controls enforce all execution boundaries."*
4. **Secret Sanitization**:
   - Zero API keys (`GEMINI_API_KEY`, `HF_API_KEY`) are committed or returned in public API payloads. Provider status endpoints only return provider names and boolean configuration flags.

---

## 4. Live Demo Scenarios Orchestrated

| Scenario ID | Flow Description | Deterministic Pipeline | Decision / Autonomy Outcome |
| :--- | :--- | :--- | :--- |
| `NORMAL_FLOW` | Standard end-to-end autonomous flow | Detect $\to$ Investigate $\to$ Plan $\to$ Guardrail $\to$ Decide | `PASS` / `PENDING` review |
| `MODIFY_FLOW` | Guardrail parameter clamping | Clamps unsafe ₹150 discount to ₹100 policy ceiling | `MODIFY` / clamped ₹100 |
| `BLOCK_FLOW` | Hard safety boundary enforcement | Proposed 99% / ₹5,000 discount violates margin rules | `BLOCK` / strictly inexecutable |
| `AUTO_APPROVE_FLOW` | Low-risk policy auto-approval | Risk 0.20 $\le$ 0.30 threshold under `AUTO_APPROVE_SAFE` | `AUTO_APPROVED` / executable |
| `UNAPPROVED_FLOW` | Human-in-the-loop review gate | Proposed action under `APPROVAL_REQUIRED` mode | `PENDING` / execution barred |
| `INSUFFICIENT_DATA_FLOW`| Unmeasured context demonstration | Sparse telemetry scenario with zero hallucination | `UNAVAILABLE` fallback notice |

---

## 5. Verification Metrics & Baseline

```text
Total Backend Pytest Suite: 364 PASS (0 failures, 0 regressions)
  - Phases 1–12 Baseline: 331 PASS
  - Phase 13 Command Center AI Suite: 33 PASS
Frontend Linter: 0 errors, 0 warnings (clean ESLint)
Frontend Production Build: Next.js 16.3.5 (Turbopack) PASS
Live Phase 13 E2E Script (scratch_verify_phase13.py): 6/6 SCENARIOS PASS
Live Phase 12 E2E Script (scratch_verify_e2e.py): 8/8 SCENARIOS PASS
```
