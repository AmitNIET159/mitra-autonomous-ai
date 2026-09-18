"""Authoritative Deterministic Autonomy Policy Engine (Phase 12).

CRITICAL ARCHITECTURAL BOUNDARIES:
1. Zero LLM authority: LLM proposes candidate actions, but deterministic policy
   evaluates safety conditions and approval requirements.
2. Autonomy controls approval flow; autonomy NEVER overrides safety.
   - Guardrail BLOCK -> strictly BLOCKED (never auto-approved, cannot be executed).
   - Guardrail ESCALATE -> strictly requires human review.
   - Guardrail MODIFY -> clamped parameters enforced (₹100 executed, ₹150 never executed).
3. Authoritative Audit Chaining (Phase 11):
   - Preserves correlation_id and SHA-256 tamper-evident chaining.
   - Records AUTONOMY_EVALUATION_STARTED, AUTO_APPROVAL_GRANTED, HUMAN_APPROVAL_REQUIRED,
     AUTONOMY_BLOCKED, AUTONOMY_ESCALATED.
4. Idempotent evaluation with stale hash protection.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import uuid

from app.core.logging import logger
from app.database.repository import (
    ActionRepository,
    AutonomyRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    MerchantRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.autonomy_engine.rules import (
    AUTO_APPROVE_SAFE_RISK_THRESHOLD,
    FULL_AUTONOMY_RISK_THRESHOLD,
    BlockedAutonomyOverrideError,
    EscalatedAutonomyOverrideError,
    StaleAutonomyEvaluationError,
    determine_autonomy_verdict,
    evaluate_16_safety_conditions,
    extract_effective_parameters,
)
from app.engines.decision_engine.rules import (
    compute_evaluation_hash,
    compute_proposal_hash,
    verify_decision_integrity,
)
from app.models.contracts import (
    ActionProposal,
    AutonomyEvaluation,
    Decision,
    GuardrailEvaluation,
)
from app.models.enums import (
    ActorType,
    ApprovalSource,
    AutonomyMode,
    AutonomyStatus,
    DecisionState,
    StageType,
)


class AutonomyPolicyEngine:
    """Evaluates merchant autonomy policy and deterministically grants or gates approvals."""

    def __init__(
        self,
        audit_engine: Optional[AuditEngine] = None,
        simulation_mode: bool = True,
    ):
        self.audit_engine = audit_engine or AuditEngine()
        self.simulation_mode = simulation_mode

    def evaluate(
        self,
        action_id: str,
        merchant_id: str = "MID-DEMO-98234",
        override_mode: Optional[AutonomyMode] = None,
    ) -> AutonomyEvaluation:
        """Evaluates autonomy policy for an action proposal and its authoritative decision.
        
        MANDATORY PRECONDITIONS:
        1. ActionProposal must exist.
        2. GuardrailEvaluation must exist.
        3. Decision must exist.
        4. Proposal and evaluation hashes must remain intact (stale check).
        """
        # 1. Load ActionProposal
        action_row = ActionRepository.get_action_by_id(action_id)
        if not action_row:
            raise ValueError(f"Action proposal '{action_id}' not found in digital twin.")

        params = json.loads(action_row["parameters"]) if isinstance(action_row["parameters"], str) else action_row["parameters"]
        action_risk = params.get("risk_score") if isinstance(params, dict) else None
        if action_risk is None:
            action_risk = action_row.get("risk_score")
        if action_risk is None:
            action_risk = 0.18

        proposal = ActionProposal(
            proposal_id=action_row["id"],
            action_id=action_row["id"],
            signal_id=action_row["signal_id"],
            merchant_id=action_row["merchant_id"],
            action_type=action_row["action_type"],
            parameters=params,
            objective=action_row.get("objective", ""),
            target_segment=action_row.get("target_segment", ""),
            target_customer_count=action_row.get("target_customer_count", 0),
            incentive_type=action_row.get("incentive_type", ""),
            incentive_value=action_row.get("incentive_value", 0.0),
            duration=action_row.get("duration", ""),
            reason=action_row.get("reason", ""),
            estimated_cost_inr=action_row.get("estimated_cost_inr", 0.0),
            status=action_row.get("status", "PROPOSED"),
            risk_score=float(action_risk),
        )

        # 2. Load GuardrailEvaluation
        eval_row = GuardrailRepository.get_evaluation_by_action(action_id)
        if not eval_row:
            raise StaleAutonomyEvaluationError(
                f"Cannot evaluate autonomy for action {action_id}: GuardrailEvaluation is missing."
            )

        evaluation = GuardrailEvaluation(
            evaluation_id=eval_row["id"],
            action_id=eval_row["action_id"],
            merchant_id=eval_row["merchant_id"],
            overall_status=eval_row["overall_status"],
            passed=bool(eval_row["passed"]),
            failed_checks=json.loads(eval_row["failed_checks"]) if isinstance(eval_row["failed_checks"], str) else eval_row["failed_checks"],
            modifications=json.loads(eval_row["modifications"]) if isinstance(eval_row["modifications"], str) else eval_row["modifications"],
            original_values=json.loads(eval_row["original_values"]) if isinstance(eval_row["original_values"], str) else eval_row["original_values"],
            modified_values=json.loads(eval_row["modified_values"]) if isinstance(eval_row["modified_values"], str) else eval_row["modified_values"],
            notes=eval_row.get("notes", ""),
        )

        # 3. Load Decision
        dec_row = DecisionRepository.get_decision_by_action(action_id)
        if not dec_row:
            raise StaleAutonomyEvaluationError(
                f"Cannot evaluate autonomy for action {action_id}: Decision must be synthesized first."
            )

        from app.engines.decision_engine.engine import DecisionEngine
        decision = DecisionEngine._row_to_decision(dec_row)

        # 4. Verify Hashes (Tamper & Staleness check)
        is_intact, reason = verify_decision_integrity(decision, proposal, evaluation)
        if not is_intact:
            raise StaleAutonomyEvaluationError(
                f"Decision is stale or mutated. Details: {reason}"
            )

        # 5. Check if duplicate execution already occurred
        existing_exec = ExecutionRepository.get_execution_by_decision(decision.decision_id)
        is_already_executed = bool(existing_exec and existing_exec.get("execution_state") in ("COMPLETED", "EXECUTING"))

        # 6. Load Merchant Autonomy Policy
        merchant_policy = MerchantRepository.get_autonomy_policy(merchant_id)
        if override_mode:
            merchant_policy["autonomy_mode"] = override_mode.value if hasattr(override_mode, "value") else str(override_mode)

        autonomy_mode_str = merchant_policy.get("autonomy_mode", "APPROVAL_REQUIRED")
        current_mode = AutonomyMode(autonomy_mode_str)

        # Determine threshold
        if current_mode == AutonomyMode.FULL_AUTONOMY:
            threshold = float(merchant_policy.get("full_autonomy_risk_threshold", FULL_AUTONOMY_RISK_THRESHOLD))
        else:
            threshold = float(merchant_policy.get("auto_approval_risk_threshold", AUTO_APPROVE_SAFE_RISK_THRESHOLD))

        if proposal.signal_id:
            correlation_id = f"wf-{proposal.signal_id.replace('sig-', '').replace('SIG-', '').lower()}"
        else:
            correlation_id = f"wf-{action_id.replace('act-', '').replace('prop-', '').lower()}"

        # 7. Audit: Evaluation Started
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor="AutonomyPolicyEngine",
            action_description="Autonomy policy evaluation started",
            input_payload={
                "action_id": action_id,
                "decision_id": decision.decision_id,
                "autonomy_mode": current_mode.value,
                "risk_score": proposal.risk_score,
                "policy_threshold": threshold,
            },
            output_payload={"status": "EVALUATING"},
            correlation_id=correlation_id,
        )

        # 8. Evaluate 16 Safety Conditions
        all_passed, passed_checks, failed_checks = evaluate_16_safety_conditions(
            proposal=proposal,
            guardrail=evaluation,
            decision=decision,
            merchant_policy=merchant_policy,
            is_already_executed=is_already_executed,
            is_hash_intact=is_intact,
            simulation_mode=self.simulation_mode,
        )

        # 9. Apply Deterministic Decision Matrix
        verdict = determine_autonomy_verdict(
            proposal=proposal,
            guardrail=evaluation,
            decision=decision,
            merchant_policy=merchant_policy,
            all_safety_conditions_passed=all_passed,
            failed_checks=failed_checks,
        )

        # 10. Update DecisionRepository if Auto-approved
        if verdict["auto_approval_allowed"]:
            DecisionRepository.auto_approve_decision(
                decision_id=decision.decision_id,
                reason=verdict["reason"],
            )
            # Record AUTO_APPROVAL_GRANTED audit event
            self.audit_engine.record_event(
                stage=StageType.DECIDE,
                actor="AutonomyPolicyEngine",
                action_description=f"Auto-approval granted for decision {decision.decision_id}",
                input_payload={
                    "decision_id": decision.decision_id,
                    "action_id": action_id,
                    "autonomy_mode": current_mode.value,
                    "risk_score": proposal.risk_score,
                    "policy_threshold": threshold,
                    "passed_checks_count": len(passed_checks),
                },
                output_payload={
                    "approval_status": "APPROVED",
                    "approval_source": ApprovalSource.AUTO_APPROVED.value,
                    "is_execution_eligible": True,
                    "approved_action": verdict["approved_action"],
                },
                correlation_id=correlation_id,
            )
        elif verdict["blocked"]:
            self.audit_engine.record_event(
                stage=StageType.DECIDE,
                actor="AutonomyPolicyEngine",
                action_description=f"Action blocked by safety guardrail in {current_mode.value} mode",
                input_payload={"decision_id": decision.decision_id, "autonomy_mode": current_mode.value},
                output_payload={"approval_source": ApprovalSource.BLOCKED.value, "is_execution_eligible": False},
                correlation_id=correlation_id,
            )
        elif verdict["escalated"]:
            self.audit_engine.record_event(
                stage=StageType.DECIDE,
                actor="AutonomyPolicyEngine",
                action_description=f"Action escalated for human review in {current_mode.value} mode",
                input_payload={"decision_id": decision.decision_id, "autonomy_mode": current_mode.value},
                output_payload={"approval_source": ApprovalSource.ESCALATED.value, "is_execution_eligible": False},
                correlation_id=correlation_id,
            )
        else:
            self.audit_engine.record_event(
                stage=StageType.DECIDE,
                actor="AutonomyPolicyEngine",
                action_description=f"Merchant approval required for decision {decision.decision_id}",
                input_payload={"decision_id": decision.decision_id, "autonomy_mode": current_mode.value},
                output_payload={"approval_source": ApprovalSource.PENDING.value, "is_execution_eligible": False},
                correlation_id=correlation_id,
            )

        # 11. Persist to AutonomyRepository
        evaluation_id = f"aut-{uuid.uuid4().hex[:10]}"
        record = AutonomyRepository.record_evaluation(
            evaluation_id=evaluation_id,
            correlation_id=correlation_id,
            merchant_id=merchant_id,
            action_id=action_id,
            guardrail_evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            autonomy_mode=current_mode.value,
            guardrail_status=evaluation.overall_status.value if hasattr(evaluation.overall_status, "value") else str(evaluation.overall_status),
            approval_required=verdict["approval_required"],
            auto_approval_allowed=verdict["auto_approval_allowed"],
            auto_approval_reason=verdict["reason"],
            approval_source=verdict["approval_source"].value if hasattr(verdict["approval_source"], "value") else str(verdict["approval_source"]),
            actor_type=verdict["actor_type"].value if hasattr(verdict["actor_type"], "value") else str(verdict["actor_type"]),
            blocked=verdict["blocked"],
            escalated=verdict["escalated"],
            approved_action=verdict["approved_action"] or {},
            evaluated_risk=float(proposal.risk_score or 0.0),
            policy_threshold=threshold,
            policy_version="1.0.0",
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            simulation_mode=self.simulation_mode,
        )

        return AutonomyEvaluation.model_validate(record)
