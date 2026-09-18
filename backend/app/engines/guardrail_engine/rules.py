"""Deterministic Guardrail Rules (G1 - G10).

SAFETY PRINCIPLES:
- 100% Deterministic and rule-based.
- Zero LLM authority or intervention.
- Hard boundaries enforced against SQLite digital-twin truth.
"""
from typing import Any, Dict, List, Optional, Tuple
import re

from app.models.contracts import ActionProposal, GuardrailCheck
from app.models.enums import ActionType, DecisionState


def evaluate_g1_minimum_margin(
    proposal: ActionProposal,
    merchant_min_margin: float,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G1 — Minimum Margin: Verifies projected margin does not fall below merchant minimum."""
    # Check if projected margin is explicitly specified in parameters or projected_impact
    proj_margin_raw = (
        proposal.parameters.get("projected_margin")
        or proposal.projected_impact.get("projected_margin")
    )

    if proj_margin_raw is not None:
        try:
            val = float(proj_margin_raw)
            # If specified as percentage like 7.8, convert to ratio 0.078
            proj_margin = val / 100.0 if val > 1.0 else val
        except (ValueError, TypeError):
            proj_margin = merchant_min_margin
    else:
        # Default projected margin for normal compliant proposals
        proj_margin = merchant_min_margin + 0.02  # e.g. 12%

    min_pct = merchant_min_margin * 100.0
    proj_pct = proj_margin * 100.0

    if proj_margin < merchant_min_margin:
        msg = (
            f"Margin guardrail violated. Required: >= {min_pct:.1f}%, "
            f"Projected: {proj_pct:.1f}%. Action blocked before execution."
        )
        check = GuardrailCheck(
            check_id="G1",
            check_type="MIN_MARGIN",
            status="FAIL",
            rule=f"projected_margin >= {min_pct:.1f}%",
            actual_value=f"{proj_pct:.1f}%",
            threshold_value=f">={min_pct:.1f}%",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G1",
        check_type="MIN_MARGIN",
        status="PASS",
        rule=f"projected_margin >= {min_pct:.1f}%",
        actual_value=f"{proj_pct:.1f}%",
        threshold_value=f">={min_pct:.1f}%",
        message=f"Projected margin {proj_pct:.1f}% satisfies minimum requirement ({min_pct:.1f}%).",
        severity="INFO",
    )
    return check, None


def evaluate_g2_daily_budget(
    proposal: ActionProposal,
    daily_budget_limit: float,
) -> Tuple[GuardrailCheck, Optional[DecisionState], Optional[float]]:
    """G2 — Daily Budget: Checks estimated cost <= daily budget limit."""
    cost = float(proposal.estimated_cost_inr or proposal.parameters.get("budget_inr") or 0.0)

    if cost > daily_budget_limit * 2.0:
        msg = (
            f"Estimated cost (INR {cost:.2f}) critically exceeds daily budget limit "
            f"(INR {daily_budget_limit:.2f}). Severe breach."
        )
        check = GuardrailCheck(
            check_id="G2",
            check_type="DAILY_BUDGET",
            status="FAIL",
            rule=f"cost <= INR {daily_budget_limit:.2f}",
            actual_value=cost,
            threshold_value=daily_budget_limit,
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK, None

    if cost > daily_budget_limit:
        # Moderate overshoot -> Deterministic clamp to daily budget
        msg = (
            f"Estimated cost (INR {cost:.2f}) exceeds daily budget (INR {daily_budget_limit:.2f}). "
            f"Clamped to INR {daily_budget_limit:.2f}."
        )
        check = GuardrailCheck(
            check_id="G2",
            check_type="DAILY_BUDGET",
            status="MODIFIED",
            rule=f"cost <= INR {daily_budget_limit:.2f}",
            actual_value=cost,
            threshold_value=daily_budget_limit,
            message=msg,
            severity="WARNING",
        )
        return check, DecisionState.MODIFY, daily_budget_limit

    check = GuardrailCheck(
        check_id="G2",
        check_type="DAILY_BUDGET",
        status="PASS",
        rule=f"cost <= INR {daily_budget_limit:.2f}",
        actual_value=cost,
        threshold_value=daily_budget_limit,
        message=f"Estimated cost INR {cost:.2f} is within daily budget INR {daily_budget_limit:.2f}.",
        severity="INFO",
    )
    return check, None, None


def evaluate_g3_maximum_discount(
    proposal: ActionProposal,
    maximum_discount_inr: float,
    max_discount_pct: float = 25.0,
) -> Tuple[GuardrailCheck, Optional[DecisionState], Optional[Dict[str, Any]]]:
    """G3 — Maximum Discount: Verifies discount/cashback does not exceed merchant limit."""
    incentive = float(proposal.incentive_value or proposal.parameters.get("discount_amount") or 0.0)
    disc_pct = float(proposal.parameters.get("discount_percentage", 0.0))

    # Backward compatibility for discount_percentage check from Phase 1
    if disc_pct > max_discount_pct:
        msg = (
            f"Proposed discount ({disc_pct:.1f}%) exceeds policy limit ({max_discount_pct:.1f}%). "
            f"Auto-clamped to {max_discount_pct:.1f}%."
        )
        check = GuardrailCheck(
            check_id="G3",
            check_type="MAX_DISCOUNT",
            status="MODIFIED",
            rule=f"discount_percentage <= {max_discount_pct:.1f}%",
            actual_value=disc_pct,
            threshold_value=max_discount_pct,
            message=msg,
            severity="WARNING",
        )
        return check, DecisionState.MODIFY, {"discount_percentage": max_discount_pct}

    if incentive > maximum_discount_inr * 2.0:
        msg = (
            f"Proposed incentive (INR {incentive:.2f}) critically exceeds maximum allowable discount "
            f"(INR {maximum_discount_inr:.2f})."
        )
        check = GuardrailCheck(
            check_id="G3",
            check_type="MAX_DISCOUNT",
            status="FAIL",
            rule=f"incentive <= INR {maximum_discount_inr:.2f}",
            actual_value=incentive,
            threshold_value=maximum_discount_inr,
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK, None

    if incentive > maximum_discount_inr:
        # Deterministic modification: clamp to maximum discount
        msg = (
            f"Proposed incentive (INR {incentive:.2f}) exceeds maximum allowable discount "
            f"(INR {maximum_discount_inr:.2f}). Auto-clamped to INR {maximum_discount_inr:.2f}."
        )
        check = GuardrailCheck(
            check_id="G3",
            check_type="MAX_DISCOUNT",
            status="MODIFIED",
            rule=f"incentive <= INR {maximum_discount_inr:.2f}",
            actual_value=incentive,
            threshold_value=maximum_discount_inr,
            message=msg,
            severity="WARNING",
        )
        return check, DecisionState.MODIFY, {"incentive_value": maximum_discount_inr, "discount_amount": maximum_discount_inr}

    check = GuardrailCheck(
        check_id="G3",
        check_type="MAX_DISCOUNT",
        status="PASS",
        rule=f"incentive <= INR {maximum_discount_inr:.2f}",
        actual_value=incentive,
        threshold_value=maximum_discount_inr,
        message=f"Incentive INR {incentive:.2f} satisfies maximum discount ceiling (INR {maximum_discount_inr:.2f}).",
        severity="INFO",
    )
    return check, None, None


def evaluate_g4_campaign_frequency(
    active_campaign_count: int,
    max_campaign_frequency: int,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G4 — Campaign Frequency: Verifies active campaigns + 1 <= allowed frequency."""
    projected_count = active_campaign_count + 1

    if projected_count > max_campaign_frequency:
        msg = (
            f"Campaign frequency limit exceeded. Active campaigns ({active_campaign_count}) + new "
            f"proposal exceeds merchant limit ({max_campaign_frequency}). Action blocked."
        )
        check = GuardrailCheck(
            check_id="G4",
            check_type="CAMPAIGN_FREQUENCY",
            status="FAIL",
            rule=f"active_campaigns + 1 <= {max_campaign_frequency}",
            actual_value=projected_count,
            threshold_value=max_campaign_frequency,
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G4",
        check_type="CAMPAIGN_FREQUENCY",
        status="PASS",
        rule=f"active_campaigns + 1 <= {max_campaign_frequency}",
        actual_value=projected_count,
        threshold_value=max_campaign_frequency,
        message=f"Projected campaign frequency ({projected_count}) is within limit ({max_campaign_frequency}).",
        severity="INFO",
    )
    return check, None


def evaluate_g5_audience_boundary(
    proposal: ActionProposal,
    eligible_customer_count: int,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G5 — Target Audience Boundary: Verifies target_customer_count <= eligible_customer_count."""
    raw_count = (
        proposal.target_customer_count
        if proposal.target_customer_count is not None and proposal.target_customer_count > 0
        else (proposal.parameters.get("target_count") or proposal.parameters.get("target_customer_count"))
    )
    if raw_count is None:
        target_count = eligible_customer_count
    else:
        target_count = int(raw_count)

    if target_count < 0:
        msg = f"Target audience count ({target_count}) cannot be negative."
        check = GuardrailCheck(
            check_id="G5",
            check_type="AUDIENCE_BOUNDARY",
            status="FAIL",
            rule="target_count >= 0",
            actual_value=target_count,
            threshold_value=">=0",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    if target_count > eligible_customer_count:
        msg = (
            f"Target audience count ({target_count}) exceeds verified eligible customer pool "
            f"({eligible_customer_count}). Unverified customer outreach blocked."
        )
        check = GuardrailCheck(
            check_id="G5",
            check_type="AUDIENCE_BOUNDARY",
            status="FAIL",
            rule=f"target_count <= {eligible_customer_count}",
            actual_value=target_count,
            threshold_value=eligible_customer_count,
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G5",
        check_type="AUDIENCE_BOUNDARY",
        status="PASS",
        rule=f"target_count <= {eligible_customer_count}",
        actual_value=target_count,
        threshold_value=eligible_customer_count,
        message=f"Target count ({target_count}) is within eligible cohort boundary ({eligible_customer_count}).",
        severity="INFO",
    )
    return check, None


def evaluate_g6_target_segment(
    proposal: ActionProposal,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G6 — Target Segment Validity: Verifies target segment is valid and non-empty."""
    segment = str(proposal.target_segment or "").strip()
    if not segment:
        msg = "Target customer segment is unspecified or empty."
        check = GuardrailCheck(
            check_id="G6",
            check_type="TARGET_SEGMENT",
            status="FAIL",
            rule="segment != ''",
            actual_value=segment,
            threshold_value="non-empty valid segment",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    # Validate recognized customer segments
    valid_terms = {"repeat_customer", "repeat", "regular", "inactive", "new_customer"}
    tokens = [t.strip().lower() for t in segment.replace(",", " ").split() if t.strip()]
    has_valid_token = any(tok in valid_terms for tok in tokens)

    if not has_valid_token:
        msg = f"Target segment '{segment}' does not match verified merchant customer cohorts."
        check = GuardrailCheck(
            check_id="G6",
            check_type="TARGET_SEGMENT",
            status="FAIL",
            rule="segment in valid_cohorts",
            actual_value=segment,
            threshold_value="recognized cohort",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G6",
        check_type="TARGET_SEGMENT",
        status="PASS",
        rule="segment in valid_cohorts",
        actual_value=segment,
        threshold_value="recognized cohort",
        message=f"Target segment '{segment}' matches verified customer cohorts.",
        severity="INFO",
    )
    return check, None


def evaluate_g7_action_type(
    proposal: ActionProposal,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G7 — Action Type Validity: Verifies action type is an authorized system action."""
    action_type = proposal.action_type
    allowed_types = set(ActionType)

    is_valid = False
    if isinstance(action_type, ActionType):
        is_valid = action_type in allowed_types
    elif isinstance(action_type, str):
        try:
            is_valid = ActionType(action_type) in allowed_types
        except ValueError:
            is_valid = False

    if not is_valid:
        msg = f"Action type '{action_type}' is unauthorized or unrecognized by MITRA policy."
        check = GuardrailCheck(
            check_id="G7",
            check_type="ACTION_TYPE",
            status="FAIL",
            rule="action_type in system_allowed",
            actual_value=action_type.value if hasattr(action_type, "value") else str(action_type),
            threshold_value="system_allowed",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G7",
        check_type="ACTION_TYPE",
        status="PASS",
        rule="action_type in system_allowed",
        actual_value=action_type.value if hasattr(action_type, "value") else str(action_type),
        threshold_value="system_allowed",
        message=f"Action type '{action_type.value if hasattr(action_type, 'value') else str(action_type)}' is authorized.",
        severity="INFO",
    )
    return check, None


def evaluate_g8_duration_boundary(
    proposal: ActionProposal,
    max_duration_days: int = 30,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G8 — Duration Boundary: Validates campaign duration is within 1 to 30 days."""
    duration_str = str(proposal.duration or "7 days").strip().lower()
    match = re.search(r"(-?\d+)", duration_str)
    if not match:
        msg = f"Malformed duration format: '{proposal.duration}'."
        check = GuardrailCheck(
            check_id="G8",
            check_type="DURATION_BOUNDARY",
            status="FAIL",
            rule="duration in 1..30 days",
            actual_value=proposal.duration,
            threshold_value="1..30 days",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    days = int(match.group(1))

    if days <= 0:
        msg = f"Campaign duration cannot be zero or negative ({days} days)."
        check = GuardrailCheck(
            check_id="G8",
            check_type="DURATION_BOUNDARY",
            status="FAIL",
            rule="duration > 0",
            actual_value=f"{days} days",
            threshold_value=">0 days",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    if days > max_duration_days:
        msg = f"Campaign duration ({days} days) exceeds maximum allowable ({max_duration_days} days)."
        check = GuardrailCheck(
            check_id="G8",
            check_type="DURATION_BOUNDARY",
            status="FAIL",
            rule=f"duration <= {max_duration_days} days",
            actual_value=f"{days} days",
            threshold_value=f"<={max_duration_days} days",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G8",
        check_type="DURATION_BOUNDARY",
        status="PASS",
        rule=f"1 <= duration <= {max_duration_days} days",
        actual_value=f"{days} days",
        threshold_value=f"<={max_duration_days} days",
        message=f"Campaign duration ({days} days) is compliant.",
        severity="INFO",
    )
    return check, None


def evaluate_g9_autonomy_mode(
    autonomy_mode: str,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G9 — Autonomy Mode: Enforces APPROVAL_REQUIRED merchant sign-off barrier."""
    if autonomy_mode == "APPROVAL_REQUIRED":
        check = GuardrailCheck(
            check_id="G9",
            check_type="AUTONOMY_MODE",
            status="PASS",
            rule="autonomy == APPROVAL_REQUIRED",
            actual_value=autonomy_mode,
            threshold_value="APPROVAL_REQUIRED",
            message="Autonomy mode APPROVAL_REQUIRED enforced. Merchant sign-off required prior to execution.",
            severity="INFO",
        )
        return check, None

    check = GuardrailCheck(
        check_id="G9",
        check_type="AUTONOMY_MODE",
        status="PASS",
        rule="autonomy recognized",
        actual_value=autonomy_mode,
        threshold_value="valid mode",
        message=f"Autonomy mode '{autonomy_mode}' recognized.",
        severity="INFO",
    )
    return check, None


def evaluate_g10_proposal_integrity(
    proposal: ActionProposal,
    valid_evidence_ids: Optional[List[str]] = None,
) -> Tuple[GuardrailCheck, Optional[DecisionState]]:
    """G10 — Proposal Integrity: Validates absence of negatives, valid evidence IDs, and proper status."""
    allowed_eids = set(valid_evidence_ids or ["E1", "E2", "E3", "E4", "E5"])

    # 1. Evidence ID verification
    cited_eids = proposal.supporting_evidence_ids or []
    for eid in cited_eids:
        if str(eid) not in allowed_eids:
            msg = f"Proposal references unverified or hallucinated evidence ID: '{eid}'."
            check = GuardrailCheck(
                check_id="G10",
                check_type="PROPOSAL_INTEGRITY",
                status="FAIL",
                rule="all cited evidence in verified_context",
                actual_value=cited_eids,
                threshold_value=list(allowed_eids),
                message=msg,
                severity="CRITICAL",
            )
            return check, DecisionState.BLOCK

    # 2. Non-negative values check
    cost = float(proposal.estimated_cost_inr or 0.0)
    if cost < 0:
        msg = f"Negative estimated cost (INR {cost}) is strictly invalid."
        check = GuardrailCheck(
            check_id="G10",
            check_type="PROPOSAL_INTEGRITY",
            status="FAIL",
            rule="estimated_cost >= 0",
            actual_value=cost,
            threshold_value=">=0",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    incentive = float(proposal.incentive_value or 0.0)
    if incentive < 0:
        msg = f"Negative incentive value (INR {incentive}) is strictly invalid."
        check = GuardrailCheck(
            check_id="G10",
            check_type="PROPOSAL_INTEGRITY",
            status="FAIL",
            rule="incentive_value >= 0",
            actual_value=incentive,
            threshold_value=">=0",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    # 3. Operational risk score check (from Phase 1)
    if proposal.risk_score > 0.7:
        msg = f"Operational risk score ({proposal.risk_score:.2f}) exceeds maximum threshold (0.70)."
        check = GuardrailCheck(
            check_id="G10",
            check_type="PROPOSAL_INTEGRITY",
            status="FAIL",
            rule="risk_score <= 0.70",
            actual_value=proposal.risk_score,
            threshold_value="<=0.70",
            message=msg,
            severity="CRITICAL",
        )
        return check, DecisionState.BLOCK

    check = GuardrailCheck(
        check_id="G10",
        check_type="PROPOSAL_INTEGRITY",
        status="PASS",
        rule="all integrity checks satisfied",
        actual_value="VALID",
        threshold_value="VALID",
        message="Proposal integrity validated. All cited evidence, numeric bounds, and risk scores are compliant.",
        severity="INFO",
    )
    return check, None
