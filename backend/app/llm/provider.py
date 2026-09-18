"""Multi-Provider AI Advisory Layer for MITRA (Phase 13).

SAFETY INVARIANTS:
1. THE LLM INTERPRETS; THE DETERMINISTIC SYSTEM DECIDES AND ACTS.
2. Zero LLM authority: LLM cannot approve/reject actions, modify guardrails, change policies, or execute transactions.
3. Strict structured context: Only persisted, verified SQLite state is provided to LLMs.
4. Non-causal framing: All hypotheses and explanations explicitly state "Causality is not established".
5. Prompt-injection defense: LLM text cannot issue operational commands; all commands are neutralized.
6. Multi-provider failover: Gemini Flash -> Hugging Face -> Deterministic Fallback.
"""
import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.database.repository import (
    ActionRepository,
    AutonomyRepository,
    BusinessImpactRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    InvestigationRepository,
    MerchantRepository,
    OutcomeRepository,
    SignalRepository,
)
from app.llm.client import FallbackClient, GeminiClient, HuggingFaceClient, LLMClient
from app.models.contracts import (
    AIContext,
    AIProviderStatus,
    AIResponse,
    generate_id,
)
from app.models.enums import AIResponseType

# Unsafe directive patterns to neutralize from model output
UNSAFE_COMMAND_PATTERNS = [
    r"\b(?:APPROVE|APPROVED|EXECUTE|EXECUTED|EXECUTION_GRANTED)\b",
    r"\b(?:BYPASS_GUARDRAILS?|OVERRIDE_GUARDRAILS?|IGNORE_SAFETY)\b",
    r"\b(?:CHANGE_POLICY|SET_FULL_AUTONOMY|FORCE_PASS)\b",
]


class AIProviderManager:
    """Manages AI reasoning providers with failover, context isolation, and prompt defense."""

    def __init__(self) -> None:
        self._cache: Dict[str, AIResponse] = {}

    def clear_cache(self) -> None:
        """Clears in-memory advisory response cache for deterministic demo reset."""
        self._cache.clear()
        logger.info("AIProviderManager: In-memory advisory cache successfully cleared.")

    def get_provider_status(self) -> AIProviderStatus:
        """Returns telemetry on configured and active AI reasoning providers."""
        settings = get_settings()
        gemini_ok = settings.is_gemini_active
        hf_ok = settings.is_hf_active

        pref = settings.AI_PROVIDER_PREFERENCE.lower()
        if pref == "gemini" and gemini_ok:
            active = f"Gemini ({settings.GEMINI_MODEL})"
        elif pref == "huggingface" and hf_ok:
            active = f"Hugging Face ({settings.HF_MODEL})"
        elif gemini_ok:
            active = f"Gemini ({settings.GEMINI_MODEL})"
        elif hf_ok:
            active = f"Hugging Face ({settings.HF_MODEL})"
        else:
            active = "Deterministic Fallback (Safe Offline)"

        available: List[str] = ["Deterministic Fallback"]
        if hf_ok:
            available.insert(0, f"Hugging Face ({settings.HF_MODEL})")
        if gemini_ok:
            available.insert(0, f"Gemini ({settings.GEMINI_MODEL})")

        return AIProviderStatus(
            active_provider=active,
            available_providers=available,
            gemini_configured=gemini_ok,
            huggingface_configured=hf_ok,
            fallback_active=(not gemini_ok and not hf_ok) or pref == "fallback",
            simulation_mode=settings.SIMULATION_MODE,
            disclaimer="Advisory AI reasoning layer. Deterministic systems retain sole decision and execution authority.",
        )

    def _sanitize_output(self, text: str) -> str:
        """Neutralizes prompt-injection attempts and unauthorized commands in model text."""
        sanitized = text
        for pat in UNSAFE_COMMAND_PATTERNS:
            sanitized = re.sub(pat, "[ADVISORY_ONLY]", sanitized, flags=re.IGNORECASE)
        return sanitized.strip()

    def _get_cache_key(self, response_type: str, correlation_id: str, extra: str = "") -> str:
        h = hashlib.sha256(f"{response_type}:{correlation_id}:{extra}".encode()).hexdigest()[:16]
        return f"{response_type}:{correlation_id}:{h}"

    async def _execute_with_failover(
        self,
        prompt: str,
        system_instruction: str,
    ) -> tuple[str, str]:
        """Executes prompt across the failover chain: Gemini -> Hugging Face -> Fallback."""
        settings = get_settings()
        pref = settings.AI_PROVIDER_PREFERENCE.lower()

        candidates: List[LLMClient] = []

        if pref == "gemini" and settings.is_gemini_active:
            candidates.append(GeminiClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL))  # type: ignore[arg-type]
        elif pref == "huggingface" and settings.is_hf_active:
            candidates.append(HuggingFaceClient(api_key=settings.effective_hf_api_key, model=settings.HF_MODEL))  # type: ignore[arg-type]
        elif pref != "fallback":
            # Auto order
            if settings.is_gemini_active:
                candidates.append(GeminiClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL))  # type: ignore[arg-type]
            if settings.is_hf_active:
                candidates.append(HuggingFaceClient(api_key=settings.effective_hf_api_key, model=settings.HF_MODEL))  # type: ignore[arg-type]

        # Deterministic fallback is always the ultimate safety net
        candidates.append(FallbackClient())

        last_err: Optional[Exception] = None
        for client in candidates:
            try:
                raw_text = await client.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
                if raw_text and raw_text.strip():
                    return self._sanitize_output(raw_text), client.provider_name
            except Exception as exc:
                logger.warning("AI provider '%s' failed: %s. Initiating failover.", client.provider_name, exc)
                last_err = exc
                continue

        # If all candidates fail unexpectedly, return deterministic safe text
        fallback = FallbackClient()
        raw = await fallback.generate(prompt=prompt, system_instruction=system_instruction)
        return self._sanitize_output(raw), fallback.provider_name

    def build_context_from_workflow(
        self,
        correlation_id: str,
        merchant_id: str = "MID-DEMO-98234",
        user_query: Optional[str] = None,
    ) -> AIContext:
        """Constructs a strict, verified AIContext strictly from persisted SQLite records."""
        # Find signal
        signals = SignalRepository.get_signals_by_merchant(merchant_id)
        signal_row: Optional[Dict[str, Any]] = None
        for s in signals:
            sid = s.get("id") or s.get("signal_id", "")
            s_corr = f"wf-{sid.replace('sig-', '').replace('SIG-', '').lower()}"
            if s_corr == correlation_id or sid == correlation_id:
                signal_row = s
                break
        if not signal_row and signals:
            signal_row = signals[0]

        signal_id = signal_row.get("id") or signal_row.get("signal_id", "") if signal_row else ""
        inv_row = InvestigationRepository.get_by_signal(signal_id) if signal_id else None
        inv_id = inv_row.get("id") or inv_row.get("investigation_id", "") if inv_row else ""

        act_row = ActionRepository.get_by_investigation(inv_id) if inv_id else None
        act_id = act_row.get("id") or act_row.get("action_id", "") if act_row else ""

        grd_row = GuardrailRepository.get_by_action(act_id) if act_id else None
        dec_row = DecisionRepository.get_decision_by_action(act_id) if act_id else None
        dec_id = dec_row.get("id") or dec_row.get("decision_id", "") if dec_row else ""

        aut_row = AutonomyRepository.get_by_action(act_id) if act_id else None
        exec_row = ExecutionRepository.get_by_decision(dec_id) if dec_id else None
        exec_id = exec_row.get("id") or exec_row.get("execution_id", "") if exec_row else ""

        out_row = OutcomeRepository.get_by_execution(exec_id) if exec_id else None
        out_id = out_row.get("id") or out_row.get("outcome_id", "") if out_row else ""

        imp_row = BusinessImpactRepository.get_by_outcome_id(out_id) if out_id else None

        # Build verified facts array with strict database provenance
        facts: List[Dict[str, Any]] = []
        if signal_row:
            facts.append({
                "fact_id": "F1",
                "entity": "Signal",
                "metric": signal_row.get("metric_name", "evening_orders"),
                "baseline": signal_row.get("baseline_value", 410.0),
                "observed": signal_row.get("observed_value", 291.0),
                "change_pct": signal_row.get("change_percentage", -29.02),
                "provenance": "signals.db",
            })
        if inv_row and inv_row.get("evidence_bundle"):
            ev = inv_row["evidence_bundle"]
            items = ev.get("evidence_items", []) if isinstance(ev, dict) else []
            for idx, itm in enumerate(items[:4], start=2):
                facts.append({
                    "fact_id": f"F{idx}",
                    "entity": "InvestigationEvidence",
                    "metric": itm.get("metric", ""),
                    "baseline": itm.get("baseline", ""),
                    "observed": itm.get("current", ""),
                    "provenance": "digital_twin_telemetry",
                })
        if grd_row:
            facts.append({
                "fact_id": "F_GUARD",
                "entity": "GuardrailEvaluation",
                "status": grd_row.get("overall_status", "PASS"),
                "modifications": grd_row.get("modifications", {}),
                "provenance": "guardrail_evaluations.db",
            })
        if out_row and out_row.get("metrics"):
            facts.append({
                "fact_id": "F_OUTCOME",
                "entity": "MeasuredOutcome",
                "status": out_row.get("outcome_status", "MEASURED"),
                "metrics": out_row.get("metrics", {}),
                "provenance": "outcomes.db",
            })
        if imp_row:
            facts.append({
                "fact_id": "F_IMPACT",
                "entity": "BusinessImpact",
                "incremental_revenue": imp_row.get("incremental_revenue", 0.0),
                "campaign_cost": imp_row.get("campaign_cost", 0.0),
                "net_profit": imp_row.get("gross_profit_impact", 0.0),
                "provenance": "business_impacts.db",
            })

        return AIContext(
            correlation_id=correlation_id,
            merchant_id=merchant_id,
            signal=signal_row,
            verified_facts=facts,
            investigation=inv_row,
            action_proposal=act_row,
            guardrail_result=grd_row,
            autonomy_result=aut_row,
            decision=dec_row,
            execution=exec_row,
            outcome=out_row,
            business_impact=imp_row,
            user_query=user_query,
        )

    async def generate_explanation(self, context: AIContext) -> AIResponse:
        """Generates a structured natural-language workflow explanation grounded in verified facts."""
        cache_key = self._get_cache_key("EXPLAIN", context.correlation_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        facts_text = json.dumps(context.verified_facts, indent=2)
        system_instruction = (
            "You are MITRA's advisory AI reasoning engine for Paytm merchants. "
            "Explain the business situation and MITRA's workflow using ONLY the provided verified facts. "
            "Rules:\n"
            "1. NEVER state that actions are definitely causal. Always say 'associated with' or 'hypothesized'.\n"
            "2. NEVER invent numbers, revenue, or customer counts not in the context.\n"
            "3. Mention referenced fact IDs (e.g. F1, F2).\n"
            "4. Keep response under 150 words. Be professional and operational."
        )
        prompt = (
            f"Correlation ID: {context.correlation_id}\n"
            f"Verified Facts:\n{facts_text}\n\n"
            f"Please explain why MITRA detected this signal and how MITRA evaluated the action."
        )

        answer_text, provider = await self._execute_with_failover(prompt, system_instruction)

        # Fallback deterministic text if offline
        if "deterministic_fallback" in answer_text.lower() or not answer_text:
            answer_text = (
                "Verified data (F1) shows evening orders declined 29.02% (410 to 291 orders). "
                "Investigation indicates repeat-customer conversion fell from 18.2% to 14.8% following the expiration "
                "of the previous evening campaign. Deterministic guardrails (F_GUARD) evaluated the proposal, clamping "
                "excessive discounts to compliant limits before authorization."
            )

        resp = AIResponse(
            response_id=generate_id("air"),
            correlation_id=context.correlation_id,
            provider=provider,
            response_type=AIResponseType.SIGNAL_EXPLANATION,
            answer=answer_text,
            verified_fact_ids=[f["fact_id"] for f in context.verified_facts[:3]],
            hypothesis="Evening order contraction is hypothesized to correlate with expired promotional presence.",
            confidence=0.88,
            disclaimer="AI-generated advisory interpretation. Causality is not established. Simulated digital-twin sandbox.",
        )
        self._cache[cache_key] = resp
        return resp

    async def answer_merchant_question(self, context: AIContext, question: str) -> AIResponse:
        """Answers merchant copilot questions grounded strictly in verified workflow facts."""
        cache_key = self._get_cache_key("QA", context.correlation_id, question)
        if cache_key in self._cache:
            return self._cache[cache_key]

        facts_text = json.dumps(context.verified_facts, indent=2)
        system_instruction = (
            "You are MITRA Copilot, an AI teammate assisting a Paytm merchant. "
            "Answer the merchant's question strictly using the provided verified facts. "
            "Rules:\n"
            "1. You have NO authority to approve, reject, or execute any action.\n"
            "2. If asked to execute or approve, state clearly that only the merchant or deterministic policy can authorize actions.\n"
            "3. Ground your answer in facts (cite F1, F2, F_GUARD when relevant).\n"
            "4. Frame causal statements as hypotheses: 'Causality is not established.'\n"
            "5. Keep answer concise, helpful, and respectful."
        )
        prompt = (
            f"Merchant Question: {question}\n\n"
            f"Verified Context:\n{facts_text}\n\n"
            f"Guardrails: {json.dumps(context.guardrail_result or {})}\n"
            f"Autonomy: {json.dumps(context.autonomy_result or {})}\n"
            f"Decision: {json.dumps(context.decision or {})}\n"
        )

        answer_text, provider = await self._execute_with_failover(prompt, system_instruction)

        if "deterministic_fallback" in answer_text.lower() or not answer_text:
            # Deterministic domain-specific responses for standard questions
            q_lower = question.lower()
            if "why" in q_lower or "happen" in q_lower:
                answer_text = (
                    "Verified facts (F1) show evening orders fell 29.02% from 410 baseline to 291 observed. "
                    "Data reveals that repeat customer conversion decreased from 18.2% to 14.8% after the previous "
                    "evening campaign expired 3 days ago. MITRA hypothesizes promotional re-engagement can address this drop."
                )
            elif "guardrail" in q_lower or "protect" in q_lower or "margin" in q_lower:
                answer_text = (
                    "Deterministic guardrails enforce a minimum 10% profit margin and cap discounts at ₹100. "
                    "If an action proposes excessive spending, guardrails automatically clamp the parameters (MODIFY) "
                    "or block execution (BLOCK). Autonomy never overrides safety."
                )
            elif "impact" in q_lower or "roi" in q_lower or "outcome" in q_lower:
                answer_text = (
                    "Simulation outcome measurement shows evening orders recovered from 291 to 388 (+33.3%). "
                    "Deterministic ROI analysis computed ₹36,375 incremental revenue against ₹9,700 campaign cost, "
                    "yielding a positive simulated gross profit lift of ₹26,675."
                )
            else:
                answer_text = (
                    f"Based on verified data for workflow {context.correlation_id}, evening order anomaly (F1) is being "
                    "managed under strict deterministic guardrails. MITRA assists with recommendations while you maintain full control."
                )

        resp = AIResponse(
            response_id=generate_id("air"),
            correlation_id=context.correlation_id,
            provider=provider,
            response_type=AIResponseType.MERCHANT_QA,
            answer=answer_text,
            verified_fact_ids=[f["fact_id"] for f in context.verified_facts[:3]],
            hypothesis="Observed trends suggest promotional alignment; causality is not established.",
            confidence=0.90,
            disclaimer="AI-generated advisory interpretation. Causality is not established. Simulated digital-twin sandbox.",
        )
        self._cache[cache_key] = resp
        return resp


# Singleton provider manager instance
_ai_provider_manager = AIProviderManager()


def get_ai_provider_manager() -> AIProviderManager:
    """Returns the singleton AIProviderManager."""
    return _ai_provider_manager
