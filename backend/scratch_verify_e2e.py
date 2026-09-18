"""Phase 12 End-to-End Verification Script: Controlled Autonomy & Human-in-the-Loop.

Verifies all 8 mandatory live E2E scenarios against the running MITRA server:
1. APPROVAL_REQUIRED: Default mode gates execution until explicit human sign-off.
2. AUTO_APPROVE_SAFE: Low risk (<=0.30) auto-approved deterministically by policy.
3. FULL_AUTONOMY: Moderate risk (<=0.50) auto-approved deterministically by policy.
4. BLOCK OVERRIDES AUTONOMY: Guardrail BLOCK strictly blocks execution even in FULL_AUTONOMY.
5. MODIFY CLAMPING: Rs 150 clamped to Rs 100, autonomy evaluates Rs 100, executes Rs 100.
6. HUMAN REJECTION: Merchant rejection halts execution permanently.
7. ESCALATION: High-risk / boundary conditions demand human sign-off under any autonomy mode.
8. STALE STATE: Proposal alteration invalidates cryptographic hash and blocks approval.
"""
import json
import sqlite3
import sys
import urllib.error
import urllib.request

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database.repository import (
    ActionRepository,
    AutonomyRepository,
    DecisionRepository,
    GuardrailRepository,
    MerchantRepository,
)

BASE_URL = "http://127.0.0.1:8000"


def api_post(path, data=None):
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_put(path, data=None):
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_e2e():
    print("======================================================================")
    print("MITRA PHASE 12: CONTROLLED AUTONOMY ENGINE LIVE E2E VERIFICATION")
    print("======================================================================\n")

    mid = "MID-DEMO-98234"

    # Reset any previous test artifacts
    conn = sqlite3.connect("mitra_local.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM autonomy_evaluations WHERE action_id LIKE 'act-p12-%'")
    cur.execute("DELETE FROM executions WHERE decision_id IN (SELECT id FROM decisions WHERE action_id LIKE 'act-p12-%')")
    cur.execute("DELETE FROM decisions WHERE action_id LIKE 'act-p12-%'")
    cur.execute("DELETE FROM guardrail_evaluations WHERE action_id LIKE 'act-p12-%'")
    cur.execute("DELETE FROM actions WHERE id LIKE 'act-p12-%'")
    cur.execute("DELETE FROM investigations WHERE id LIKE 'inv-p12-%'")
    cur.execute("DELETE FROM signals WHERE id LIKE 'sig-p12-%'")
    conn.commit()
    conn.close()

    # SCENARIO 1: APPROVAL_REQUIRED (DEFAULT MODE)
    print("--- SCENARIO 1: APPROVAL_REQUIRED (Default Gate Mode) ---")
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "APPROVAL_REQUIRED"})
    policy = api_get(f"/api/merchants/{mid}/autonomy")
    assert policy["autonomy_mode"] == "APPROVAL_REQUIRED", f"Unexpected mode: {policy}"

    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc1",
        investigation_id="inv-p12-sc1",
        action_id="act-p12-sc1",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 5, "discount_amount": 10, "budget_inr": 500, "target_count": 100, "risk_score": 0.15},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc1")
    api_post("/api/decisions/create/act-p12-sc1")

    # Autonomy evaluation
    eval1 = api_post("/api/autonomy/evaluate/act-p12-sc1")
    assert eval1["autonomy_status"] == "APPROVAL_REQUIRED", f"Got {eval1['autonomy_status']}"
    assert eval1["auto_approval_allowed"] is False
    assert eval1["approval_required"] is True

    # Execution must be forbidden prior to human sign-off
    dec1 = api_get("/api/actions/act-p12-sc1/decision")
    assert dec1["approval_status"] == "PENDING"
    assert dec1["is_execution_eligible"] is False
    try:
        api_post(f"/api/executions/execute/{dec1['decision_id']}")
        assert False, "Execution should have failed without approval"
    except urllib.error.HTTPError as e:
        assert e.code in (400, 422)

    # Merchant sign-off via Phase 12 endpoint
    app1 = api_post("/api/autonomy/act-p12-sc1/approve", {"merchant_id": mid, "reason": "Approved by merchant demo"})
    assert app1["approval_source"] == "HUMAN_APPROVED"

    # Now execution succeeds
    exec1 = api_post(f"/api/executions/execute/{dec1['decision_id']}")
    assert exec1["status"] == "COMPLETED"
    print("✓ Scenario 1 PASS: APPROVAL_REQUIRED gated execution until merchant approved.\n")

    # SCENARIO 2: AUTO_APPROVE_SAFE (LOW RISK <= 0.30)
    print("--- SCENARIO 2: AUTO_APPROVE_SAFE (Risk <= 0.30) ---")
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "AUTO_APPROVE_SAFE", "auto_approval_risk_threshold": 0.30})

    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc2",
        investigation_id="inv-p12-sc2",
        action_id="act-p12-sc2",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 10, "discount_amount": 25, "budget_inr": 800, "target_count": 100, "risk_score": 0.20},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc2")
    api_post("/api/decisions/create/act-p12-sc2")

    eval2 = api_post("/api/autonomy/evaluate/act-p12-sc2")
    assert eval2["autonomy_status"] == "AUTO_APPROVED", f"Expected AUTO_APPROVED, got {eval2['autonomy_status']}"
    assert eval2["auto_approval_allowed"] is True
    assert eval2["approval_source"] == "AUTO_APPROVED"

    # Automatically execution eligible without human call
    dec2 = api_get("/api/actions/act-p12-sc2/decision")
    assert dec2["approval_status"] == "APPROVED"
    assert dec2["is_execution_eligible"] is True

    exec2 = api_post(f"/api/executions/execute/{dec2['decision_id']}")
    assert exec2["status"] == "COMPLETED"
    print(f"✓ Scenario 2 PASS: AUTO_APPROVE_SAFE cleared risk={eval2['evaluated_risk']} <= threshold={eval2['policy_threshold']}.\n")

    # SCENARIO 3: FULL_AUTONOMY (MODERATE RISK <= 0.50)
    print("--- SCENARIO 3: FULL_AUTONOMY (Risk <= 0.50) ---")
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "FULL_AUTONOMY", "full_autonomy_risk_threshold": 0.50})

    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc3",
        investigation_id="inv-p12-sc3",
        action_id="act-p12-sc3",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 15, "discount_amount": 45, "budget_inr": 1500, "target_count": 100, "risk_score": 0.42},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc3")
    api_post("/api/decisions/create/act-p12-sc3")

    eval3 = api_post("/api/autonomy/evaluate/act-p12-sc3")
    assert eval3["autonomy_status"] == "AUTO_APPROVED"
    assert eval3["auto_approval_allowed"] is True
    assert eval3["approval_source"] == "AUTO_APPROVED"

    dec3 = api_get("/api/actions/act-p12-sc3/decision")
    assert dec3["approval_status"] == "APPROVED"
    assert dec3["is_execution_eligible"] is True

    exec3 = api_post(f"/api/executions/execute/{dec3['decision_id']}")
    assert exec3["status"] == "COMPLETED"
    print(f"✓ Scenario 3 PASS: FULL_AUTONOMY cleared moderate risk={eval3['evaluated_risk']} <= {eval3['policy_threshold']}.\n")

    # SCENARIO 4: BLOCK OVERRIDES AUTONOMY (SAFETY BOUNDARY INVARIANT)
    print("--- SCENARIO 4: BLOCK OVERRIDES AUTONOMY (Hard Guardrail) ---")
    # Even under FULL_AUTONOMY:
    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc4",
        investigation_id="inv-p12-sc4",
        action_id="act-p12-sc4",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 99, "discount_amount": 5000, "budget_inr": 999999, "target_count": 100, "risk_score": 0.10},
    )
    grd4 = api_post("/api/guardrails/evaluate/act-p12-sc4")
    assert grd4["overall_status"] == "BLOCK"

    dec4 = api_post("/api/decisions/create/act-p12-sc4")
    assert dec4["decision_state"] == "BLOCK"

    eval4 = api_post("/api/autonomy/evaluate/act-p12-sc4")
    assert eval4["autonomy_status"] == "BLOCKED"
    assert eval4["blocked"] is True
    assert eval4["auto_approval_allowed"] is False

    # Manual approval MUST fail
    try:
        api_post("/api/autonomy/act-p12-sc4/approve", {"merchant_id": mid})
        assert False, "Manual approval of BLOCKED action must fail"
    except urllib.error.HTTPError as e:
        assert e.code == 400

    # Execution MUST fail
    try:
        api_post(f"/api/executions/execute/{dec4['decision_id']}")
        assert False, "Execution of BLOCKED action must fail"
    except urllib.error.HTTPError as e:
        assert e.code in (400, 422)
    print("✓ Scenario 4 PASS: BLOCK unconditionally overrides FULL_AUTONOMY. Autonomy never bypasses safety.\n")

    # SCENARIO 5: MODIFY CLAMPING INVARIANT
    print("--- SCENARIO 5: MODIFY Clamping Invariant ---")
    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc5",
        investigation_id="inv-p12-sc5",
        action_id="act-p12-sc5",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 10, "discount_amount": 150, "budget_inr": 1000, "target_count": 100, "risk_score": 0.25},
    )
    grd5 = api_post("/api/guardrails/evaluate/act-p12-sc5")
    assert grd5["overall_status"] == "MODIFY"
    assert grd5["modifications"]["discount_amount"] == 100.0

    dec5 = api_post("/api/decisions/create/act-p12-sc5")
    assert dec5["decision_state"] == "MODIFY"
    assert dec5["approved_action"]["parameters"]["discount_amount"] == 100.0

    # Under FULL_AUTONOMY, the clamped Rs 100 action is auto-approved
    eval5 = api_post("/api/autonomy/evaluate/act-p12-sc5")
    assert eval5["autonomy_status"] == "AUTO_APPROVED"
    assert eval5["auto_approval_allowed"] is True

    # Execute and verify executed parameters contain strictly Rs 100, NEVER raw Rs 150
    exec5 = api_post(f"/api/executions/execute/{dec5['decision_id']}")
    exec_params = exec5["approved_action"]["parameters"]
    assert exec_params["discount_amount"] == 100.0, f"Unsafe Rs 150 leaked! Got {exec_params['discount_amount']}"
    print("✓ Scenario 5 PASS: Guardrail clamped Rs 150 -> Rs 100. Autonomy approved Rs 100. Execution strictly executed Rs 100.\n")

    # SCENARIO 6: HUMAN REJECTION
    print("--- SCENARIO 6: Human Rejection Flow ---")
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "APPROVAL_REQUIRED"})

    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc6",
        investigation_id="inv-p12-sc6",
        action_id="act-p12-sc6",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 10, "discount_amount": 20, "budget_inr": 500, "target_count": 100, "risk_score": 0.20},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc6")
    api_post("/api/decisions/create/act-p12-sc6")
    api_post("/api/autonomy/evaluate/act-p12-sc6")

    rej6 = api_post("/api/autonomy/act-p12-sc6/reject", {"merchant_id": mid, "reason": "Merchant campaign pause"})
    assert rej6["approval_source"] == "REJECTED"

    dec6 = api_get("/api/actions/act-p12-sc6/decision")
    assert dec6["approval_status"] == "REJECTED"
    assert dec6["is_execution_eligible"] is False

    try:
        api_post(f"/api/executions/execute/{dec6['decision_id']}")
        assert False, "Rejected decision must not execute"
    except urllib.error.HTTPError as e:
        assert e.code in (400, 422)
    print("✓ Scenario 6 PASS: Merchant rejected action; execution permanently barred.\n")

    # SCENARIO 7: ESCALATION FLOW
    print("--- SCENARIO 7: ESCALATION Review Gate ---")
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "FULL_AUTONOMY"})

    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc7",
        investigation_id="inv-p12-sc7",
        action_id="act-p12-sc7",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 45, "discount_amount": 80, "budget_inr": 2000, "target_count": 100, "risk_score": 0.85},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc7")
    api_post("/api/decisions/create/act-p12-sc7")

    eval7 = api_post("/api/autonomy/evaluate/act-p12-sc7")
    # Because risk 0.85 > max_auto_risk 0.50 (or guardrail overall status is ESCALATE), cannot auto approve
    assert eval7["autonomy_status"] in ("ESCALATED", "APPROVAL_REQUIRED")
    assert eval7["auto_approval_allowed"] is False

    dec7_state = api_get("/api/actions/act-p12-sc7/decision")
    assert dec7_state["is_execution_eligible"] is False
    print("✓ Scenario 7 PASS: High risk / boundary condition prevented auto-approval even in FULL_AUTONOMY.\n")

    # SCENARIO 8: STALE STATE / CRYPTOGRAPHIC INVARIANCE
    print("--- SCENARIO 8: Stale State / Cryptographic Invariance ---")
    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-p12-sc8",
        investigation_id="inv-p12-sc8",
        action_id="act-p12-sc8",
        merchant_id=mid,
        action_type="OFFER_CAMPAIGN",
        parameters={"discount_percent": 10, "discount_amount": 20, "budget_inr": 600, "target_count": 100, "risk_score": 0.20},
    )
    api_post("/api/guardrails/evaluate/act-p12-sc8")
    api_post("/api/decisions/create/act-p12-sc8")
    api_post("/api/autonomy/evaluate/act-p12-sc8")

    # Tamper with proposal parameters directly in SQLite
    conn = sqlite3.connect("mitra_local.db")
    cur = conn.cursor()
    cur.execute(
        "UPDATE actions SET parameters = ? WHERE id = ?",
        (json.dumps({"discount_percent": 50, "discount_amount": 999, "budget_inr": 9999, "target_count": 100}), "act-p12-sc8")
    )
    conn.commit()
    conn.close()

    # Re-evaluating or approving must fail due to SHA-256 hash mismatch
    try:
        api_post("/api/autonomy/evaluate/act-p12-sc8")
        assert False, "Tampered proposal should trigger 409 Conflict due to hash invalidation"
    except urllib.error.HTTPError as e:
        assert e.code == 409
    print("✓ Scenario 8 PASS: Proposal mutation detected by SHA-256 integrity verification (409 Conflict).\n")

    # RESET POLICY TO DEMO DEFAULT
    api_put(f"/api/merchants/{mid}/autonomy", {"autonomy_mode": "APPROVAL_REQUIRED", "auto_approval_risk_threshold": 0.30})
    final_policy = api_get(f"/api/merchants/{mid}/autonomy")
    assert final_policy["autonomy_mode"] == "APPROVAL_REQUIRED"
    print("Demo policy cleanly reset to APPROVAL_REQUIRED.\n")

    print("======================================================================")
    print("ALL 8/8 PHASE 12 LIVE E2E SCENARIOS SUCCEEDED WITH 100% COMPLIANCE!")
    print("======================================================================")


if __name__ == "__main__":
    run_e2e()
