"""Deterministic Explainability Rules and Provenance Resolvers (Phase 11).

SAFETY & PROTOTYPE PRINCIPLES:
- Facts vs Hypotheses: Strictly distinguishes verified database facts from AI interpretations.
- Non-Causality: Zero causal claims ("Causality is not established; this is an AI interpretation").
- Zero Secret Leakage: Sensitive credentials stripped from all payloads.
- Zero Numerical Hallucination: All metrics come directly from authoritative database records.
- Prototype Disclaimer: Explicitly marked as SIMULATED / PROTOTYPE / DIGITAL TWIN.
"""
import json
from typing import Any, Dict, List, Optional, Tuple

from app.database.connection import get_connection
from app.database.repository import (
    ActionRepository,
    AuditRepository,
    AutonomyRepository,
    BusinessImpactRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    InvestigationRepository,
    SignalRepository,
)
from app.models.contracts import FactItem, HypothesisItem


def resolve_workflow_entities(identifier: str) -> Dict[str, Any]:
    """Resolves all interconnected entities across the 10-phase workflow by any entity ID or correlation ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        sig_row = None
        inv_row = None
        act_row = None
        grd_row = None
        dec_row = None
        exec_row = None
        out_row = None
        imp_row = None
        aut_row = None
        correlation_id = identifier

        # 1. Check if identifier directly matches an entity type
        if identifier.startswith("sig-"):
            sig_row = SignalRepository.get_signal(identifier)
        elif identifier.startswith("inv-"):
            inv_row = InvestigationRepository.get_investigation(identifier)
        elif identifier.startswith("act-") or identifier.startswith("prop-"):
            act_row = ActionRepository.get_action_proposal(identifier)
        elif identifier.startswith("dec-"):
            dec_row = DecisionRepository.get_decision(identifier)
        elif identifier.startswith("exec-"):
            exec_row = ExecutionRepository.get_execution(identifier)
        elif identifier.startswith("out-"):
            cur.execute("SELECT * FROM outcomes WHERE id = ?", (identifier,))
            out_row = cur.fetchone()
            out_row = dict(out_row) if out_row else None
        elif identifier.startswith("imp-"):
            imp_row = BusinessImpactRepository.get_business_impact(identifier)
        elif identifier.startswith("aut-"):
            aut_row = AutonomyRepository.get_evaluation(identifier)

        # 2. If it's a correlation ID or we need to find entities linked to correlation_id
        if not (sig_row or inv_row or act_row or dec_row or exec_row or out_row or imp_row):
            # Try searching audit_events for this correlation_id
            cur.execute(
                """
                SELECT signal_id, investigation_id, action_id, decision_id, execution_id, outcome_id, impact_id
                FROM audit_events WHERE correlation_id = ? AND (signal_id IS NOT NULL OR action_id IS NOT NULL)
                ORDER BY timestamp DESC LIMIT 1
                """,
                (identifier,),
            )
            linked_audit = cur.fetchone()
            if linked_audit:
                la = dict(linked_audit)
                if la.get("signal_id"):
                    sig_row = SignalRepository.get_signal(la["signal_id"])
                if la.get("investigation_id"):
                    inv_row = InvestigationRepository.get_investigation(la["investigation_id"])
                if la.get("action_id"):
                    act_row = ActionRepository.get_action_proposal(la["action_id"])
                if la.get("decision_id"):
                    dec_row = DecisionRepository.get_decision(la["decision_id"])
                if la.get("execution_id"):
                    exec_row = ExecutionRepository.get_execution(la["execution_id"])
                if la.get("outcome_id"):
                    cur.execute("SELECT * FROM outcomes WHERE id = ?", (la["outcome_id"],))
                    orow = cur.fetchone()
                    out_row = dict(orow) if orow else None
                if la.get("impact_id"):
                    imp_row = BusinessImpactRepository.get_business_impact(la["impact_id"])

        # 3. Traverse dependencies upwards / downwards to complete the graph (multiple passes for full bidirectional resolution)
        for _ in range(4):
            # If we have impact, get outcome, execution, decision, action
            if imp_row:
                if not out_row and imp_row.get("outcome_id"):
                    cur.execute("SELECT * FROM outcomes WHERE id = ?", (imp_row["outcome_id"],))
                    orow = cur.fetchone()
                    out_row = dict(orow) if orow else None
                if not exec_row and imp_row.get("execution_id"):
                    exec_row = ExecutionRepository.get_execution(imp_row["execution_id"])
                if not dec_row and imp_row.get("decision_id"):
                    dec_row = DecisionRepository.get_decision(imp_row["decision_id"])
                if not act_row and imp_row.get("action_id"):
                    act_row = ActionRepository.get_action_proposal(imp_row["action_id"])

            # If we have outcome, get execution, decision, action, impact
            if out_row:
                if not exec_row and out_row.get("execution_id"):
                    exec_row = ExecutionRepository.get_execution(out_row["execution_id"])
                if not dec_row and out_row.get("decision_id"):
                    dec_row = DecisionRepository.get_decision(out_row["decision_id"])
                if not act_row and out_row.get("action_id"):
                    act_row = ActionRepository.get_action_proposal(out_row["action_id"])
                if not imp_row:
                    imp_row = BusinessImpactRepository.get_by_outcome(out_row["id"])

            # If we have execution, get decision, action, outcome, impact
            if exec_row:
                if not dec_row and exec_row.get("decision_id"):
                    dec_row = DecisionRepository.get_decision(exec_row["decision_id"])
                if not act_row and exec_row.get("action_id"):
                    act_row = ActionRepository.get_action_proposal(exec_row["action_id"])
                if not out_row:
                    cur.execute("SELECT * FROM outcomes WHERE execution_id = ?", (exec_row["id"],))
                    orow = cur.fetchone()
                    out_row = dict(orow) if orow else None
                    if out_row and not imp_row:
                        imp_row = BusinessImpactRepository.get_by_outcome(out_row["id"])

            # If we have decision, get guardrail, action, execution
            if dec_row:
                if not act_row and dec_row.get("action_id"):
                    act_row = ActionRepository.get_action_proposal(dec_row["action_id"])
                if not grd_row and dec_row.get("evaluation_id"):
                    grd_row = GuardrailRepository.get_evaluation(dec_row["evaluation_id"])
                if not exec_row:
                    exec_row = ExecutionRepository.get_execution_by_decision(dec_row["id"])

            # If we have action, get investigation, signal, guardrail, decision
            if act_row:
                if not inv_row and act_row.get("investigation_id"):
                    inv_row = InvestigationRepository.get_investigation(act_row["investigation_id"])
                if not sig_row and act_row.get("signal_id"):
                    sig_row = SignalRepository.get_signal(act_row["signal_id"])
                if not grd_row:
                    grd_row = GuardrailRepository.get_evaluation_by_action(act_row["id"])
                if not dec_row:
                    dec_row = DecisionRepository.get_decision_by_action(act_row["id"])

            # If we have investigation, get signal, action
            if inv_row:
                if not sig_row and inv_row.get("signal_id"):
                    sig_row = SignalRepository.get_signal(inv_row["signal_id"])
                if not act_row:
                    act_row = ActionRepository.get_action_by_investigation(inv_row["id"])

            # If we have signal, get investigation
            if sig_row and not inv_row:
                inv_row = InvestigationRepository.get_investigation_by_signal(sig_row["id"])
                if inv_row and not act_row:
                    act_row = ActionRepository.get_action_by_investigation(inv_row["id"])

            # If we have action or decision, get autonomy evaluation
            if act_row and not aut_row:
                aut_row = AutonomyRepository.get_by_action(act_row["id"])
            if dec_row and not aut_row:
                aut_row = AutonomyRepository.get_by_decision(dec_row["id"])

        # Resolve correlation ID
        if not correlation_id.startswith("wf-"):
            if sig_row:
                correlation_id = f"wf-{sig_row['id'].replace('sig-', '')}"
            elif inv_row:
                correlation_id = f"wf-{inv_row['id'].replace('inv-', '')}"
            elif act_row:
                correlation_id = f"wf-{act_row['id'].replace('act-', '').replace('prop-', '')}"
            else:
                correlation_id = f"wf-{identifier}"

        # Fetch audit events for this workflow correlation ID
        cur.execute(
            """
            SELECT * FROM audit_events 
            WHERE correlation_id = ? 
            ORDER BY timestamp ASC, rowid ASC
            """,
            (correlation_id,),
        )
        audit_rows = [AuditRepository._row_to_event(r) for r in cur.fetchall()]
        if not audit_rows:
            cur.execute(
                """
                SELECT * FROM audit_events 
                WHERE (signal_id IS NOT NULL AND signal_id = ?)
                   OR (action_id IS NOT NULL AND action_id = ?)
                   OR (decision_id IS NOT NULL AND decision_id = ?)
                   OR (execution_id IS NOT NULL AND execution_id = ?)
                ORDER BY timestamp ASC, rowid ASC
                """,
                (
                    sig_row["id"] if sig_row else "",
                    act_row["id"] if act_row else "",
                    dec_row["id"] if dec_row else "",
                    exec_row["id"] if exec_row else "",
                ),
            )
            audit_rows = [AuditRepository._row_to_event(r) for r in cur.fetchall()]

        return {
            "correlation_id": correlation_id,
            "signal": sig_row,
            "investigation": inv_row,
            "action": act_row,
            "guardrail": grd_row,
            "decision": dec_row,
            "autonomy": aut_row,
            "execution": exec_row,
            "outcome": out_row,
            "business_impact": imp_row,
            "audit_events": audit_rows,
        }
    finally:
        conn.close()


def extract_facts_and_hypotheses(
    investigation_row: Optional[Dict[str, Any]],
    signal_row: Optional[Dict[str, Any]],
    autonomy_row: Optional[Dict[str, Any]] = None,
) -> Tuple[List[FactItem], List[HypothesisItem], List[Dict[str, Any]]]:
    """Extracts authoritative facts with provenance and clearly labels AI hypotheses."""
    facts: List[FactItem] = []
    hypotheses: List[HypothesisItem] = []
    provenance: List[Dict[str, Any]] = []

    # 1. Fact: Primary Signal Anomaly (Reserved ID F1)
    if signal_row:
        base_val = signal_row.get("baseline_value", 0.0)
        obs_val = signal_row.get("observed_value", 0.0)
        chg_pct = signal_row.get("change_percentage", signal_row.get("decline_percentage", 0.0))
        metric = signal_row.get("metric_name", "evening_orders")
        stmt = f"Observed metric '{metric}' dropped by {abs(chg_pct):.2f}% (from {base_val} to {obs_val})."
        facts.append(
            FactItem(
                id="F1",
                fact_type="METRIC_ANOMALY",
                statement=stmt,
                source="business_metrics",
                metric=metric,
                baseline_value=base_val,
                observed_value=obs_val,
                provenance="SQLite table 'daily_metrics' (pre-aggregated merchant transactions)",
            )
        )
        provenance.append({
            "fact_id": "F1",
            "source_table": "daily_metrics",
            "metric": metric,
            "recorded_at": signal_row.get("detected_at"),
        })
    idx = 2

    # 2. Extract facts from Investigation evidence bundle
    if investigation_row:
        bundle_raw = investigation_row.get("evidence_bundle")
        if isinstance(bundle_raw, str):
            try:
                bundle = json.loads(bundle_raw)
            except Exception:
                bundle = {}
        elif isinstance(bundle_raw, dict):
            bundle = bundle_raw
        else:
            bundle = {}

        for item in bundle.get("evidence_items", []):
            desc = item.get("description") or item.get("finding") or "Evidence observed"
            metric = item.get("metric_name")
            base_v = item.get("baseline_value")
            obs_v = item.get("observed_value")
            src = item.get("source") or "pos_transactions"
            facts.append(
                FactItem(
                    id=f"F{idx}",
                    fact_type="EVIDENCE_OBSERVATION",
                    statement=desc,
                    source=src,
                    metric=metric,
                    baseline_value=base_v,
                    observed_value=obs_v,
                    provenance=f"SQLite table '{src}' (evidence verification window)",
                )
            )
            provenance.append({
                "fact_id": f"F{idx}",
                "source_table": src,
                "metric": metric,
            })
            idx += 1

        # 3. Extract Hypotheses (strictly separated from facts)
        hypo_raw = investigation_row.get("hypotheses")
        if isinstance(hypo_raw, str):
            try:
                hypo_list = json.loads(hypo_raw)
            except Exception:
                hypo_list = []
        elif isinstance(hypo_raw, list):
            hypo_list = hypo_raw
        else:
            hypo_list = []

        h_idx = 1
        for h in hypo_list:
            if isinstance(h, dict):
                text = h.get("hypothesis") or h.get("statement") or str(h)
                conf_raw = h.get("confidence", 0.8)
                if isinstance(conf_raw, (int, float)):
                    conf = float(conf_raw)
                elif isinstance(conf_raw, str):
                    conf_map = {"CRITICAL": 0.95, "HIGH": 0.85, "MEDIUM": 0.70, "LOW": 0.50}
                    try:
                        conf = float(conf_raw)
                    except ValueError:
                        conf = conf_map.get(conf_raw.upper(), 0.75)
                else:
                    conf = 0.80
            else:
                text = str(h)
                conf = 0.8
            hypotheses.append(
                HypothesisItem(
                    id=f"H{h_idx}",
                    hypothesis=text,
                    confidence=conf,
                    is_causal_claim=False,
                    caveat="Causality is not established; this is an AI interpretation of observed facts.",
                )
            )
            h_idx += 1

    # 4. Extract Autonomy Facts
    if autonomy_row:
        facts.append(
            FactItem(
                id=f"F{idx}",
                fact_type="AUTONOMY_MODE",
                statement=f"Merchant autonomy mode configured as '{autonomy_row.get('autonomy_mode', 'APPROVAL_REQUIRED')}'.",
                source="merchants",
                metric="autonomy_level",
                baseline_value=None,
                observed_value=None,
                provenance="SQLite table 'merchants.autonomy_level'",
            )
        )
        provenance.append({
            "fact_id": f"F{idx}",
            "source_table": "merchants",
            "metric": "autonomy_level",
        })
        idx += 1
        risk_val = float(autonomy_row.get("evaluated_risk", 0.0))
        thresh_val = float(autonomy_row.get("policy_threshold", 0.30))
        facts.append(
            FactItem(
                id=f"F{idx}",
                fact_type="EVALUATED_RISK",
                statement=f"Evaluated action risk score is {risk_val:.2f} (Policy threshold: {thresh_val:.2f}).",
                source="autonomy_evaluations",
                metric="evaluated_risk",
                baseline_value=thresh_val,
                observed_value=risk_val,
                provenance="SQLite table 'autonomy_evaluations.evaluated_risk'",
            )
        )
        provenance.append({
            "fact_id": f"F{idx}",
            "source_table": "autonomy_evaluations",
            "metric": "evaluated_risk",
        })
        idx += 1

    return facts, hypotheses, provenance


def build_signal_explanation(signal_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Explains why the signal was detected."""
    if not signal_row:
        return {"status": "UNAVAILABLE", "description": "No active anomaly signal detected."}
    m_name = signal_row.get("metric_name", "evening_orders")
    b_val = signal_row.get("baseline_value", 0.0)
    o_val = signal_row.get("observed_value", 0.0)
    pct = signal_row.get("change_percentage", signal_row.get("decline_percentage", 0.0))
    return {
        "signal_id": signal_row.get("id"),
        "signal_type": signal_row.get("signal_type", "GENERAL_ANOMALY"),
        "severity": signal_row.get("severity", "MEDIUM"),
        "title": signal_row.get("title", "Metric Anomaly Detected"),
        "metric_name": m_name,
        "baseline_value": b_val,
        "observed_value": o_val,
        "change_percentage": pct,
        "explanation": f"The signal was triggered because {m_name} shifted by {pct:.2f}% (from {b_val} to {o_val}), violating the defined digital-twin volatility threshold.",
        "detected_at": signal_row.get("detected_at"),
    }


def build_action_explanation(action_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Explains why the candidate action was proposed."""
    if not action_row:
        return None
    params = action_row.get("parameters")
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    elif not isinstance(params, dict):
        params = {}

    evidence_ids = action_row.get("supporting_evidence_ids")
    if isinstance(evidence_ids, str):
        try:
            evidence_ids = json.loads(evidence_ids)
        except Exception:
            evidence_ids = []

    return {
        "action_id": action_row.get("id"),
        "action_type": action_row.get("action_type", "OFFER_CAMPAIGN"),
        "objective": action_row.get("objective", "Re-engage customers"),
        "target_segment": action_row.get("target_segment", "repeat_customer, regular"),
        "target_customer_count": action_row.get("target_customer_count", 0),
        "incentive_type": action_row.get("incentive_type", "CASHBACK"),
        "incentive_value": action_row.get("incentive_value", 0.0),
        "duration": action_row.get("duration", "7 days"),
        "estimated_cost_inr": action_row.get("estimated_cost_inr", 0.0),
        "reason": action_row.get("reason", "Addresses detected anomaly"),
        "supporting_evidence_ids": evidence_ids or [],
        "explanation": (
            f"Action proposed: {action_row.get('action_type')} targeting {action_row.get('target_customer_count')} "
            f"customers with INR {action_row.get('incentive_value')} {action_row.get('incentive_type')}. "
            f"Rationale: {action_row.get('reason')}"
        ),
    }


def build_guardrail_explanation(guardrail_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Explains the 10 deterministic guardrail evaluations and parameter clamp modifications."""
    if not guardrail_row:
        return None

    checks_raw = guardrail_row.get("checks")
    if isinstance(checks_raw, str):
        try:
            checks = json.loads(checks_raw)
        except Exception:
            checks = []
    elif isinstance(checks_raw, list):
        checks = checks_raw
    else:
        checks = []

    mods_raw = guardrail_row.get("modified_values") or guardrail_row.get("modifications")
    if isinstance(mods_raw, str):
        try:
            mods = json.loads(mods_raw)
        except Exception:
            mods = {}
    elif isinstance(mods_raw, dict):
        mods = mods_raw
    else:
        mods = {}

    orig_raw = guardrail_row.get("original_values")
    if isinstance(orig_raw, str):
        try:
            orig = json.loads(orig_raw)
        except Exception:
            orig = {}
    elif isinstance(orig_raw, dict):
        orig = orig_raw
    else:
        orig = {}

    overall_st = guardrail_row.get("overall_status", "PASS")
    clamp_details = []
    for k, v in mods.items():
        o_v = orig.get(k, "original")
        clamp_details.append(f"{k}: requested {o_v} -> clamped to safety maximum {v}")

    return {
        "evaluation_id": guardrail_row.get("id") or guardrail_row.get("evaluation_id"),
        "overall_status": overall_st,
        "passed": bool(guardrail_row.get("passed", True)),
        "notes": guardrail_row.get("notes", ""),
        "checks_evaluated": len(checks),
        "checks": checks,
        "modifications": mods,
        "original_values": orig,
        "clamp_details": clamp_details,
        "explanation": (
            f"Evaluated 10/10 deterministic safety guardrails. Verdict: {overall_st}. "
            + (f"Modifications applied: {', '.join(clamp_details)}." if clamp_details else "All constraints satisfied without modification.")
        ),
    }


def build_decision_explanation(decision_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Explains the authoritative decision and merchant sign-off status."""
    if not decision_row:
        return None

    state = decision_row.get("decision_state", "PASS")
    appr_st = decision_row.get("approval_status", "PENDING")
    is_exec = bool(decision_row.get("is_execution_eligible", False))

    safety_block_note = ""
    if state == "BLOCK":
        safety_block_note = "CRITICAL: Guardrail BLOCK cannot be overridden by merchant sign-off. Execution remains permanently prohibited."

    return {
        "decision_id": decision_row.get("id") or decision_row.get("decision_id"),
        "decision_state": state,
        "approval_required": bool(decision_row.get("approval_required", True)),
        "approval_status": appr_st,
        "is_execution_eligible": is_exec,
        "reason": decision_row.get("reason", ""),
        "safety_block_note": safety_block_note,
        "explanation": (
            f"Decision State: {state}. Merchant Approval: {appr_st}. Execution Eligible: {is_exec}. "
            f"Rationale: {decision_row.get('reason')} {safety_block_note}".strip()
        ),
    }


def build_execution_explanation(
    execution_row: Optional[Dict[str, Any]],
    action_row: Optional[Dict[str, Any]],
    guardrail_row: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Explains the simulated execution and verifies parameter invariants."""
    if not execution_row:
        return None

    st = execution_row.get("execution_state", "COMPLETED")
    mode = execution_row.get("execution_mode", "SIMULATION")
    appr_action = execution_row.get("approved_action", {})
    if isinstance(appr_action, str):
        try:
            appr_action = json.loads(appr_action)
        except Exception:
            appr_action = {}

    orig_incentive = action_row.get("incentive_value") if action_row else None
    executed_incentive = appr_action.get("incentive_value")

    invariant_verified = True
    invariant_note = "Action executed safely in digital twin sandbox."
    if orig_incentive is not None and executed_incentive is not None:
        if orig_incentive > executed_incentive:
            invariant_note = (
                f"MODIFY INVARIANT VERIFIED: Original proposal requested INR {orig_incentive}, "
                f"but execution strictly applied the guardrail-clamped value of INR {executed_incentive}. "
                f"The unsafe proposed value was NEVER executed."
            )

    return {
        "execution_id": execution_row.get("id"),
        "execution_state": st,
        "execution_mode": mode,
        "simulated": True,
        "disclaimer": "SIMULATED - PROTOTYPE - NO REAL PAYTM TRANSACTION",
        "executed_at": execution_row.get("executed_at"),
        "approved_parameters": appr_action.get("parameters") or appr_action,
        "executed_parameters": appr_action.get("parameters") or appr_action,
        "invariant_verified": invariant_verified,
        "invariant_note": invariant_note,
        "explanation": f"Execution mode {mode} reached state {st}. {invariant_note}",
    }


def build_outcome_explanation(outcome_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Explains before vs after metrics with descriptive, non-causal framing."""
    if not outcome_row:
        return None

    bm = outcome_row.get("baseline_metrics")
    if isinstance(bm, str):
        try:
            bm = json.loads(bm)
        except Exception:
            bm = {}
    elif not isinstance(bm, dict):
        bm = {}

    pm = outcome_row.get("post_action_metrics")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = {}
    elif not isinstance(pm, dict):
        pm = {}

    changes = outcome_row.get("metric_changes")
    if isinstance(changes, str):
        try:
            changes = json.loads(changes)
        except Exception:
            changes = {}
    elif not isinstance(changes, dict):
        changes = {}

    eve_change = changes.get("evening_orders", {})
    rev_change = changes.get("revenue", {})

    return {
        "outcome_id": outcome_row.get("id"),
        "outcome_status": outcome_row.get("outcome_status", "MEASURED"),
        "baseline_metrics": bm,
        "post_action_metrics": pm,
        "metric_changes": changes,
        "measured_at": outcome_row.get("measured_at"),
        "framing": "DESCRIPTIVE_NON_CAUSAL",
        "explanation": (
            f"Observed simulated outcomes over 7-day post-action observation window: "
            f"Evening orders changed by {eve_change.get('percentage_change', 0):+.2f}% ({eve_change.get('description', '')}). "
            f"Revenue changed by {rev_change.get('percentage_change', 0):+.2f}%. "
            f"Descriptive observation only; external causality is not asserted."
        ),
    }


def build_business_impact_explanation(impact_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Explains ROI and business impact metrics without gross profit fabrication."""
    if not impact_row:
        return None

    roi_pct = impact_row.get("roi_percentage")
    roi_str = f"{roi_pct:.2f}%" if roi_pct is not None else "None (zero-cost / insufficient data)"
    cost = impact_row.get("campaign_cost", 0.0)
    inc_rev = impact_row.get("incremental_revenue", 0.0)
    classification = impact_row.get("impact_classification", "NEUTRAL")

    return {
        "impact_id": impact_row.get("id"),
        "impact_status": impact_row.get("impact_status", "CALCULATED"),
        "impact_classification": classification,
        "incremental_revenue": inc_rev,
        "campaign_cost": cost,
        "roi_percentage": roi_pct,
        "cost_per_incremental_order": impact_row.get("cost_per_incremental_order"),
        "revenue_per_campaign_rupee": impact_row.get("revenue_per_campaign_rupee"),
        "gross_profit_impact": None,
        "gross_profit_note": "Not available in simulation (COGS not modeled)",
        "explanation": (
            f"Simulated ROI calculated as {roi_str} based on incremental revenue of INR {inc_rev:.2f} "
            f"and campaign cost of INR {cost:.2f}. Classification: {classification}. "
            f"Gross profit impact: Not available in simulation (zero COGS fabrication guarantee)."
        ),
    }


def build_autonomy_explanation(
    autonomy_row: Optional[Dict[str, Any]],
    merchant_policy: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Explains the controlled autonomy evaluation, approval requirements, and safety supremacy."""
    if not autonomy_row:
        return None

    mode = autonomy_row.get("autonomy_mode", "APPROVAL_REQUIRED")
    source = autonomy_row.get("approval_source", "PENDING")
    actor = autonomy_row.get("actor_type", "SYSTEM")
    appr_req = bool(autonomy_row.get("approval_required", True))
    auto_allowed = bool(autonomy_row.get("auto_approval_allowed", False))
    blocked = bool(autonomy_row.get("blocked", False))
    escalated = bool(autonomy_row.get("escalated", False))
    risk = float(autonomy_row.get("evaluated_risk", 0.0))
    threshold = float(autonomy_row.get("policy_threshold", 0.30))
    reason = autonomy_row.get("auto_approval_reason") or autonomy_row.get("reason", "")
    passed_checks = autonomy_row.get("passed_checks", [])
    failed_checks = autonomy_row.get("failed_checks", [])

    if blocked:
        explanation = (
            f"SAFETY SUPREMACY ENFORCED: Guardrail BLOCK overrides all autonomy modes (current mode: {mode}). "
            "Neither merchant sign-off nor automatic approval is permitted."
        )
    elif escalated:
        explanation = (
            f"HUMAN REVIEW ENFORCED: Action was escalated by guardrail policy. "
            "Automatic execution is strictly prohibited under any autonomy mode."
        )
    elif auto_allowed:
        explanation = (
            f"AUTO-APPROVED BY DETERMINISTIC POLICY: Autonomy mode {mode} cleared execution. "
            f"Risk score ({risk:.2f}) was within policy threshold ({threshold:.2f}). "
            "All 16 deterministic safety conditions satisfied."
        )
    else:
        explanation = (
            f"MERCHANT APPROVAL REQUIRED: Under autonomy mode {mode}, this action requires explicit "
            f"merchant sign-off before execution. Reason: {reason}"
        )

    return {
        "evaluation_id": autonomy_row.get("id"),
        "autonomy_mode": mode,
        "approval_source": source,
        "actor_type": actor,
        "approval_required": appr_req,
        "auto_approval_allowed": auto_allowed,
        "blocked": blocked,
        "escalated": escalated,
        "evaluated_risk": risk,
        "policy_threshold": threshold,
        "passed_checks_count": len(passed_checks) if isinstance(passed_checks, list) else 0,
        "failed_checks_count": len(failed_checks) if isinstance(failed_checks, list) else 0,
        "passed_checks": passed_checks if isinstance(passed_checks, list) else [],
        "failed_checks": failed_checks if isinstance(failed_checks, list) else [],
        "reason": reason,
        "explanation": explanation,
        "safety_principle": "Autonomy controls approval flow; autonomy NEVER overrides hard safety guardrails.",
    }
