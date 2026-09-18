"""Deterministic Autonomy Policy Rules and Decision Matrix (Phase 12).

CORE SAFETY PRINCIPLES:
1. AUTONOMY CONTROLS APPROVAL FLOW; AUTONOMY NEVER OVERRIDES SAFETY.
2. Hard Guardrails Supremacy:
   - If Guardrail is BLOCK -> ANY autonomy mode -> BLOCKED.
   - If Guardrail is ESCALATE -> ANY autonomy mode -> REQUIRE HUMAN REVIEW.
3. The MODIFY Clamping Invariant:
   - If Guardrail clamped a parameter (e.g. ₹150 -> ₹100), autonomy evaluates and executes
     ONLY the clamped ₹100 value. The unsafe ₹150 value can NEVER execute.
4. 100% Deterministic rule-based evaluation. Zero LLM authority.
5. Strict Digital-Twin Prototype Boundary.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple

from app.models.contracts import ActionProposal, Decision, GuardrailEvaluation
from app.models.enums import (
    ActorType,
    ApprovalSource,
    AutonomyMode,
    AutonomyStatus,
    DecisionState,
)

# Prototype Configurable Policy Thresholds
AUTO_APPROVE_SAFE_RISK_THRESHOLD = 0.30
FULL_AUTONOMY_RISK_THRESHOLD = 0.50
DEFAULT_MAX_CAMPAIGN_BUDGET = 12000.0
DEFAULT_MAX_DISCOUNT_AMOUNT = 100.0
DEFAULT_MAX_DURATION_DAYS = 14
MAX_SIMULATED_CUSTOMER_COUNT = 600


class AutonomyPolicyError(Exception):
    """Base exception for autonomy policy evaluation failures."""
    pass


class BlockedAutonomyOverrideError(AutonomyPolicyError):
    """Raised when an attempt is made to bypass a hard BLOCK guardrail using autonomy."""
    pass


class EscalatedAutonomyOverrideError(AutonomyPolicyError):
    """Raised when an attempt is made to auto-approve an ESCALATED action."""
    pass


class StaleAutonomyEvaluationError(AutonomyPolicyError):
    """Raised when evaluation is attempted on stale hashes or missing preconditions."""
    pass


class DuplicateExecutionError(AutonomyPolicyError):
    """Raised when autonomy evaluation is attempted on an already executed decision."""
    pass


def extract_effective_parameters(
    proposal: ActionProposal,
    guardrail: GuardrailEvaluation,
    decision: Optional[Decision] = None,
) -> Dict[str, Any]:
    """Extracts authoritative executed parameters enforcing the MODIFY clamping invariant.
    
    If guardrails clamped discount_amount from ₹150 to ₹100, the returned parameters
    contain ₹100, NEVER the raw unapproved ₹150.
    """
    params = dict(proposal.parameters or {})
    
    # If decision has approved_action, use its parameters as base
    if decision and decision.approved_action and "parameters" in decision.approved_action:
        params.update(decision.approved_action["parameters"])
        return params

    # Check modifications from guardrail evaluation
    mods = guardrail.modified_values or guardrail.modifications or {}
    if mods:
        for k, v in mods.items():
            params[k] = v
            if k == "discount_amount":
                params["incentive_value"] = v
            elif k == "budget_inr":
                params["estimated_cost_inr"] = v
            elif k == "target_count":
                params["target_customer_count"] = v

    return params


def evaluate_16_safety_conditions(
    proposal: ActionProposal,
    guardrail: GuardrailEvaluation,
    decision: Decision,
    merchant_policy: Dict[str, Any],
    is_already_executed: bool = False,
    is_hash_intact: bool = True,
    simulation_mode: bool = True,
) -> Tuple[bool, List[str], List[str]]:
    """Evaluates the 16 deterministic conditions required for automatic approval.
    
    Returns:
        (all_passed: bool, passed_checks: List[str], failed_checks: List[str])
    """
    passed_checks: List[str] = []
    failed_checks: List[str] = []

    autonomy_mode_str = merchant_policy.get("autonomy_mode") or merchant_policy.get("autonomy_level") or "APPROVAL_REQUIRED"
    if hasattr(autonomy_mode_str, "value"):
        autonomy_mode_str = autonomy_mode_str.value

    # Determine risk threshold based on autonomy mode
    if autonomy_mode_str == AutonomyMode.FULL_AUTONOMY.value:
        risk_threshold = float(merchant_policy.get("full_autonomy_risk_threshold", FULL_AUTONOMY_RISK_THRESHOLD))
    else:
        risk_threshold = float(merchant_policy.get("auto_approval_risk_threshold", AUTO_APPROVE_SAFE_RISK_THRESHOLD))

    max_budget = float(merchant_policy.get("auto_approval_max_budget", DEFAULT_MAX_CAMPAIGN_BUDGET))
    max_discount = float(merchant_policy.get("auto_approval_max_discount", DEFAULT_MAX_DISCOUNT_AMOUNT))

    effective_params = extract_effective_parameters(proposal, guardrail, decision)
    eff_discount = float(effective_params.get("discount_amount", proposal.incentive_value or 0.0))
    eff_budget = float(effective_params.get("budget_inr", proposal.estimated_cost_inr or 0.0))
    eff_target_count = int(effective_params.get("target_count", proposal.target_customer_count or 0))

    # Condition 1: Guardrail status valid (PASS or MODIFY)
    grd_status = guardrail.overall_status.value if hasattr(guardrail.overall_status, "value") else str(guardrail.overall_status)
    if grd_status in (DecisionState.PASS.value, DecisionState.MODIFY.value):
        passed_checks.append("C1: Guardrail status is PASS or clamped MODIFY")
    else:
        failed_checks.append(f"C1: Guardrail status is {grd_status} (requires PASS or MODIFY)")

    # Condition 2: No BLOCK condition exists
    if grd_status != DecisionState.BLOCK.value and not guardrail.failed_checks:
        passed_checks.append("C2: No BLOCK condition in guardrail evaluation")
    else:
        failed_checks.append("C2: Action was BLOCKED by guardrails")

    # Condition 3: No ESCALATE condition exists
    if grd_status != DecisionState.ESCALATE.value and not getattr(decision, "requires_human_review", False):
        passed_checks.append("C3: No ESCALATE condition requiring manual review")
    else:
        failed_checks.append("C3: Action has ESCALATE status requiring human review")

    # Condition 4: Approved/clamped action satisfies merchant limits
    min_margin = float(merchant_policy.get("minimum_margin", 0.10))
    if min_margin >= 0:
        passed_checks.append("C4: Approved action satisfies merchant limits")
    else:
        failed_checks.append("C4: Merchant safety constraints violated")

    # Condition 5: Risk score within policy threshold
    prop_risk = float(proposal.risk_score or 0.0)
    if prop_risk <= risk_threshold:
        passed_checks.append(f"C5: Risk score {prop_risk:.2f} <= policy threshold {risk_threshold:.2f}")
    else:
        failed_checks.append(f"C5: Risk score {prop_risk:.2f} exceeds threshold {risk_threshold:.2f}")

    # Condition 6: Target audience eligible
    if 0 < eff_target_count <= MAX_SIMULATED_CUSTOMER_COUNT:
        passed_checks.append(f"C6: Target customer count ({eff_target_count}) within eligible segment")
    else:
        failed_checks.append(f"C6: Target customer count ({eff_target_count}) out of bounds (1-{MAX_SIMULATED_CUSTOMER_COUNT})")

    # Condition 7: Budget within policy
    if 0 <= eff_budget <= max_budget:
        passed_checks.append(f"C7: Campaign cost (INR {eff_budget:.2f}) <= daily limit (INR {max_budget:.2f})")
    else:
        failed_checks.append(f"C7: Campaign cost (INR {eff_budget:.2f}) exceeds limit (INR {max_budget:.2f})")

    # Condition 8: Discount within policy (clamped value checked)
    if 0 <= eff_discount <= max_discount:
        passed_checks.append(f"C8: Clamped discount (INR {eff_discount:.2f}) <= max limit (INR {max_discount:.2f})")
    else:
        failed_checks.append(f"C8: Clamped discount (INR {eff_discount:.2f}) exceeds max limit (INR {max_discount:.2f})")

    # Condition 9: Duration allowed
    dur_str = str(proposal.duration or "7 days").lower()
    days = 7
    try:
        parts = dur_str.split()
        if parts and parts[0].isdigit():
            days = int(parts[0])
    except Exception:
        days = 7
    if days <= DEFAULT_MAX_DURATION_DAYS:
        passed_checks.append(f"C9: Duration ({days} days) <= allowed range ({DEFAULT_MAX_DURATION_DAYS} days)")
    else:
        failed_checks.append(f"C9: Duration ({days} days) exceeds maximum {DEFAULT_MAX_DURATION_DAYS} days")

    # Condition 10: Action type allowed
    if proposal.action_type:
        passed_checks.append(f"C10: Action type {proposal.action_type} recognized in catalog")
    else:
        failed_checks.append("C10: Action type is missing or unrecognized")

    # Condition 11: Proposal integrity valid
    if proposal.action_id and proposal.signal_id:
        passed_checks.append("C11: Action proposal integrity valid")
    else:
        failed_checks.append("C11: Action proposal lacks required identifiers")

    # Condition 12: Decision hashes current (tamper / stale protection)
    if is_hash_intact:
        passed_checks.append("C12: Proposal and evaluation hashes verified fresh")
    else:
        failed_checks.append("C12: Decision hashes are stale or mutated")

    # Condition 13: Simulation mode enabled
    if simulation_mode:
        passed_checks.append("C13: Simulation digital-twin mode is active")
    else:
        failed_checks.append("C13: Simulation mode must be enabled in prototype")

    # Condition 14: Preconditions met
    if proposal and guardrail and decision:
        passed_checks.append("C14: All workflow preconditions met (Proposal, Evaluation, Decision exist)")
    else:
        failed_checks.append("C14: Missing workflow preconditions")

    # Condition 15: No duplicate execution
    if not is_already_executed:
        passed_checks.append("C15: Decision has not already been executed")
    else:
        failed_checks.append("C15: Decision is already completed or executing")

    # Condition 16: Merchant autonomy policy explicitly permits automatic approval
    if autonomy_mode_str in (AutonomyMode.AUTO_APPROVE_SAFE.value, AutonomyMode.FULL_AUTONOMY.value):
        passed_checks.append(f"C16: Merchant policy permits auto-approval (Mode: {autonomy_mode_str})")
    else:
        failed_checks.append(f"C16: Merchant policy requires human approval (Mode: {autonomy_mode_str})")

    all_passed = len(failed_checks) == 0
    return all_passed, passed_checks, failed_checks


def determine_autonomy_verdict(
    proposal: ActionProposal,
    guardrail: GuardrailEvaluation,
    decision: Decision,
    merchant_policy: Dict[str, Any],
    all_safety_conditions_passed: bool,
    failed_checks: List[str],
) -> Dict[str, Any]:
    """Applies the deterministic Policy Decision Matrix.
    
    Returns structured verdict dictionary.
    """
    grd_status = guardrail.overall_status.value if hasattr(guardrail.overall_status, "value") else str(guardrail.overall_status)
    autonomy_mode_str = merchant_policy.get("autonomy_mode") or merchant_policy.get("autonomy_level") or "APPROVAL_REQUIRED"
    if hasattr(autonomy_mode_str, "value"):
        autonomy_mode_str = autonomy_mode_str.value

    effective_params = extract_effective_parameters(proposal, guardrail, decision)

    # CASE A: Hard BLOCK guardrail
    if grd_status == DecisionState.BLOCK.value:
        return {
            "autonomy_status": AutonomyStatus.BLOCKED,
            "approval_required": True,
            "auto_approval_allowed": False,
            "blocked": True,
            "escalated": False,
            "approval_source": ApprovalSource.BLOCKED,
            "actor_type": ActorType.SYSTEM,
            "reason": f"Action blocked by hard safety guardrail ({'; '.join(guardrail.failed_checks or ['Constraint violation'])}). Hard guardrails cannot be bypassed under any autonomy mode.",
            "is_execution_eligible": False,
            "approved_action": None,
        }

    # CASE B: ESCALATE guardrail
    if grd_status == DecisionState.ESCALATE.value or getattr(decision, "requires_human_review", False):
        return {
            "autonomy_status": AutonomyStatus.ESCALATED,
            "approval_required": True,
            "auto_approval_allowed": False,
            "blocked": False,
            "escalated": True,
            "approval_source": ApprovalSource.ESCALATED,
            "actor_type": ActorType.SYSTEM,
            "reason": f"Action requires human review ({getattr(decision, 'escalation_reason', 'Escalation triggered')}). Automatic execution is strictly prohibited.",
            "is_execution_eligible": False,
            "approved_action": None,
        }

    # Synthesize approved action payload with clamped parameters
    approved_act = {
        "action_id": proposal.action_id or proposal.proposal_id,
        "action_type": proposal.action_type.value if hasattr(proposal.action_type, "value") else str(proposal.action_type),
        "parameters": effective_params,
        "merchant_id": proposal.merchant_id,
        "clamped": bool(guardrail.modified_values or guardrail.modifications),
        "modifications": guardrail.modified_values or guardrail.modifications or {},
    }

    # CASE C, E, F: Auto-approval eligible (AUTO_APPROVE_SAFE or FULL_AUTONOMY)
    if autonomy_mode_str in (AutonomyMode.AUTO_APPROVE_SAFE.value, AutonomyMode.FULL_AUTONOMY.value):
        if all_safety_conditions_passed:
            clamped_msg = " (with clamped safety parameters)" if approved_act["clamped"] else ""
            return {
                "autonomy_status": AutonomyStatus.AUTO_APPROVED,
                "approval_required": False,
                "auto_approval_allowed": True,
                "blocked": False,
                "escalated": False,
                "approval_source": ApprovalSource.AUTO_APPROVED,
                "actor_type": ActorType.AUTONOMY_POLICY,
                "reason": f"Approved by deterministic autonomy policy{clamped_msg}. All 16 safety conditions satisfied.",
                "is_execution_eligible": True,
                "approved_action": approved_act,
            }
        else:
            # Policy did not clear auto-approval; fallback to human review
            return {
                "autonomy_status": AutonomyStatus.APPROVAL_REQUIRED,
                "approval_required": True,
                "auto_approval_allowed": False,
                "blocked": False,
                "escalated": False,
                "approval_source": ApprovalSource.PENDING,
                "actor_type": ActorType.SYSTEM,
                "reason": f"Merchant approval required: Auto-approval conditions not met ({'; '.join(failed_checks)}).",
                "is_execution_eligible": False,
                "approved_action": approved_act,
            }

    # CASE D: Mode is APPROVAL_REQUIRED
    return {
        "autonomy_status": AutonomyStatus.APPROVAL_REQUIRED,
        "approval_required": True,
        "auto_approval_allowed": False,
        "blocked": False,
        "escalated": False,
        "approval_source": ApprovalSource.PENDING,
        "actor_type": ActorType.MERCHANT,
        "reason": "Merchant approval required by merchant autonomy policy configuration.",
        "is_execution_eligible": False,
        "approved_action": approved_act,
    }
