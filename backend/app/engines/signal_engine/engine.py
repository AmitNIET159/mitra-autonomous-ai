from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.database.repository import MerchantRepository, SignalRepository
from app.engines.audit_engine.engine import AuditEngine
from app.engines.signal_engine.detectors import (
    CampaignUnderperformanceDetector,
    CustomerEngagementDeclineDetector,
    EveningOrderDeclineDetector,
    RepeatCustomerConversionDetector,
    RevenueDeclineDetector,
)
from app.engines.signal_engine.thresholds import DEFAULT_THRESHOLDS, ThresholdConfig
from app.models.contracts import DetectionResult, Signal
from app.models.enums import SignalSeverity, SignalStatus, StageType


class SignalDetectionEngine:
    """Deterministic Signal Detection Engine for MITRA.
    
    CORE PRINCIPLE:
    "Deterministic systems calculate truth; the LLM interprets it."
    
    This engine derives mathematical anomalies directly from SQLite digital-twin data.
    NO LLM is utilized in this layer.
    """

    def __init__(
        self,
        thresholds: Optional[ThresholdConfig] = None,
        audit_engine: Optional[AuditEngine] = None,
    ):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.audit_engine = audit_engine or AuditEngine()
        self.detectors = [
            EveningOrderDeclineDetector(thresholds=self.thresholds),
            RepeatCustomerConversionDetector(thresholds=self.thresholds),
            RevenueDeclineDetector(thresholds=self.thresholds),
            CampaignUnderperformanceDetector(thresholds=self.thresholds),
            CustomerEngagementDeclineDetector(thresholds=self.thresholds),
        ]

    def detect_signals(self, merchant_id: str = "MID-DEMO-98234") -> List[Signal]:
        """Runs all deterministic detectors and persists/updates active signals."""
        merchant = MerchantRepository.get_merchant(merchant_id)
        if not merchant:
            logger.warning("SignalDetectionEngine: merchant %s not found. Aborting detection.", merchant_id)
            return []

        logger.info("SignalDetectionEngine: Running deterministic detection for %s", merchant_id)

        # 1. Audit detection start
        self.audit_engine.record_event(
            stage=StageType.DETECT,
            actor="SignalDetectionEngine",
            action_description="Initiated deterministic signal detection scan over digital twin telemetry",
            input_payload={"merchant_id": merchant_id},
            output_payload={"status": "IN_PROGRESS", "detectors_count": len(self.detectors)},
        )

        detected_signals: List[Signal] = []
        active_detected_types: List[str] = []

        # 2. Run detectors deterministically
        for detector in self.detectors:
            try:
                res: Optional[DetectionResult] = detector.detect(merchant_id)
                if res:
                    active_detected_types.append(res.signal_type)

                    # Persist / update active signal idempotently
                    raw_row = SignalRepository.upsert_active_signal(
                        merchant_id=merchant_id,
                        signal_type=res.signal_type,
                        severity=res.severity.value,
                        metric_name=res.metric_name,
                        baseline_value=res.baseline_value,
                        observed_value=res.current_value,
                        change_percentage=res.change_percentage,
                        decline_percentage=res.decline_percentage,
                        description=res.description,
                        evidence=res.evidence,
                    )

                    signal_obj = Signal(
                        signal_id=raw_row["id"],
                        merchant_id=raw_row["merchant_id"],
                        signal_type=raw_row["signal_type"],
                        severity=SignalSeverity(raw_row["severity"]),
                        metric_name=raw_row["metric_name"],
                        baseline_value=float(raw_row["baseline_value"]),
                        observed_value=float(raw_row["observed_value"]),
                        change_percentage=float(raw_row["change_percentage"]),
                        decline_percentage=float(raw_row["decline_percentage"]),
                        variance_percentage=float(raw_row["change_percentage"]),
                        description=raw_row["description"],
                        status=SignalStatus(raw_row["status"]),
                        context_data=res.evidence,
                    )
                    detected_signals.append(signal_obj)

                    # Audit signal detection
                    self.audit_engine.record_event(
                        stage=StageType.DETECT,
                        actor="SignalDetectionEngine",
                        action_description=f"Detected {res.severity.value} severity signal: {res.signal_type}",
                        input_payload={"metric_name": res.metric_name, "baseline": res.baseline_value},
                        output_payload={
                            "signal_id": signal_obj.signal_id,
                            "signal_type": res.signal_type,
                            "severity": res.severity.value,
                            "change_percentage": res.change_percentage,
                            "decline_percentage": res.decline_percentage,
                        },
                    )
            except Exception as exc:
                logger.error("Detector %s failed: %s", detector.signal_type, exc)

        # 3. Resolve disappeared signals (idempotent resolution)
        resolved_ids = SignalRepository.resolve_disappeared_signals(merchant_id, active_detected_types)
        for r_id in resolved_ids:
            self.audit_engine.record_event(
                stage=StageType.DETECT,
                actor="SignalDetectionEngine",
                action_description=f"Marked disappeared signal {r_id} as RESOLVED",
                input_payload={"signal_id": r_id},
                output_payload={"status": "RESOLVED"},
            )

        logger.info(
            "SignalDetectionEngine scan complete for %s: %d active signals detected.",
            merchant_id,
            len(detected_signals),
        )
        return detected_signals

    def scan_signals(self, merchant_id: str) -> List[Signal]:
        """Backward-compatibility alias for MITRAOrchestrator."""
        return self.detect_signals(merchant_id)


# Backward-compatible alias
SignalEngine = SignalDetectionEngine
