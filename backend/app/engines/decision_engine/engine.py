from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from app.core.logging import logger
from app.database.repository import (
    ActionRepository,
    DecisionRepository,
    GuardrailRepository,
    MerchantRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.decision_engine.rules import (
    BlockedDecisionApprovalError,
    EscalatedDecisionApprovalError,
    MerchantAuthorizationError,
    MissingGuardrailEvaluationError,
    StaleDecisionError,
    compute_evaluation_hash,
    compute_proposal_hash,
    evaluate_decision_state,
    synthesize_approved_action,
    verify_decision_integrity,
    verify_evaluation_precondition,
)
from app.models.contracts import ActionProposal, Decision, GuardrailCheck, GuardrailEvaluation
from app.models.enums import ApprovalStatus, DecisionState, StageType


class DecisionEngine:
    """Authoritative Deterministic Decision Engine & Merchant Sign-off Gateway.
    
    CRITICAL ARCHITECTURAL BOUNDARIES:
    1. Phase 7 does NOT evaluate guardrails. It consumes the persisted output of Phase 6.
    2. A Decision cannot exist as an authoritative execution decision without a valid
       persisted GuardrailEvaluation.
    3. Zero LLM authority over decisions, approvals, or execution authorization.
    4. Merchant approval is strictly a sign-off action, NOT a safety-rule override.
       - BLOCK decisions CANNOT be approved.
       - ESCALATE decisions require explicit human review resolution.
       - MODIFY decisions strictly approve the modified parameters (e.g. ₹100, never ₹150).
    5. SHA-256 hashes protect against stale or mutated proposals/evaluations.
    """

    def __init__(self, audit_engine: Optional[AuditEngine] = None):
        self.audit_engine = audit_engine or AuditEngine()

    def decide(
        self,
        proposal: ActionProposal,
        guardrail: GuardrailEvaluation,
        require_approval: Optional[bool] = None,
        merchant_settings: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Determines final authoritative decision strictly derived from GuardrailEvaluation.
        
        CRITICAL: Pure deterministic mapping from Phase 6 output.
        Zero LLM calls, zero guardrail re-evaluations.
        """
        # Precondition check
        verify_evaluation_precondition(
            action_id=proposal.action_id or proposal.proposal_id,
            evaluation=guardrail,
            merchant_id=proposal.merchant_id,
        )

        state = evaluate_decision_state(guardrail)
        approved_action = synthesize_approved_action(proposal, guardrail, state)
        
        # Compute canonical hashes for tamper and staleness protection
        p_hash = compute_proposal_hash(proposal)
        e_hash = compute_evaluation_hash(guardrail)

        # Autonomy & Approval policy
        if require_approval is not None:
            approval_req = require_approval
        elif merchant_settings:
            autonomy = merchant_settings.get("autonomy_level", "APPROVAL_REQUIRED")
            approval_req = autonomy == "APPROVAL_REQUIRED"
        else:
            # Default to False for raw programmatic calls (e.g. Phase 1 orchestrator tests)
            # API workflow explicitly requests require_approval=True
            approval_req = False

        if approval_req:
            appr_status = ApprovalStatus.PENDING
            is_exec_eligible = False
        else:
            appr_status = ApprovalStatus.NOT_REQUIRED
            is_exec_eligible = state in (DecisionState.PASS, DecisionState.MODIFY)

        # Build human-readable deterministic rationale
        if state == DecisionState.PASS:
            reason = f"Approved for execution: {guardrail.notes or 'All guardrails passed.'}"
            escalation_reason = None
            requires_human_review = False
        elif state == DecisionState.MODIFY:
            mods_str = ", ".join(f"{k}={v}" for k, v in (guardrail.modified_values or guardrail.modifications).items())
            reason = f"Approved with modifications ({mods_str}): {guardrail.notes or 'Parameters clamped to safety thresholds.'}"
            escalation_reason = None
            requires_human_review = False
        elif state == DecisionState.BLOCK:
            violations = guardrail.failed_checks or guardrail.violations or ["Safety constraint violation"]
            reason = f"Action blocked: {'; '.join(violations)}"
            escalation_reason = None
            requires_human_review = False
            is_exec_eligible = False
        elif state == DecisionState.ESCALATE:
            violations = guardrail.failed_checks or guardrail.violations or ["Requires merchant sign-off"]
            escalation_reason = "; ".join(violations) or guardrail.notes
            reason = f"Action escalated to merchant for human review: {escalation_reason}"
            requires_human_review = True
            is_exec_eligible = False
        else:
            state = DecisionState.BLOCK
            reason = "Action blocked due to unrecognized guardrail state."
            escalation_reason = None
            requires_human_review = False
            is_exec_eligible = False

        action_id = proposal.action_id or proposal.proposal_id
        evaluation_id = guardrail.evaluation_id or getattr(guardrail, "result_id", "")

        return Decision(
            action_id=action_id,
            evaluation_id=evaluation_id,
            merchant_id=proposal.merchant_id or "MID-DEMO-98234",
            decision_state=state,
            reason=reason,
            triggered_rules=guardrail.failed_checks or [],
            modifications=guardrail.modified_values or guardrail.modifications or {},
            approval_required=approval_req,
            approval_status=appr_status,
            proposal_hash=p_hash,
            evaluation_hash=e_hash,
            is_deterministic=True,
            approved_action=approved_action,
            is_execution_eligible=is_exec_eligible,
            escalation_reason=escalation_reason,
            requires_human_review=requires_human_review,
        )

    def create_decision_from_persisted_evaluation(
        self,
        action_id: str,
        merchant_id: str = "MID-DEMO-98234",
    ) -> Decision:
        """Authoritatively creates a Decision from existing, persisted GuardrailEvaluation.
        
        PRECONDITION:
        GuardrailEvaluation MUST already exist in the database.
        Phase 7 NEVER silently invokes Phase 6 GuardrailEngine.
        If evaluation is missing, raises MissingGuardrailEvaluationError.
        """
        # 1. Load ActionProposal
        action_row = ActionRepository.get_action_by_id(action_id)
        if not action_row:
            raise ValueError(f"Action proposal {action_id} not found in database.")

        proposal = ActionProposal(
            proposal_id=action_row["id"],
            action_id=action_row["id"],
            signal_id=action_row["signal_id"],
            merchant_id=action_row["merchant_id"],
            action_type=action_row["action_type"],
            parameters=json.loads(action_row["parameters"]) if isinstance(action_row["parameters"], str) else action_row["parameters"],
            objective=action_row.get("objective", ""),
            target_segment=action_row.get("target_segment", ""),
            target_customer_count=action_row.get("target_customer_count", 0),
            incentive_type=action_row.get("incentive_type", ""),
            incentive_value=action_row.get("incentive_value", 0.0),
            duration=action_row.get("duration", ""),
            reason=action_row.get("reason", ""),
            estimated_cost_inr=action_row.get("estimated_cost_inr", 0.0),
            status=action_row.get("status", "PROPOSED"),
        )

        # 2. Load latest persisted GuardrailEvaluation (MANDATORY PRECONDITION)
        eval_row = GuardrailRepository.get_evaluation_by_action(action_id)
        if not eval_row:
            logger.warning(
                "Cannot create decision for action %s: No GuardrailEvaluation exists.",
                action_id,
            )
            raise MissingGuardrailEvaluationError(
                "Guardrail evaluation required before decision creation."
            )

        checks_raw = eval_row.get("checks", "[]")
        passed_raw = eval_row.get("passed_checks", "[]")
        failed_raw = eval_row.get("failed_checks", "[]")
        mods_raw = eval_row.get("modifications", "{}")
        orig_raw = eval_row.get("original_values", "{}")
        mod_vals_raw = eval_row.get("modified_values", "{}")

        parsed_checks = self._parse_guardrail_checks(checks_raw)

        evaluation = GuardrailEvaluation(
            evaluation_id=eval_row["id"],
            action_id=eval_row["action_id"],
            merchant_id=eval_row["merchant_id"],
            overall_status=eval_row["overall_status"],
            passed=bool(eval_row["passed"]),
            checks=parsed_checks,
            passed_checks=json.loads(passed_raw) if isinstance(passed_raw, str) else passed_raw,
            failed_checks=json.loads(failed_raw) if isinstance(failed_raw, str) else failed_raw,
            modifications=json.loads(mods_raw) if isinstance(mods_raw, str) else mods_raw,
            original_values=json.loads(orig_raw) if isinstance(orig_raw, str) else orig_raw,
            modified_values=json.loads(mod_vals_raw) if isinstance(mod_vals_raw, str) else mod_vals_raw,
            notes=eval_row.get("notes", ""),
            evaluated_at=eval_row.get("evaluated_at", datetime.now(timezone.utc).isoformat()),
        )

        # 3. Check for existing idempotent decision
        current_p_hash = compute_proposal_hash(proposal)
        current_e_hash = compute_evaluation_hash(evaluation)
        existing_dec = DecisionRepository.get_decision_by_action(action_id)

        if existing_dec:
            # If hashes match, return existing valid decision
            if (
                existing_dec.get("proposal_hash") == current_p_hash
                and existing_dec.get("evaluation_hash") == current_e_hash
            ):
                logger.info(
                    "Idempotent decision retrieval for action %s (decision %s)",
                    action_id,
                    existing_dec["id"],
                )
                return self._row_to_decision(existing_dec)

        # 4. Synthesize authoritative decision (Under merchant autonomy mode APPROVAL_REQUIRED)
        decision = self.decide(
            proposal=proposal,
            guardrail=evaluation,
            require_approval=True,
        )

        # 5. Persist to DecisionRepository
        persisted_dict = DecisionRepository.create_or_update_decision(
            action_id=decision.action_id,
            evaluation_id=decision.evaluation_id,
            merchant_id=decision.merchant_id,
            decision_state=decision.decision_state.value,
            reason=decision.reason,
            triggered_rules=decision.triggered_rules,
            modifications=decision.modifications,
            approval_required=decision.approval_required,
            approval_status=decision.approval_status.value,
            proposal_hash=decision.proposal_hash,
            evaluation_hash=decision.evaluation_hash,
            is_deterministic=decision.is_deterministic,
            approved_action=decision.approved_action,
            requires_human_review=decision.requires_human_review,
            is_execution_eligible=decision.is_execution_eligible,
            decided_at=decision.decided_at,
            decided_by=decision.decided_by,
            decision_id=decision.decision_id,
        )

        # 6. Audit Logging
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor="DeterministicDecisionEngine",
            action_description=f"Authoritative decision created: {decision.decision_state.value}",
            input_payload={
                "action_id": action_id,
                "evaluation_id": evaluation.evaluation_id,
                "proposal_hash": decision.proposal_hash,
                "evaluation_hash": decision.evaluation_hash,
            },
            output_payload={
                "decision_id": decision.decision_id,
                "decision_state": decision.decision_state.value,
                "approval_required": decision.approval_required,
                "approval_status": decision.approval_status.value,
                "is_execution_eligible": decision.is_execution_eligible,
            },
        )

        return self._row_to_decision(persisted_dict)

    def approve_decision(
        self,
        decision_id: str,
        approver_merchant_id: str = "MID-DEMO-98234",
        approver_name: str = "Merchant Admin",
    ) -> Decision:
        """Processes merchant sign-off for an authoritative Decision.
        
        SAFETY INVARIANTS:
        - BLOCK decisions CANNOT be approved (raises BlockedDecisionApprovalError).
        - ESCALATE decisions CANNOT bypass human review (raises EscalatedDecisionApprovalError).
        - Proposal and evaluation hashes must match current database state (Stale check).
        - Approver merchant ID must match decision merchant ID.
        - Approval CANNOT modify the proposed parameters.
        """
        row = DecisionRepository.get_decision(decision_id)
        if not row:
            raise ValueError(f"Decision {decision_id} not found.")

        # Merchant authorization check
        if row["merchant_id"] != approver_merchant_id:
            raise MerchantAuthorizationError(
                f"Merchant {approver_merchant_id} unauthorized to approve decision for {row['merchant_id']}."
            )

        dec_state = row.get("decision_state") or row.get("state")
        if dec_state == DecisionState.BLOCK.value:
            raise BlockedDecisionApprovalError("Blocked decisions cannot be approved.")

        if dec_state == DecisionState.ESCALATE.value:
            raise EscalatedDecisionApprovalError(
                "Escalated decisions require human review and cannot bypass the review barrier."
            )

        # Hash integrity / Stale check
        action_row = ActionRepository.get_action_by_id(row["action_id"])
        eval_row = GuardrailRepository.get_evaluation_by_action(row["action_id"])
        if not action_row or not eval_row:
            raise StaleDecisionError("Decision is stale. Associated action or evaluation is missing.")

        proposal = ActionProposal(
            proposal_id=action_row["id"],
            action_id=action_row["id"],
            signal_id=action_row["signal_id"],
            merchant_id=action_row["merchant_id"],
            action_type=action_row["action_type"],
            parameters=json.loads(action_row["parameters"]) if isinstance(action_row["parameters"], str) else action_row["parameters"],
            incentive_value=action_row.get("incentive_value", 0.0),
            target_customer_count=action_row.get("target_customer_count", 0),
            estimated_cost_inr=action_row.get("estimated_cost_inr", 0.0),
            duration=action_row.get("duration", ""),
            reason=action_row.get("reason") or "Action proposal",
        )

        evaluation = GuardrailEvaluation(
            evaluation_id=eval_row["id"],
            action_id=eval_row["action_id"],
            merchant_id=eval_row["merchant_id"],
            overall_status=eval_row["overall_status"],
            passed=bool(eval_row["passed"]),
            failed_checks=json.loads(eval_row["failed_checks"]) if isinstance(eval_row["failed_checks"], str) else eval_row["failed_checks"],
            modifications=json.loads(eval_row["modifications"]) if isinstance(eval_row["modifications"], str) else eval_row["modifications"],
            modified_values=json.loads(eval_row["modified_values"]) if isinstance(eval_row["modified_values"], str) else eval_row["modified_values"],
        )

        decision_obj = self._row_to_decision(row)
        is_intact, reason = verify_decision_integrity(decision_obj, proposal, evaluation)
        if not is_intact:
            raise StaleDecisionError(f"Decision is stale. Fresh guardrail evaluation required. Details: {reason}")

        # Record approval
        updated_row = DecisionRepository.approve_decision(decision_id, approver=approver_name)
        if not updated_row:
            raise ValueError(f"Failed to record approval for decision {decision_id}.")

        approved_decision = self._row_to_decision(updated_row)

        # Audit Logging
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor=f"Merchant ({approver_name})",
            action_description=f"Merchant approved decision {decision_id}: execution eligible",
            input_payload={
                "decision_id": decision_id,
                "approver_merchant_id": approver_merchant_id,
                "proposal_hash": decision_obj.proposal_hash,
                "evaluation_hash": decision_obj.evaluation_hash,
            },
            output_payload={
                "approval_status": "APPROVED",
                "is_execution_eligible": True,
                "approved_action": approved_decision.approved_action,
            },
        )

        return approved_decision

    def reject_decision(
        self,
        decision_id: str,
        reason: str = "Rejected by merchant",
        approver_merchant_id: str = "MID-DEMO-98234",
        approver_name: str = "Merchant Admin",
    ) -> Decision:
        """Processes merchant rejection of an authoritative Decision."""
        row = DecisionRepository.get_decision(decision_id)
        if not row:
            raise ValueError(f"Decision {decision_id} not found.")

        if row["merchant_id"] != approver_merchant_id:
            raise MerchantAuthorizationError(
                f"Merchant {approver_merchant_id} unauthorized to reject decision for {row['merchant_id']}."
            )

        updated_row = DecisionRepository.reject_decision(decision_id, reason=reason)
        if not updated_row:
            raise ValueError(f"Failed to record rejection for decision {decision_id}.")

        rejected_decision = self._row_to_decision(updated_row)

        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor=f"Merchant ({approver_name})",
            action_description=f"Merchant rejected decision {decision_id}",
            input_payload={"decision_id": decision_id, "reason": reason},
            output_payload={"approval_status": "REJECTED", "is_execution_eligible": False},
        )

        return rejected_decision

    @staticmethod
    def _row_to_decision(row: Dict[str, Any]) -> Decision:
        """Helper mapping SQLite dictionary to Decision model."""
        rules_raw = row.get("triggered_rules", "[]")
        mods_raw = row.get("modifications", "{}")
        appr_act_raw = row.get("approved_action", "{}")

        rules = json.loads(rules_raw) if isinstance(rules_raw, str) else (rules_raw or [])
        mods = json.loads(mods_raw) if isinstance(mods_raw, str) else (mods_raw or {})
        appr_act = json.loads(appr_act_raw) if isinstance(appr_act_raw, str) else (appr_act_raw or None)
        if appr_act == {}:
            appr_act = None

        state_str = row.get("decision_state") or row.get("state") or "PASS"
        appr_str = row.get("approval_status") or "PENDING"

        return Decision(
            decision_id=row["id"],
            action_id=row["action_id"],
            evaluation_id=row.get("evaluation_id", ""),
            merchant_id=row.get("merchant_id", "MID-DEMO-98234"),
            decision_state=DecisionState(state_str),
            reason=row.get("reason") or row.get("rationale") or "",
            triggered_rules=rules,
            modifications=mods,
            approval_required=bool(row.get("approval_required", 1)),
            approval_status=ApprovalStatus(appr_str),
            decided_at=row.get("decided_at") or row.get("created_at") or "",
            decided_by=row.get("decided_by", "MITRA_DECISION_ENGINE"),
            approved_at=row.get("approved_at"),
            rejected_at=row.get("rejected_at"),
            proposal_hash=row.get("proposal_hash", ""),
            evaluation_hash=row.get("evaluation_hash", ""),
            is_deterministic=bool(row.get("is_deterministic", 1)),
            approved_action=appr_act,
            is_execution_eligible=bool(row.get("is_execution_eligible", 0)),
            requires_human_review=bool(row.get("requires_human_review", 0)),
        )

    @staticmethod
    def _parse_guardrail_checks(checks_raw: Any) -> list:
        """Parses and normalizes guardrail checks list from database row."""
        checks_list = json.loads(checks_raw) if isinstance(checks_raw, str) else (checks_raw or [])
        parsed_checks = []
        for c in checks_list:
            if isinstance(c, dict):
                parsed_checks.append(
                    GuardrailCheck(
                        check_id=c.get("check_id", "G0"),
                        check_type=c.get("check_type", c.get("rule_name", "CUSTOM_CHECK")),
                        status=c.get("status", "PASS"),
                        rule=c.get("rule", c.get("rule_name", "Policy check")),
                        actual_value=c.get("actual_value", ""),
                        threshold_value=c.get("threshold_value", ""),
                        message=c.get("message", "Check evaluated"),
                        severity=c.get("severity", "INFO"),
                    )
                )
            elif isinstance(c, GuardrailCheck):
                parsed_checks.append(c)
        return parsed_checks
