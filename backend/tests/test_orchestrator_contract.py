import pytest
from app.engines.guardrail_engine.engine import GuardrailEngine
from app.engines.orchestrator import MITRAOrchestrator
from app.llm.client import FallbackClient
from app.models.contracts import ActionProposal, Signal
from app.models.enums import ActionType, DecisionState, SignalSeverity


@pytest.mark.asyncio
async def test_orchestrator_full_compliant_flow():
    """Verifies that compliant signal runs end-to-end through orchestrator."""
    orchestrator = MITRAOrchestrator(llm_client=FallbackClient())

    signal = Signal(
        merchant_id="MID-DELHI-98234",
        signal_type="AFTERNOON_FOOTFALL_DIP",
        severity=SignalSeverity.MEDIUM,
        metric_name="hourly_transactions",
        baseline_value=25.0,
        observed_value=12.0,
        variance_percentage=-52.0,
        description="Transaction velocity dipped during 2 PM - 5 PM slot",
    )

    result = await orchestrator.run_pipeline_for_signal(signal)

    assert result["signal"] == signal
    assert result["investigation"] is not None
    assert result["proposal"] is not None
    assert result["guardrail"].passed is True
    assert result["decision"].state in (DecisionState.PASS, DecisionState.MODIFY)
    assert result["execution"] is not None
    assert result["execution"].success is True
    assert result["outcome"] is not None
    assert result["audit_events_count"] >= 6


@pytest.mark.asyncio
async def test_orchestrator_blocked_flow_skips_execution():
    """Verifies that when guardrail blocks, execution is safely skipped."""
    # Mock planning engine to produce high risk proposal
    orchestrator = MITRAOrchestrator(
        llm_client=FallbackClient(),
        guardrail_engine=GuardrailEngine(max_budget_inr=500.0),  # low limit
    )

    # Force planning engine to return proposal exceeding low limit
    async def unsafe_plan(inv):
        return ActionProposal(
            signal_id=inv.signal_id,
            merchant_id=inv.merchant_id,
            action_type=ActionType.OFFER_CAMPAIGN,
            parameters={"budget_inr": 50000.0},
            reason="Extravagant campaign",
            estimated_cost_inr=50000.0,
            risk_score=0.95,  # Exceeds max risk
        )

    orchestrator.planning_engine.plan_action = unsafe_plan  # type: ignore[assignment]

    signal = Signal(
        merchant_id="MID-DELHI-98234",
        signal_type="TEST_CRITICAL_SIGNAL",
        severity=SignalSeverity.CRITICAL,
        metric_name="abnormal_volume",
        baseline_value=100.0,
        observed_value=500.0,
        variance_percentage=400.0,
        description="High volatility test",
    )

    result = await orchestrator.run_pipeline_for_signal(signal)

    assert result["guardrail"].recommended_state == DecisionState.BLOCK
    assert result["decision"].state == DecisionState.BLOCK
    # CRITICAL: Execution MUST BE None when blocked
    assert result["execution"] is None
    assert result["outcome"] is None
