import pytest
from app.engines.execution_engine.engine import (
    BlockedActionExecutionError,
    EscalatedActionExecutionError,
    ExecutionEngine,
    UncheckedExecutionAttemptError,
)
from app.engines.guardrail_engine.engine import GuardrailEngine
from app.models.contracts import ActionProposal, Decision
from app.models.enums import ActionType, DecisionState


def test_unchecked_proposal_cannot_execute():
    """CRITICAL SAFETY TEST:
    Raw ActionProposal must NEVER be executed directly by ExecutionEngine.
    """
    engine = ExecutionEngine(simulation_mode=True)
    raw_proposal = ActionProposal(
        signal_id="sig-1",
        merchant_id="MID-101",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount": 20},
        reason="Unchecked attempt",
    )

    with pytest.raises(UncheckedExecutionAttemptError):
        engine.execute(raw_proposal)  # type: ignore[arg-type]


def test_arbitrary_dict_cannot_execute():
    """Raw dictionary representing LLM output must NEVER execute directly."""
    engine = ExecutionEngine(simulation_mode=True)
    raw_dict = {"action": "DISPATCH_PROMOTION", "amount": 5000}

    with pytest.raises(UncheckedExecutionAttemptError):
        engine.execute(raw_dict)  # type: ignore[arg-type]


def test_blocked_decision_cannot_execute():
    """A Decision with state=BLOCK must be strictly rejected by ExecutionEngine."""
    engine = ExecutionEngine(simulation_mode=True)
    blocked_decision = Decision(
        proposal_id="prop-1",
        state=DecisionState.BLOCK,
        approved_action=None,
        rationale="Budget exceeded policy",
        guardrail_result_id="grd-1",
    )

    with pytest.raises(BlockedActionExecutionError):
        engine.execute(blocked_decision)


def test_escalated_decision_cannot_execute_without_signoff():
    """A Decision with state=ESCALATE must be rejected until human approves."""
    engine = ExecutionEngine(simulation_mode=True)
    escalated_decision = Decision(
        proposal_id="prop-2",
        state=DecisionState.ESCALATE,
        approved_action=None,
        rationale="Requires merchant approval",
        requires_human_review=True,
        guardrail_result_id="grd-2",
    )

    with pytest.raises(EscalatedActionExecutionError):
        engine.execute(escalated_decision)


def test_passed_decision_executes_safely():
    """A Decision with state=PASS executes safely."""
    engine = ExecutionEngine(simulation_mode=True)
    approved_decision = Decision(
        proposal_id="prop-3",
        state=DecisionState.PASS,
        approved_action={
            "action_type": ActionType.OFFER_CAMPAIGN.value,
            "parameters": {"discount_percentage": 10.0},
        },
        rationale="Safe parameters verified by guardrails",
        guardrail_result_id="grd-3",
    )

    result = engine.execute(approved_decision)
    assert result.success is True
    assert result.decision_id == approved_decision.decision_id
    assert result.simulated is True


def test_deterministic_guardrail_clamping_to_modify():
    """Guardrails must modify excessive discount parameters to policy ceiling."""
    guardrails = GuardrailEngine(max_discount_pct=20.0)
    excessive_proposal = ActionProposal(
        signal_id="sig-4",
        merchant_id="MID-101",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_percentage": 35.0},
        reason="High discount test",
        estimated_cost_inr=1000.0,
    )

    eval_result = guardrails.evaluate(excessive_proposal)
    assert eval_result.recommended_state == DecisionState.MODIFY
    assert eval_result.modified_parameters is not None
    assert eval_result.modified_parameters["discount_percentage"] == 20.0
