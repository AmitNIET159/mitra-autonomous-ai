from enum import Enum


class DecisionState(str, Enum):
    """Authoritative decision states in MITRA.
    
    CRITICAL: Exactly these 4 states are permitted by project contract.
    """
    PASS = "PASS"
    MODIFY = "MODIFY"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class ApprovalStatus(str, Enum):
    """Merchant sign-off approval statuses for decisions."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOT_REQUIRED = "NOT_REQUIRED"


class SignalSeverity(str, Enum):
    """Severity levels for detected business signals."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    """Categorization of merchant actions MITRA can propose and evaluate."""
    EVENING_REENGAGEMENT_CAMPAIGN = "EVENING_REENGAGEMENT_CAMPAIGN"
    OFFER_CAMPAIGN = "OFFER_CAMPAIGN"
    INVENTORY_RESTOCK = "INVENTORY_RESTOCK"
    QR_PLACEMENT_ALERT = "QR_PLACEMENT_ALERT"
    SOUNDBOX_DIAGNOSTIC = "SOUNDBOX_DIAGNOSTIC"
    CUSTOMER_LOYALTY = "CUSTOMER_LOYALTY"
    EXPIRY_PROMOTION = "EXPIRY_PROMOTION"


class StageType(str, Enum):
    """Autonomous teammate workflow stages."""
    DETECT = "DETECT"
    INVESTIGATE = "INVESTIGATE"
    DECIDE = "DECIDE"
    GUARD = "GUARD"
    ACT = "ACT"
    LEARN = "LEARN"
    AUDIT = "AUDIT"


class InvestigationStatus(str, Enum):
    """Lifecycle status of an investigation."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    INCONCLUSIVE = "INCONCLUSIVE"


class SignalStatus(str, Enum):
    """Lifecycle status of a detected business signal."""
    ACTIVE = "ACTIVE"
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class ExecutionState(str, Enum):
    """Lifecycle states of simulated execution."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ExecutionMode(str, Enum):
    """Execution modes. Strictly SIMULATION in MITRA prototype."""
    SIMULATION = "SIMULATION"


class OutcomeStatus(str, Enum):
    """Lifecycle states of outcome measurement."""
    PENDING = "PENDING"
    MEASURED = "MEASURED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class MeasurementMode(str, Enum):
    """Measurement modes for outcome monitoring. Strictly SIMULATION in prototype."""
    SIMULATION = "SIMULATION"


class ImpactStatus(str, Enum):
    """Lifecycle states of business impact and ROI analysis."""
    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FAILED = "FAILED"


class ImpactClassification(str, Enum):
    """Deterministic classification of simulated business impact."""
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AutonomyMode(str, Enum):
    """Supported merchant autonomy modes in MITRA."""
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    AUTO_APPROVE_SAFE = "AUTO_APPROVE_SAFE"
    FULL_AUTONOMY = "FULL_AUTONOMY"


class ApprovalSource(str, Enum):
    """Authoritative source of decision approval in MITRA."""
    HUMAN_APPROVED = "HUMAN_APPROVED"
    AUTO_APPROVED = "AUTO_APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    PENDING = "PENDING"


class ActorType(str, Enum):
    """Actor identity performing an approval or autonomy decision."""
    MERCHANT = "MERCHANT"
    AUTONOMY_POLICY = "AUTONOMY_POLICY"
    SYSTEM = "SYSTEM"


class AutonomyStatus(str, Enum):
    """Deterministic verdict of autonomy policy evaluation."""
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    AUTO_APPROVED = "AUTO_APPROVED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    REJECTED = "REJECTED"


class AIResponseType(str, Enum):
    """Categorization of AI advisory outputs."""
    SIGNAL_EXPLANATION = "SIGNAL_EXPLANATION"
    ACTION_EXPLANATION = "ACTION_EXPLANATION"
    OUTCOME_SUMMARY = "OUTCOME_SUMMARY"
    BUSINESS_SUMMARY = "BUSINESS_SUMMARY"
    MERCHANT_QA = "MERCHANT_QA"


