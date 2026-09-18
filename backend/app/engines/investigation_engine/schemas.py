from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Constrained confidence levels for MITRA investigations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceCategory(str, Enum):
    """Categorization of gathered deterministic evidence items."""
    PRIMARY_SIGNAL = "PRIMARY_SIGNAL"
    CUSTOMER_BEHAVIOR = "CUSTOMER_BEHAVIOR"
    CAMPAIGN_CONTEXT = "CAMPAIGN_CONTEXT"
    TARGET_AUDIENCE = "TARGET_AUDIENCE"
    BUSINESS_CONTEXT = "BUSINESS_CONTEXT"


class EvidenceItem(BaseModel):
    """An individual piece of deterministically verified evidence."""
    evidence_id: str = Field(description="Unique evidence identifier, e.g. E1, E2")
    category: EvidenceCategory = Field(description="Domain category of this evidence item")
    metric: str = Field(description="Name of the underlying metric or business dimension")
    baseline: Any = Field(description="Historical baseline value or benchmark")
    current: Any = Field(description="Observed current value in the evaluation window")
    change_percentage: Optional[float] = Field(default=None, description="Deterministic percentage change")
    observation: str = Field(description="Factual, un-hypothesized observation statement")
    source: str = Field(description="Deterministic origin (e.g. transactions, customers, campaigns)")


class EvidenceBundle(BaseModel):
    """Complete bundle of deterministic evidence assembled for a business signal."""
    signal_id: str
    signal_type: str
    severity: str
    merchant_id: str
    primary_metric: str
    created_at: str
    evidence_items: List[EvidenceItem] = Field(default_factory=list)


class Hypothesis(BaseModel):
    """A plausible hypothesis explaining a signal without asserting unproven causality."""
    hypothesis: str = Field(description="Statement of possible association (must not assert proven causality)")
    rationale: str = Field(description="Logical reasoning linking the supporting evidence items")
    supporting_evidence_ids: List[str] = Field(
        description="List of evidence IDs (e.g. ['E1', 'E2']) grounding this hypothesis"
    )
    confidence: ConfidenceLevel = Field(
        description="Confidence level (HIGH requires >=2 independent evidence items)"
    )


class InvestigationResult(BaseModel):
    """Structured, validated output of a MITRA signal investigation."""
    investigation_id: str
    signal_id: str
    merchant_id: str
    status: str = "COMPLETED"
    summary: str
    findings: List[str] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    created_at: str
    is_fallback: bool = False
    evidence_bundle: Optional[EvidenceBundle] = None
