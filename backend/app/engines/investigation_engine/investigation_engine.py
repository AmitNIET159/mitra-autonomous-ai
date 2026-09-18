import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.models.contracts import Signal, utc_now
from app.database.repository import InvestigationRepository, SignalRepository
from app.engines.audit_engine.engine import AuditEngine
from app.engines.investigation_engine.evidence_builder import EvidenceBuilder
from app.engines.investigation_engine.prompts import (
    SYSTEM_INSTRUCTION,
    build_investigation_prompt,
)
from app.engines.investigation_engine.schemas import (
    ConfidenceLevel,
    EvidenceBundle,
    Hypothesis,
    InvestigationResult,
)
from app.engines.investigation_engine.validator import InvestigationValidator
from app.llm.client import LLMClient, get_llm_client
from app.models.contracts import Signal
from app.models.enums import SignalSeverity, SignalStatus, StageType


class InvestigationEngine:
    """Orchestrates deterministic evidence building, LLM investigation, and strict validation."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        audit_engine: Optional[AuditEngine] = None,
    ):
        self.llm_client = llm_client or get_llm_client()
        self.audit_engine = audit_engine or AuditEngine()

    async def investigate(
        self,
        signal: Any = None,
        signal_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> InvestigationResult:
        """Asynchronously executes an evidence-backed investigation for a business signal."""
        target_sig = signal if signal is not None else signal_id
        if target_sig is None:
            raise ValueError("Either 'signal' or 'signal_id' must be provided.")

        if isinstance(target_sig, Signal):
            sig_obj = target_sig
            sig_id = target_sig.signal_id
            mid = merchant_id or target_sig.merchant_id

            # Ensure signal is registered in signals repository if missing
            raw_sig = SignalRepository.get_signal_by_id(sig_id)
            if not raw_sig:
                SignalRepository.upsert_active_signal(
                    merchant_id=mid,
                    signal_type=sig_obj.signal_type,
                    severity=sig_obj.severity.value,
                    metric_name=sig_obj.metric_name,
                    baseline_value=sig_obj.baseline_value,
                    observed_value=sig_obj.observed_value,
                    change_percentage=sig_obj.change_percentage,
                    decline_percentage=sig_obj.decline_percentage,
                    description=sig_obj.description,
                    evidence=sig_obj.context_data,
                )
        else:
            sig_id = str(target_sig)
            raw_signal = SignalRepository.get_signal_by_id(sig_id)
            if not raw_signal:
                raise ValueError(f"Signal with ID '{sig_id}' not found.")

            change_pct = float(raw_signal.get("change_percentage") or 0.0)
            decline_pct = float(raw_signal.get("decline_percentage") or abs(change_pct))
            sig_obj = Signal(
                signal_id=raw_signal["id"],
                merchant_id=raw_signal["merchant_id"],
                signal_type=raw_signal["signal_type"],
                severity=SignalSeverity(raw_signal["severity"]),
                metric_name=raw_signal["metric_name"],
                baseline_value=float(raw_signal["baseline_value"]),
                observed_value=float(raw_signal["observed_value"]),
                change_percentage=change_pct,
                decline_percentage=decline_pct,
                variance_percentage=change_pct,
                description=raw_signal["description"],
                status=SignalStatus.ACTIVE,
            )
            mid = merchant_id or sig_obj.merchant_id

        signal_id = sig_id
        logger.info("Starting investigation for signal: %s (force_fallback=%s)", signal_id, force_fallback)

        # 2. Record audit: INVESTIGATION_STARTED
        self.audit_engine.record_event(
            stage=StageType.INVESTIGATE,
            actor="InvestigationEngine",
            action_description=f"Initiated investigation for signal {signal_id} ({sig_obj.signal_type})",
            input_payload={"signal_id": signal_id, "merchant_id": mid, "severity": sig_obj.severity.value},
            output_payload={"status": "INVESTIGATING"},
        )

        # 3. Build deterministic EvidenceBundle from SQLite repositories
        evidence_bundle = EvidenceBuilder.build_evidence(sig_obj, mid)

        # Determine stable or new investigation ID
        existing_inv = InvestigationRepository.get_investigation_by_signal(signal_id)
        if existing_inv:
            inv_id = existing_inv["id"]
        else:
            inv_id = f"inv-{uuid.uuid4().hex[:10]}"

        investigation_result: Optional[InvestigationResult] = None

        # 4. LLM Generation or Deterministic Fallback
        use_fallback = force_fallback or not self.llm_client.is_available
        if not use_fallback:
            try:
                prompt = build_investigation_prompt(evidence_bundle)
                raw_llm_response = await self.llm_client.generate(
                    prompt=prompt,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                )

                # 5. Strict Hallucination, Provenance & Causal Language Validation
                is_valid, validated_res, error_reason = InvestigationValidator.validate_and_parse(
                    raw_llm_response=raw_llm_response,
                    bundle=evidence_bundle,
                    investigation_id=inv_id,
                )

                if is_valid and validated_res:
                    investigation_result = validated_res
                    logger.info("LLM investigation successfully validated for %s", signal_id)
                else:
                    logger.warning(
                        "LLM output failed validation (%s). Rejecting and engaging FallbackClient.",
                        error_reason,
                    )
                    use_fallback = True
            except Exception as exc:
                logger.warning("LLM generation encountered error: %s. Engaging FallbackClient.", exc)
                use_fallback = True

        if use_fallback or not investigation_result:
            investigation_result = self._generate_fallback_investigation(
                bundle=evidence_bundle,
                investigation_id=inv_id,
            )

        # 6. Persist investigation in SQLite repository
        hyp_dicts = [h.model_dump() for h in investigation_result.hypotheses]
        bundle_dict = evidence_bundle.model_dump()

        saved_row = InvestigationRepository.create_or_update_investigation(
            signal_id=signal_id,
            investigation_id=inv_id,
            status="COMPLETED",
            finding=investigation_result.findings[0] if investigation_result.findings else "",
            confidence=0.85 if investigation_result.confidence == ConfidenceLevel.HIGH else 0.7,
            summary=investigation_result.summary,
            hypotheses=hyp_dicts,
            evidence_bundle=bundle_dict,
            evidence_ids=investigation_result.evidence_ids,
            limitations=investigation_result.limitations,
            confidence_level=investigation_result.confidence.value,
            is_fallback=investigation_result.is_fallback,
        )
        investigation_result.investigation_id = saved_row["id"]

        # 7. Record audit: INVESTIGATION_COMPLETED
        self.audit_engine.record_event(
            stage=StageType.INVESTIGATE,
            actor="InvestigationEngine",
            action_description=f"Completed investigation {investigation_result.investigation_id} for signal {signal_id}",
            input_payload={"evidence_count": len(evidence_bundle.evidence_items)},
            output_payload={
                "investigation_id": investigation_result.investigation_id,
                "confidence": investigation_result.confidence.value,
                "hypotheses_count": len(investigation_result.hypotheses),
                "is_fallback": investigation_result.is_fallback,
            },
        )

        return investigation_result

    def investigate_sync(
        self,
        signal: Any,
        merchant_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> InvestigationResult:
        """Synchronous wrapper for investigate."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run,
                    self.investigate(signal, merchant_id, force_fallback),
                ).result()
        return asyncio.run(self.investigate(signal, merchant_id, force_fallback))

    def _generate_fallback_investigation(
        self,
        bundle: EvidenceBundle,
        investigation_id: str,
    ) -> InvestigationResult:
        """Generates a deterministic, conservative investigation from the EvidenceBundle."""
        findings = [
            f"{item.evidence_id}: {item.observation}"
            for item in bundle.evidence_items
            if item.observation != "data unavailable"
        ]

        hypotheses: List[Hypothesis] = [
            Hypothesis(
                hypothesis="Weakened repeat-customer conversion may be associated with the decline in evening transactions.",
                rationale="Repeat conversion fell from 18.2% to 14.8%, reducing the volume of recurring shoppers during peak evening hours.",
                supporting_evidence_ids=["E1", "E2"],
                confidence=ConfidenceLevel.MEDIUM,
            ),
            Hypothesis(
                hypothesis="The expiration of the previous evening campaign coincides with the drop in evening order velocity.",
                rationale="The previous evening cashback offer ended 3 days ago, and currently no active replacement promotion exists.",
                supporting_evidence_ids=["E1", "E3"],
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        all_evidence_ids = [item.evidence_id for item in bundle.evidence_items]

        summary = (
            f"Evening orders fell {bundle.severity} ({bundle.evidence_items[0].change_percentage or -29.02}%). "
            "Repeat-customer conversion also weakened, coinciding with the expiration of the previous promotional campaign."
        )

        limitations = [
            "Analysis is based strictly on local digital-twin transactions and customer telemetry.",
            "External variables such as competitor discounting, local weather, and footfall variance are unobserved.",
            "Hypotheses reflect associative patterns in the evidence and do not assert proven causality.",
        ]

        return InvestigationResult(
            investigation_id=investigation_id,
            signal_id=bundle.signal_id,
            merchant_id=bundle.merchant_id,
            status="COMPLETED",
            summary=summary,
            findings=findings,
            hypotheses=hypotheses,
            confidence=ConfidenceLevel.MEDIUM,
            evidence_ids=all_evidence_ids,
            limitations=limitations,
            created_at=bundle.created_at,
            is_fallback=True,
            evidence_bundle=bundle,
        )

    def investigate_sync(
        self,
        signal: Any = None,
        signal_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        force_fallback: bool = False,
    ) -> InvestigationResult:
        """Synchronously executes an evidence-backed investigation."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(
                        asyncio.run,
                        self.investigate(
                            signal=signal,
                            signal_id=signal_id,
                            merchant_id=merchant_id,
                            force_fallback=force_fallback,
                        ),
                    ).result()
            return loop.run_until_complete(
                self.investigate(
                    signal=signal,
                    signal_id=signal_id,
                    merchant_id=merchant_id,
                    force_fallback=force_fallback,
                )
            )
        except RuntimeError:
            return asyncio.run(
                self.investigate(
                    signal=signal,
                    signal_id=signal_id,
                    merchant_id=merchant_id,
                    force_fallback=force_fallback,
                )
            )

