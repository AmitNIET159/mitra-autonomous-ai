from dataclasses import dataclass
from typing import Optional
from app.models.enums import SignalSeverity


@dataclass(frozen=True)
class ThresholdConfig:
    """Configurable thresholds for deterministic anomaly classification.
    
    CRITICAL:
    NONE: <5%
    LOW: 5–10%
    MEDIUM: 10–20%
    HIGH: 20–30%
    CRITICAL: >30%
    """
    none_ceiling_pct: float = 5.0
    low_ceiling_pct: float = 10.0
    medium_ceiling_pct: float = 20.0
    high_ceiling_pct: float = 30.0

    def classify_decline(self, decline_percentage: float) -> Optional[SignalSeverity]:
        """Classifies decline percentage into deterministic severity.
        
        Returns None if below the minimum anomaly threshold (<5%).
        """
        if decline_percentage < self.none_ceiling_pct:
            return None
        elif decline_percentage < self.low_ceiling_pct:
            return SignalSeverity.LOW
        elif decline_percentage < self.medium_ceiling_pct:
            return SignalSeverity.MEDIUM
        elif decline_percentage < self.high_ceiling_pct:
            return SignalSeverity.HIGH
        else:
            return SignalSeverity.CRITICAL


# Global default threshold configuration
DEFAULT_THRESHOLDS = ThresholdConfig()
