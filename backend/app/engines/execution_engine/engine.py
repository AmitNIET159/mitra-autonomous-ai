from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
import uuid

from app.core.config import get_settings
from app.core.logging import logger
from app.database.repository import (
    ActionRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.decision_engine.rules import (
    compute_evaluation_hash,
    compute_proposal_hash,
)
from app.integrations.paytm_simulator import RealExecutionNotAllowedError, SimulatedPaytmAdapter
from app.models.contracts import Decision, ExecutionResult
from app.models.enums import (
    ActionType,
    ApprovalStatus,
    DecisionState,
    ExecutionMode,
    ExecutionState,
    StageType,
)

settings = get_settings()


class ExecutionSafetyError(Exception):
    """Base exception for any safety boundary violation in execution."""
    pass


class DecisionNotFoundError(ExecutionSafetyError):
    """Raised when the specified decision cannot be found."""
    pass


class MerchantMismatchError(ExecutionSafetyError):
    """Raised when the executing merchant does not match the decision merchant."""
    pass


class UncheckedExecutionAttemptError(ExecutionSafetyError):
    """Raised when an entity attempts to execute without an authoritative Decision object."""
    pass


class BlockedActionExecutionError(ExecutionSafetyError):
    """Raised when execution is attempted on an action that was BLOCKED by guardrails."""
    pass


class EscalatedActionExecutionError(ExecutionSafetyError):
    """Raised when execution is attempted on an action pending merchant ESCALATION sign-off."""
    pass


class UnapprovedActionExecutionError(ExecutionSafetyError):
    """Raised when execution is attempted on an action that has not received merchant sign-off."""
    pass


class ExecutionNotEligibleError(ExecutionSafetyError):
    """Raised when execution is attempted on a decision marked as ineligible for execution."""
    pass


class StaleDecisionExecutionError(ExecutionSafetyError):
    """Raised when execution is attempted on a decision with stale or invalid integrity hashes."""
    pass


class ExecutionAlreadyCompletedError(ExecutionSafetyError):
    """Raised when duplicate execution is attempted on an already completed decision."""
    pass


class ExecutionEngine:
    """Safely executes authorized actions for Paytm merchants via simulation.
    
    CRITICAL ARCHITECTURAL BOUNDARY:
    - NEVER accepts raw LLM outputs or raw ActionProposal instances.
    - Strictly accepts ONLY valid, merchant-approved Decision instances.
    - Strictly rejects any Decision not in PASS or MODIFY state.
    - Strictly enforces all 10 execution preconditions.
    - For MODIFY decisions, executes ONLY the guardrail-clamped safe parameters.
    - All actions in this hackathon prototype execute strictly in digital-twin simulation mode.
    """

    def __init__(
        self,
        simulation_mode: bool = True,
        audit_engine: Optional[AuditEngine] = None,
        adapter: Optional[SimulatedPaytmAdapter] = None,
    ):
        if not simulation_mode:
            raise RealExecutionNotAllowedError(
                "CRITICAL SAFETY BARRIER: Real Paytm execution is strictly disallowed in MITRA prototype. "
                "simulation_mode must be True."
            )
        self.simulation_mode = simulation_mode
        self.audit_engine = audit_engine or AuditEngine()
        self.adapter = adapter or SimulatedPaytmAdapter(simulation_mode=True)

    def execute(
        self,
        decision_or_id: Union[Decision, str],
        merchant_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Executes an action strictly gated by authoritative Decision and 10 preconditions."""
        # 1. Resolve Decision instance
        decision: Decision
        if isinstance(decision_or_id, str):
            row = DecisionRepository.get_decision(decision_or_id)
            if not row:
                raise DecisionNotFoundError(f"Decision with ID '{decision_or_id}' was not found.")
            decision = Decision.model_validate(row)
        elif isinstance(decision_or_id, Decision):
            decision = decision_or_id
        else:
            logger.error(
                "CRITICAL SAFETY VIOLATION: Execution attempted with invalid type: %s. "
                "Only validated Decision instances or IDs may execute.",
                type(decision_or_id).__name__,
            )
            raise UncheckedExecutionAttemptError(
                f"ExecutionEngine only accepts Decision instances, received: {type(decision_or_id).__name__}. "
                "Raw proposals or LLM responses can NEVER directly execute."
            )

        # Audit attempt
        self.audit_engine.record_event(
            stage=StageType.ACT,
            actor="ExecutionEngine",
            action_description="Execution requested for decision",
            input_payload={"decision_id": decision.decision_id, "merchant_id": merchant_id},
            output_payload={"decision_state": decision.state.value},
        )

        try:
            # 2. Decision State enforcement (Precondition 2)
            if decision.state == DecisionState.BLOCK:
                logger.warning("Blocked action %s attempted execution. Aborting.", decision.decision_id)
                raise BlockedActionExecutionError(
                    f"Cannot execute decision {decision.decision_id}: state is BLOCK. Rationale: {decision.rationale}"
                )

            if decision.state == DecisionState.ESCALATE:
                logger.warning("Escalated action %s attempted execution without human review. Aborting.", decision.decision_id)
                raise EscalatedActionExecutionError(
                    f"Cannot execute decision {decision.decision_id}: state is ESCALATE. Requires merchant sign-off."
                )

            if decision.state not in (DecisionState.PASS, DecisionState.MODIFY):
                raise ExecutionSafetyError(
                    f"Cannot execute decision {decision.decision_id}: unrecognized state {decision.state}"
                )

            # 3. Merchant Approval Sign-off enforcement (Precondition 3)
            if getattr(decision, "approval_required", False):
                appr_status = getattr(decision, "approval_status", None)
                if appr_status != ApprovalStatus.APPROVED:
                    logger.warning(
                        "Unapproved action (Decision: %s, Status: %s) attempted execution.",
                        decision.decision_id,
                        appr_status,
                    )
                    raise UnapprovedActionExecutionError(
                        f"Cannot execute decision {decision.decision_id}: approval_status is {appr_status}. "
                        "Merchant sign-off (APPROVED) is strictly required before execution."
                    )

            # 4. Execution Eligibility enforcement (Precondition 4)
            if getattr(decision, "approval_required", False) and not getattr(decision, "is_execution_eligible", False):
                raise ExecutionNotEligibleError(
                    f"Cannot execute decision {decision.decision_id}: is_execution_eligible is False."
                )

            # 5. Approved Action payload exists (Precondition 5)
            if not decision.approved_action:
                raise ExecutionSafetyError(
                    f"Cannot execute decision {decision.decision_id}: approved_action payload is missing."
                )

            # 6. Merchant ID verification (Precondition 6)
            target_merchant = merchant_id or decision.merchant_id
            if merchant_id and decision.merchant_id and merchant_id != decision.merchant_id:
                raise MerchantMismatchError(
                    f"Merchant ID mismatch: request specifies '{merchant_id}', but decision belongs to '{decision.merchant_id}'."
                )

            # 7 & 8. Tamper and Stale hash verification (Preconditions 7 & 8)
            action_id = decision.action_id or getattr(decision, "proposal_id", "")
            if decision.proposal_hash and action_id:
                action_row = ActionRepository.get_action_proposal(action_id)
                if action_row:
                    current_prop_hash = compute_proposal_hash(action_row)
                    if current_prop_hash != decision.proposal_hash:
                        raise StaleDecisionExecutionError(
                            "Proposal integrity hash mismatch: underlying action proposal was modified after decision."
                        )

            if decision.evaluation_hash and decision.evaluation_id:
                eval_row = GuardrailRepository.get_evaluation(decision.evaluation_id)
                if eval_row:
                    current_eval_hash = compute_evaluation_hash(eval_row)
                    if current_eval_hash != decision.evaluation_hash:
                        raise StaleDecisionExecutionError(
                            "Evaluation integrity hash mismatch: underlying guardrail evaluation was modified after decision."
                        )

            # 9. Idempotency Check (Precondition 9)
            existing_exec = ExecutionRepository.get_execution_by_decision(decision.decision_id)
            if existing_exec:
                if existing_exec.get("execution_state") == ExecutionState.COMPLETED.value:
                    logger.info("Decision %s already executed. Returning existing execution.", decision.decision_id)
                    self.audit_engine.record_event(
                        stage=StageType.ACT,
                        actor="ExecutionEngine",
                        action_description="Duplicate execution prevented (idempotent return)",
                        input_payload={"decision_id": decision.decision_id},
                        output_payload={"execution_id": existing_exec["id"], "status": "COMPLETED"},
                    )
                    return ExecutionResult(
                        execution_id=existing_exec["id"],
                        decision_id=existing_exec["decision_id"],
                        action_id=existing_exec.get("action_id", action_id),
                        merchant_id=existing_exec.get("merchant_id", target_merchant),
                        action_type=ActionType(existing_exec.get("action_type", ActionType.OFFER_CAMPAIGN.value)),
                        execution_state=ExecutionState.COMPLETED,
                        status="COMPLETED",
                        success=True,
                        execution_mode=ExecutionMode.SIMULATION,
                        simulated=True,
                        approved_action=existing_exec.get("approved_action", decision.approved_action),
                        result=existing_exec.get("result", {}),
                        output_details=existing_exec.get("result", {}),
                        executed_at=existing_exec.get("executed_at"),
                    )

            # 10. Simulation Mode enforcement (Precondition 10)
            if not self.simulation_mode:
                raise RealExecutionNotAllowedError("Real Paytm API dispatch is strictly prohibited.")

        except ExecutionSafetyError as err:
            self.audit_engine.record_event(
                stage=StageType.ACT,
                actor="ExecutionEngine",
                action_description=f"Execution blocked by safety barrier: {type(err).__name__}",
                input_payload={"decision_id": decision.decision_id},
                output_payload={"error": str(err)},
            )
            raise

        # 11. Create EXECUTING record in Database
        exec_id = f"exec-{uuid.uuid4().hex[:10]}"
        action_type_str = decision.approved_action.get("action_type", ActionType.OFFER_CAMPAIGN.value)
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            action_type = ActionType.OFFER_CAMPAIGN

        ExecutionRepository.create_execution(
            execution_id=exec_id,
            decision_id=decision.decision_id,
            action_id=action_id,
            merchant_id=target_merchant,
            action_type=action_type.value,
            execution_state=ExecutionState.EXECUTING.value,
            execution_mode=ExecutionMode.SIMULATION.value,
            simulated=True,
            approved_action=decision.approved_action,
        )

        self.audit_engine.record_event(
            stage=StageType.ACT,
            actor="ExecutionEngine",
            action_description="Execution started",
            input_payload={"execution_id": exec_id, "decision_id": decision.decision_id},
            output_payload={"execution_state": "EXECUTING"},
        )

        # 12. Run Simulation Adapter using APPROVED_ACTION (Guarantees MODIFY Clamped Parameters)
        try:
            sim_output = self.adapter.simulate_campaign_execution(
                approved_action=decision.approved_action,
                merchant_id=target_merchant,
            )
        except Exception as exc:
            ExecutionRepository.mark_failed(exec_id, str(exc))
            self.audit_engine.record_event(
                stage=StageType.ACT,
                actor="ExecutionEngine",
                action_description="Execution failed during simulation",
                input_payload={"execution_id": exec_id},
                output_payload={"error": str(exc)},
            )
            raise

        # 13. Mark COMPLETED in Database
        ExecutionRepository.mark_completed(exec_id, sim_output)

        # 14. Audit Success
        self.audit_engine.record_event(
            stage=StageType.ACT,
            actor="ExecutionEngine (Simulated Paytm Adapter)",
            action_description=f"Simulated execution completed for {action_type.value}",
            input_payload={"decision_id": decision.decision_id, "execution_id": exec_id},
            output_payload=sim_output,
        )

        return ExecutionResult(
            execution_id=exec_id,
            decision_id=decision.decision_id,
            action_id=action_id,
            merchant_id=target_merchant,
            action_type=action_type,
            execution_state=ExecutionState.COMPLETED,
            status="COMPLETED",
            success=True,
            execution_mode=ExecutionMode.SIMULATION,
            simulated=True,
            approved_action=decision.approved_action,
            result=sim_output,
            output_details=sim_output,
            executed_at=datetime.now(timezone.utc),
        )
