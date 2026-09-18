import pytest
from pydantic import ValidationError
from app.models.contracts import (
    ActionProposal,
    AuditEvent,
    Decision,
    ExecutionResult,
    GuardrailResult,
    Investigation,
    Outcome,
    Signal,
)
from app.models.enums import (
    ActionType,
    DecisionState,
    InvestigationStatus,
    SignalSeverity,
    StageType,
)


def test_decision_states_are_strictly_four():
    """MITRA must support exactly PASS, MODIFY, BLOCK, ESCALATE."""
    permitted_states = {"PASS", "MODIFY", "BLOCK", "ESCALATE"}
    actual_states = {s.value for s in DecisionState}
    assert actual_states == permitted_states


def test_signal_contract_validation():
    """Validates Signal model creation and field validation."""
    signal = Signal(
        merchant_id="MID-101",
        signal_type="GMV_DROP",
        severity=SignalSeverity.HIGH,
        metric_name="daily_soundbox_gmv",
        baseline_value=15000.0,
        observed_value=9500.0,
        variance_percentage=-36.67,
        description="Soundbox GMV dropped significantly below normal weekday baseline",
    )
    assert signal.signal_id.startswith("sig-")
    assert signal.severity == SignalSeverity.HIGH
    assert signal.variance_percentage == -36.67


def test_action_proposal_contract():
    """Validates ActionProposal model."""
    proposal = ActionProposal(
        signal_id="sig-test",
        merchant_id="MID-101",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_percentage": 15.0, "budget_inr": 2000.0},
        reason="Boost footfall during afternoon dip",
        confidence=0.9,
        estimated_cost_inr=2000.0,
    )
    assert proposal.proposal_id.startswith("prop-")
    assert proposal.confidence == 0.9


def test_invalid_decision_state_rejected():
    """Ensures arbitrary decision strings are strictly rejected by Pydantic."""
    with pytest.raises(ValidationError):
        Decision(
            proposal_id="prop-test",
            state="ARBITRARY_APPROVE",  # type: ignore[arg-type]
            rationale="Invalid state",
            guardrail_result_id="grd-test",
        )


def test_audit_event_contract():
    """Validates AuditEvent data serialization and structure."""
    event = AuditEvent(
        stage=StageType.GUARD,
        actor="DeterministicGuardrailEngine",
        action_description="Evaluated budget constraints",
        input_payload={"budget": 1000},
        output_payload={"passed": True},
        integrity_hash="abcdef123456",
    )
    assert event.stage == StageType.GUARD
    assert event.integrity_hash == "abcdef123456"
