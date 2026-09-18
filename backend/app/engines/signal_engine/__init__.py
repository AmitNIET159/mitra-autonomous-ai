"""Signal Engine package for deterministic business anomaly detection."""
from app.engines.signal_engine.detectors import (
    BaseDetector,
    CampaignUnderperformanceDetector,
    CustomerEngagementDeclineDetector,
    EveningOrderDeclineDetector,
    RepeatCustomerConversionDetector,
    RevenueDeclineDetector,
)
from app.engines.signal_engine.engine import SignalDetectionEngine, SignalEngine
from app.engines.signal_engine.thresholds import DEFAULT_THRESHOLDS, ThresholdConfig

__all__ = [
    "SignalDetectionEngine",
    "SignalEngine",
    "ThresholdConfig",
    "DEFAULT_THRESHOLDS",
    "BaseDetector",
    "EveningOrderDeclineDetector",
    "RepeatCustomerConversionDetector",
    "RevenueDeclineDetector",
    "CampaignUnderperformanceDetector",
    "CustomerEngagementDeclineDetector",
]
