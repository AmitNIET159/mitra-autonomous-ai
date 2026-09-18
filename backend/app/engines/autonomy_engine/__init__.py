"""Autonomy Policy Engine package for MITRA (Phase 12)."""

from app.engines.autonomy_engine.engine import AutonomyPolicyEngine
from app.engines.autonomy_engine.rules import (
    AUTO_APPROVE_SAFE_RISK_THRESHOLD,
    FULL_AUTONOMY_RISK_THRESHOLD,
    AutonomyPolicyError,
    BlockedAutonomyOverrideError,
    EscalatedAutonomyOverrideError,
    StaleAutonomyEvaluationError,
    determine_autonomy_verdict,
    evaluate_16_safety_conditions,
    extract_effective_parameters,
)

__all__ = [
    "AutonomyPolicyEngine",
    "AUTO_APPROVE_SAFE_RISK_THRESHOLD",
    "FULL_AUTONOMY_RISK_THRESHOLD",
    "AutonomyPolicyError",
    "BlockedAutonomyOverrideError",
    "EscalatedAutonomyOverrideError",
    "StaleAutonomyEvaluationError",
    "evaluate_16_safety_conditions",
    "determine_autonomy_verdict",
    "extract_effective_parameters",
]
