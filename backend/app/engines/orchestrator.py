from typing import Any, Dict, Optional
from app.core.config import get_settings
from app.core.logging import logger
from app.engines.audit_engine.engine import AuditEngine
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.execution_engine.engine import ExecutionEngine
from app.engines.guardrail_engine.engine import GuardrailEngine
from app.engines.investigation_engine import InvestigationEngine
from app.engines.monitoring_engine import MonitoringEngine
from app.engines.planning_engine import PlanningEngine
from app.engines.signal_engine import SignalEngine
from app.llm.client import LLMClient, get_llm_client
from app.models.contracts import (
    ActionProposal,
    Decision,
    ExecutionResult,
    GuardrailResult,
    Investigation,
    Outcome,
    Signal,
)
from app.models.enums import DecisionState, StageType

settings = get_settings()


class MITRAOrchestrator:
    """Core Orchestrator coordinating MITRA's autonomous teammate workflow.
    
    PIPELINE CONTRACT:
    DETECT -> INVESTIGATE -> DECIDE -> GUARD -> ACT -> LEARN
    
    SAFETY PRINCIPLE:
    "Deterministic systems calculate truth; the LLM interprets it."
    ExecutionEngine can only be called with an approved Decision object.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        guardrail_engine: Optional[GuardrailEngine] = None,
        decision_engine: Optional[DecisionEngine] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        monitoring_engine: Optional[MonitoringEngine] = None,
        audit_engine: Optional[AuditEngine] = None,
    ):
        self.llm_client = llm_client or get_llm_client()
        self.signal_engine = SignalEngine()
        self.investigation_engine = InvestigationEngine(llm_client=self.llm_client)
        self.planning_engine = PlanningEngine(llm_client=self.llm_client)
        self.guardrail_engine = guardrail_engine or GuardrailEngine()
        self.decision_engine = decision_engine or DecisionEngine()
        self.execution_engine = execution_engine or ExecutionEngine(
            simulation_mode=settings.SIMULATION_MODE
        )
        self.monitoring_engine = monitoring_engine or MonitoringEngine(
            simulation_mode=settings.SIMULATION_MODE
        )
        self.audit_engine = audit_engine or AuditEngine()

    async def run_pipeline_for_signal(self, signal: Signal) -> Dict[str, Any]:
        """Runs the complete MITRA workflow for an incoming business signal."""
        logger.info("MITRA Orchestrator processing signal: %s", signal.signal_id)

        # 1. DETECT stage audit
        self.audit_engine.record_event(
            stage=StageType.DETECT,
            actor="SignalEngine",
            action_description=f"Detected anomaly in metric {signal.metric_name}",
            input_payload={"signal_id": signal.signal_id, "merchant_id": signal.merchant_id},
            output_payload=signal.model_dump(mode="json"),
        )

        # 2. INVESTIGATE
        investigation: Investigation = await self.investigation_engine.investigate(signal)
        self.audit_engine.record_event(
            stage=StageType.INVESTIGATE,
            actor=f"InvestigationEngine ({self.llm_client.provider_name})",
            action_description="Investigated root causes and gathered hypotheses",
            input_payload={"signal_id": signal.signal_id},
            output_payload=investigation.model_dump(mode="json"),
        )

        # 3. PLAN
        proposal: ActionProposal = await self.planning_engine.plan_action(investigation)
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor=f"PlanningEngine ({self.llm_client.provider_name})",
            action_description=f"Generated action proposal {proposal.action_type.value}",
            input_payload={"investigation_id": investigation.investigation_id},
            output_payload=proposal.model_dump(mode="json"),
        )

        # 4. GUARD (Deterministic Guardrails)
        guardrail: GuardrailResult = self.guardrail_engine.evaluate(proposal)
        self.audit_engine.record_event(
            stage=StageType.GUARD,
            actor="DeterministicGuardrailEngine",
            action_description=f"Evaluated proposal constraints: {guardrail.recommended_state.value}",
            input_payload=proposal.model_dump(mode="json"),
            output_payload=guardrail.model_dump(mode="json"),
        )

        # 5. DECIDE (Authoritative Decision)
        decision: Decision = self.decision_engine.decide(proposal, guardrail)
        self.audit_engine.record_event(
            stage=StageType.DECIDE,
            actor="DecisionEngine",
            action_description=f"Authoritative decision produced: {decision.state.value}",
            input_payload={"proposal_id": proposal.proposal_id, "guardrail_id": guardrail.result_id},
            output_payload=decision.model_dump(mode="json"),
        )

        # 6. ACT (Execution gated strictly by Decision state)
        execution: Optional[ExecutionResult] = None
        outcome: Optional[Outcome] = None

        if decision.state in (DecisionState.PASS, DecisionState.MODIFY):
            execution = self.execution_engine.execute(decision)
            self.audit_engine.record_event(
                stage=StageType.ACT,
                actor="ExecutionEngine (Simulated Paytm Adapter)",
                action_description=f"Executed {decision.state.value} action: {execution.action_type.value}",
                input_payload=decision.model_dump(mode="json"),
                output_payload=execution.model_dump(mode="json"),
            )

            # 7. LEARN (Post-execution monitoring)
            outcome = self.monitoring_engine.measure_outcome(execution)
            self.audit_engine.record_event(
                stage=StageType.LEARN,
                actor="MonitoringEngine",
                action_description=f"Measured post-action outcome: delta {outcome.delta_percentage}%",
                input_payload={"execution_id": execution.execution_id},
                output_payload=outcome.model_dump(mode="json"),
            )
        else:
            logger.info(
                "Execution bypassed for decision %s because state is %s",
                decision.decision_id,
                decision.state.value,
            )

        return {
            "signal": signal,
            "investigation": investigation,
            "proposal": proposal,
            "guardrail": guardrail,
            "decision": decision,
            "execution": execution,
            "outcome": outcome,
            "audit_events_count": len(self.audit_engine.get_events()),
        }
