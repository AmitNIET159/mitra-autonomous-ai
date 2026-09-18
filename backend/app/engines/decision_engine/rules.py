import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from app.models.contracts import ActionProposal, Decision, GuardrailEvaluation
from app.models.enums import ApprovalStatus, DecisionState


class DecisionRuleError(Exception):
    """Base exception for deterministic decision rule failures."""
    pass


class MissingGuardrailEvaluationError(DecisionRuleError):
    """Raised when decision creation is attempted without an existing GuardrailEvaluation."""
    pass


class GuardrailActionMismatchError(DecisionRuleError):
    """Raised when GuardrailEvaluation does not belong to the target ActionProposal."""
    pass


class GuardrailMerchantMismatchError(DecisionRuleError):
    """Raised when GuardrailEvaluation merchant does not match target merchant."""
    pass


class BlockedDecisionApprovalError(DecisionRuleError):
    """Raised when an attempt is made to approve a BLOCKED decision."""
    pass


class EscalatedDecisionApprovalError(DecisionRuleError):
    """Raised when an attempt is made to approve an ESCALATED decision without resolution."""
    pass


class StaleDecisionError(DecisionRuleError):
    """Raised when a decision has stale proposal or evaluation hashes."""
    pass


class MerchantAuthorizationError(DecisionRuleError):
    """Raised when an unauthorized merchant attempts sign-off."""
    pass


def compute_proposal_hash(proposal: Any) -> str:
    """Computes deterministic canonical SHA-256 hash for an ActionProposal or row dict.
    
    Protects against post-decision tampering or payload drift.
    """
    if isinstance(proposal, dict):
        raw_at = proposal.get("action_type", "")
        action_type = raw_at.value if hasattr(raw_at, "value") else str(raw_at)
        params = proposal.get("parameters") or {}
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}
        params = dict(params)
        inc_val = proposal.get("incentive_value")
        if inc_val is not None and "discount_amount" not in params:
            params["discount_amount"] = inc_val
        cost_val = proposal.get("estimated_cost_inr")
        if cost_val is not None and "budget_inr" not in params:
            params["budget_inr"] = cost_val
        tgt_cnt = proposal.get("target_customer_count", 0)
        if tgt_cnt is not None and "target_count" not in params:
            params["target_count"] = tgt_cnt

        canonical_dict = {
            "action_type": action_type,
            "parameters": params,
            "estimated_cost_inr": round(float(proposal.get("estimated_cost_inr", 0.0) or 0.0), 2),
            "incentive_value": round(float(proposal.get("incentive_value", 0.0) or 0.0), 2),
            "target_customer_count": int(proposal.get("target_customer_count", 0) or 0),
            "duration": str(proposal.get("duration", "") or ""),
        }
    else:
        action_type = proposal.action_type.value if hasattr(proposal.action_type, "value") else str(proposal.action_type)
        params = dict(proposal.parameters or {})
        inc_val = getattr(proposal, "incentive_value", None)
        if inc_val is not None and "discount_amount" not in params:
            params["discount_amount"] = inc_val
        cost_val = getattr(proposal, "estimated_cost_inr", None)
        if cost_val is not None and "budget_inr" not in params:
            params["budget_inr"] = cost_val
        tgt_cnt = getattr(proposal, "target_customer_count", 0)
        if tgt_cnt is not None and "target_count" not in params:
            params["target_count"] = tgt_cnt

        canonical_dict = {
            "action_type": action_type,
            "parameters": params,
            "estimated_cost_inr": round(float(getattr(proposal, "estimated_cost_inr", 0.0) or 0.0), 2),
            "incentive_value": round(float(getattr(proposal, "incentive_value", 0.0) or 0.0), 2),
            "target_customer_count": int(getattr(proposal, "target_customer_count", 0) or 0),
            "duration": str(getattr(proposal, "duration", "") or ""),
        }
    encoded = json.dumps(canonical_dict, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_evaluation_hash(evaluation: Any) -> str:
    """Computes deterministic canonical SHA-256 hash for a GuardrailEvaluation or row dict.
    
    Protects against out-of-sync or mutated guardrail evaluations.
    """
    if isinstance(evaluation, dict):
        raw_os = evaluation.get("overall_status", "")
        overall_status = raw_os.value if hasattr(raw_os, "value") else str(raw_os)
        failed_checks = evaluation.get("failed_checks") or []
        if isinstance(failed_checks, str):
            try:
                failed_checks = json.loads(failed_checks)
            except Exception:
                failed_checks = []
        mods = evaluation.get("modified_values") or evaluation.get("modifications") or {}
        if isinstance(mods, str):
            try:
                mods = json.loads(mods)
            except Exception:
                mods = {}
        canonical_dict = {
            "overall_status": overall_status,
            "passed": bool(evaluation.get("passed", 1)),
            "failed_checks": sorted(failed_checks),
            "modifications": mods,
        }
    else:
        overall_status = evaluation.overall_status.value if hasattr(evaluation.overall_status, "value") else str(evaluation.overall_status)
        canonical_dict = {
            "overall_status": overall_status,
            "passed": bool(evaluation.passed),
            "failed_checks": sorted(evaluation.failed_checks or []),
            "modifications": evaluation.modified_values or evaluation.modifications or {},
        }
    encoded = json.dumps(canonical_dict, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_decision_state(evaluation: GuardrailEvaluation) -> DecisionState:
    """Deterministically derives authoritative DecisionState from GuardrailEvaluation.
    
    CRITICAL: 100% Deterministic mapping, zero LLM authority.
    """
    status = evaluation.overall_status
    if isinstance(status, str):
        try:
            status = DecisionState(status)
        except ValueError:
            return DecisionState.BLOCK

    if status == DecisionState.PASS:
        return DecisionState.PASS
    elif status == DecisionState.MODIFY:
        return DecisionState.MODIFY
    elif status == DecisionState.BLOCK:
        return DecisionState.BLOCK
    elif status == DecisionState.ESCALATE:
        return DecisionState.ESCALATE
    else:
        return DecisionState.BLOCK


def synthesize_approved_action(
    proposal: ActionProposal,
    evaluation: GuardrailEvaluation,
    state: DecisionState,
) -> Optional[Dict[str, Any]]:
    """Synthesizes binding approved action parameters strictly adhering to safety rules.
    
    MODIFY INTEGRITY GUARANTEE:
    If Phase 6 modified a parameter (e.g. cashback ₹150 -> ₹100), the approved action
    MUST contain the clamped ₹100 value and NEVER the requested ₹150.
    """
    if state == DecisionState.PASS:
        action_type = proposal.action_type.value if hasattr(proposal.action_type, "value") else str(proposal.action_type)
        return {
            "action_type": action_type,
            "parameters": dict(proposal.parameters or {}),
            "confidence": getattr(proposal, "confidence", 0.85),
            "incentive_value": getattr(proposal, "incentive_value", None),
            "target_customer_count": getattr(proposal, "target_customer_count", None),
            "estimated_cost_inr": getattr(proposal, "estimated_cost_inr", None),
        }

    elif state == DecisionState.MODIFY:
        action_type = proposal.action_type.value if hasattr(proposal.action_type, "value") else str(proposal.action_type)
        effective_params = dict(proposal.parameters or {})
        mods = dict(evaluation.modified_values or evaluation.modifications or {})
        effective_params.update(mods)

        # Derive effective safe incentive
        effective_incentive = getattr(proposal, "incentive_value", None)
        for key in ("incentive_value", "discount_amount", "discount", "max_discount"):
            if key in mods:
                effective_incentive = mods[key]
                break

        return {
            "action_type": action_type,
            "parameters": effective_params,
            "confidence": getattr(proposal, "confidence", 0.85),
            "incentive_value": effective_incentive,
            "target_customer_count": mods.get("target_customer_count", getattr(proposal, "target_customer_count", None)),
            "estimated_cost_inr": mods.get("estimated_cost_inr", getattr(proposal, "estimated_cost_inr", None)),
            "modifications_applied": mods,
        }

    else:
        # BLOCK and ESCALATE have no approved execution parameters
        return None


def verify_evaluation_precondition(
    action_id: str,
    evaluation: Optional[GuardrailEvaluation],
    merchant_id: Optional[str] = None,
) -> None:
    """Verifies that an existing, valid GuardrailEvaluation is present before decision creation."""
    if evaluation is None:
        raise MissingGuardrailEvaluationError(
            "Guardrail evaluation required before decision creation."
        )

    eval_action = evaluation.action_id or getattr(evaluation, "proposal_id", "")
    if eval_action != action_id:
        raise GuardrailActionMismatchError(
            f"Guardrail evaluation action {eval_action} does not match requested action {action_id}."
        )

    if merchant_id and evaluation.merchant_id and evaluation.merchant_id != merchant_id:
        raise GuardrailMerchantMismatchError(
            f"Guardrail evaluation merchant {evaluation.merchant_id} does not match requested merchant {merchant_id}."
        )


def verify_decision_integrity(
    decision: Decision,
    current_proposal: ActionProposal,
    current_evaluation: GuardrailEvaluation,
) -> Tuple[bool, Optional[str]]:
    """Verifies that proposal and evaluation hashes match the canonical decision hashes.
    
    Returns:
        (True, None) if intact.
        (False, failure_reason) if hash mismatch detected.
    """
    current_p_hash = compute_proposal_hash(current_proposal)
    if decision.proposal_hash and decision.proposal_hash != current_p_hash:
        return False, f"Proposal payload has changed (expected hash {decision.proposal_hash[:8]}, got {current_p_hash[:8]})."

    current_e_hash = compute_evaluation_hash(current_evaluation)
    if decision.evaluation_hash and decision.evaluation_hash != current_e_hash:
        return False, f"Guardrail evaluation has changed (expected hash {decision.evaluation_hash[:8]}, got {current_e_hash[:8]})."

    return True, None
