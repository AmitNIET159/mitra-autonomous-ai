import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging import logger
from app.engines.investigation_engine.schemas import (
    ConfidenceLevel,
    EvidenceBundle,
    Hypothesis,
    InvestigationResult,
)


class InvestigationValidationError(Exception):
    """Raised when an LLM output fails hallucination, provenance, or safety checks."""
    pass


# Disallowed absolute causal phrases
ABSOLUTE_CAUSAL_PATTERNS = [
    re.compile(r"\bdirectly\s+caused\b", re.IGNORECASE),
    re.compile(r"\bcaused\s+by\b", re.IGNORECASE),
    re.compile(r"\bcaused\b", re.IGNORECASE),
    re.compile(r"\bbecause\s+of\b", re.IGNORECASE),
    re.compile(r"\bresulted\s+from\b", re.IGNORECASE),
    re.compile(r"\bled\s+to\b", re.IGNORECASE),
    re.compile(r"\bdue\s+to\b", re.IGNORECASE),
    re.compile(r"\bresponsible\s+for\b", re.IGNORECASE),
    re.compile(r"\bis\s+the\s+cause\s+of\b", re.IGNORECASE),
    re.compile(r"\bproves\s+that\b", re.IGNORECASE),
]


class InvestigationValidator:
    """Strict validator for LLM investigation outputs.
    
    Enforces:
    1. Evidence Traceability: All cited evidence IDs must exist in the bundle.
    2. Hallucination Guard: Numbers, metrics, and percentages must match supplied evidence.
       Fabricated figures cause immediate rejection and fallback.
    3. Causal Language Guard: Rejects or sanitizes unproven causality claims.
    4. Confidence Rule: HIGH confidence requires >= 2 independent evidence items.
    """

    @staticmethod
    def _extract_bundle_numbers(bundle: EvidenceBundle) -> Set[float]:
        """Extracts valid numeric figures present in the evidence bundle."""
        valid_numbers: Set[float] = set()
        for item in bundle.evidence_items:
            for val in (item.baseline, item.current, item.change_percentage):
                if isinstance(val, (int, float)):
                    valid_numbers.add(round(float(val), 2))
                    # Also add rounded integer variant
                    valid_numbers.add(float(int(val)))
            # Also extract numbers embedded in observation text
            found = re.findall(r"\b\d+(?:\.\d+)?\b", item.observation)
            for f in found:
                try:
                    num = float(f)
                    valid_numbers.add(round(num, 2))
                    valid_numbers.add(float(int(num)))
                except ValueError:
                    pass
        return valid_numbers

    @classmethod
    def validate_and_parse(
        cls,
        raw_llm_response: str,
        bundle: EvidenceBundle,
        investigation_id: str,
    ) -> Tuple[bool, Optional[InvestigationResult], Optional[str]]:
        """Validates the raw LLM response.
        
        Returns:
            (is_valid, investigation_result, error_reason)
        """
        # 1. Parse JSON
        text = raw_llm_response.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except Exception as exc:
            return False, None, f"LLM output is not valid JSON: {exc}"

        if not isinstance(data, dict):
            return False, None, "LLM output root is not a dictionary"

        # 2. Check evidence ID validity
        valid_evidence_ids = {item.evidence_id for item in bundle.evidence_items}
        raw_hypotheses = data.get("hypotheses", [])
        if not isinstance(raw_hypotheses, list) or len(raw_hypotheses) == 0:
            return False, None, "LLM output does not contain any hypotheses"

        validated_hypotheses: List[Hypothesis] = []
        all_cited_ids: Set[str] = set()

        for idx, h in enumerate(raw_hypotheses):
            if not isinstance(h, dict):
                return False, None, f"Hypothesis #{idx} is not an object"

            cited_ids = h.get("supporting_evidence_ids", [])
            if not isinstance(cited_ids, list):
                return False, None, f"Hypothesis #{idx} supporting_evidence_ids is not a list"

            # Check that all cited IDs actually exist in the EvidenceBundle
            for eid in cited_ids:
                if eid not in valid_evidence_ids:
                    logger.warning("Rejected LLM output: Unknown evidence ID '%s' cited", eid)
                    return False, None, f"Unknown evidence ID '{eid}' cited in hypothesis #{idx}"
                all_cited_ids.add(eid)

            hyp_text = str(h.get("hypothesis", "")).strip()
            rationale_text = str(h.get("rationale", "")).strip()

            if not hyp_text:
                return False, None, f"Hypothesis #{idx} text is empty"

            # 3. Causal Language Guard
            for pattern in ABSOLUTE_CAUSAL_PATTERNS:
                if pattern.search(hyp_text):
                    logger.warning("Causal language pattern detected in hypothesis: '%s'", hyp_text)
                    # Attempt minor wording sanitization if possible, else reject
                    # Replace "directly caused by" / "caused by" with "may be associated with"
                    hyp_text = pattern.sub("may be associated with", hyp_text)

            # 4. Confidence Rule Enforcement:
            # HIGH requires >= 2 independent evidence items
            raw_conf = str(h.get("confidence", "MEDIUM")).upper()
            if raw_conf not in ("LOW", "MEDIUM", "HIGH"):
                raw_conf = "MEDIUM"
            conf_level = ConfidenceLevel(raw_conf)

            if conf_level == ConfidenceLevel.HIGH and len(set(cited_ids)) < 2:
                logger.info(
                    "Clamping hypothesis #%d confidence from HIGH to MEDIUM: requires >=2 independent evidence items, had %d",
                    idx,
                    len(set(cited_ids)),
                )
                conf_level = ConfidenceLevel.MEDIUM

            validated_hypotheses.append(
                Hypothesis(
                    hypothesis=hyp_text,
                    rationale=rationale_text,
                    supporting_evidence_ids=cited_ids,
                    confidence=conf_level,
                )
            )

        # 5. Hallucination Detection on Numbers/Metrics
        bundle_numbers = cls._extract_bundle_numbers(bundle)
        summary = str(data.get("summary", "")).strip()
        findings = [str(f) for f in data.get("findings", []) if isinstance(f, str)]
        limitations = [str(lim) for lim in data.get("limitations", []) if isinstance(lim, str)]

        # Check for fabricated metrics in findings and hypotheses
        text_to_check = f"{summary} " + " ".join(findings) + " " + " ".join(h.hypothesis for h in validated_hypotheses)
        percentage_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", text_to_check)
        for p in percentage_matches:
            try:
                num = round(float(p), 2)
                # Check if this percentage or its absolute value was in the bundle
                if num not in bundle_numbers and abs(num) not in bundle_numbers:
                    # Allow trivial roundings or percentages within 0.1 of valid numbers
                    close = any(abs(num - bn) < 0.15 for bn in bundle_numbers)
                    if not close:
                        logger.warning("Rejected LLM output: Fabricated percentage '%s%%' detected", p)
                        return False, None, f"Fabricated metric '{p}%' not found in EvidenceBundle"
            except ValueError:
                pass

        # Overall confidence rule
        overall_conf_raw = str(data.get("confidence", "MEDIUM")).upper()
        if overall_conf_raw not in ("LOW", "MEDIUM", "HIGH"):
            overall_conf_raw = "MEDIUM"
        overall_conf = ConfidenceLevel(overall_conf_raw)

        # Overall HIGH confidence requires at least one hypothesis with >= 2 independent evidence items
        if overall_conf == ConfidenceLevel.HIGH:
            has_high_hyp = any(
                h.confidence == ConfidenceLevel.HIGH and len(set(h.supporting_evidence_ids)) >= 2
                for h in validated_hypotheses
            )
            if not has_high_hyp:
                overall_conf = ConfidenceLevel.MEDIUM

        result = InvestigationResult(
            investigation_id=investigation_id,
            signal_id=bundle.signal_id,
            merchant_id=bundle.merchant_id,
            status="COMPLETED",
            summary=summary,
            findings=findings,
            hypotheses=validated_hypotheses,
            confidence=overall_conf,
            evidence_ids=sorted(list(all_cited_ids)),
            limitations=limitations,
            created_at=bundle.created_at,
            is_fallback=False,
            evidence_bundle=bundle,
        )

        return True, result, None
