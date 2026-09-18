from abc import ABC, abstractmethod
import json
from typing import Any, Dict, Optional
import httpx

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class LLMClient(ABC):
    """Abstract interface for LLM operations in MITRA.
    
    Any underlying provider (Gemini, Fallback, etc.) implements this contract.
    Business logic and deterministic layers MUST depend strictly on this abstraction.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identification name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates whether this client is fully operational."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generates text response for the given prompt and system instructions."""
        pass


class GeminiClient(LLMClient):
    """Client for Google Gemini (Flash 3.8 High / gemini-2.5-flash) via official REST endpoint."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 30.0):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        )

    @property
    def provider_name(self) -> str:
        return f"Gemini ({self._model})"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not self.is_available:
            raise RuntimeError("Gemini API key is not configured.")

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        try:
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini response structure: %s", data)
            raise RuntimeError(f"Failed to parse Gemini response: {exc}") from exc


class FallbackClient(LLMClient):
    """Deterministic, local fallback client.
    
    Ensures MITRA never crashes when offline or when no Gemini API key is configured.
    Produces safe, structured merchant interpretations for prototypes and testing.
    """

    @property
    def provider_name(self) -> str:
        return "Deterministic Fallback Client (Offline Safe)"

    @property
    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        logger.info("Executing via FallbackClient (Deterministic Simulation Mode)")
        
        # Return deterministic structured response format
        return json.dumps({
            "mode": "deterministic_fallback",
            "status": "success",
            "interpretation": "Merchant signal evaluated using deterministic fallback rules.",
            "confidence": 0.85,
            "projected_impact": {
                "estimated_conversion_lift_pct": 14.5,
                "risk_assessment": "low",
            }
        })


class HuggingFaceClient(LLMClient):
    """Client for Hugging Face Inference API.
    
    Provides optional secondary AI fallback when configured via HF_API_KEY.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/Llama-3.2-3B-Instruct",
        timeout: float = 30.0,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._endpoint = f"https://api-inference.huggingface.co/models/{self._model}"

    @property
    def provider_name(self) -> str:
        return f"Hugging Face ({self._model})"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not self.is_available:
            raise RuntimeError("Hugging Face API key is not configured.")

        combined_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

        payload: Dict[str, Any] = {
            "inputs": combined_prompt,
            "parameters": {
                "max_new_tokens": 512,
                "temperature": max(0.01, min(temperature, 1.0)),
                "return_full_text": False,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "generated_text" in data[0]:
            return str(data[0]["generated_text"]).strip()
        elif isinstance(data, dict) and "generated_text" in data:
            return str(data["generated_text"]).strip()
        elif isinstance(data, str):
            return data.strip()
        else:
            return str(data)


def get_llm_client(
    force_fallback: bool = False,
    preferred_provider: Optional[str] = None,
) -> LLMClient:
    """Factory function providing the appropriate LLMClient instance based on configuration and preference."""
    app_settings = get_settings()
    pref = (preferred_provider or app_settings.AI_PROVIDER_PREFERENCE).lower()

    if force_fallback or pref == "fallback":
        return FallbackClient()

    if pref == "gemini":
        if app_settings.is_gemini_active:
            return GeminiClient(
                api_key=app_settings.GEMINI_API_KEY,  # type: ignore[arg-type]
                model=app_settings.GEMINI_MODEL,
            )
        logger.info("Gemini preferred but unconfigured. Falling back.")
        if app_settings.is_hf_active:
            return HuggingFaceClient(
                api_key=app_settings.HF_API_KEY,  # type: ignore[arg-type]
                model=app_settings.HF_MODEL,
            )
        return FallbackClient()

    if pref == "huggingface":
        if app_settings.is_hf_active:
            return HuggingFaceClient(
                api_key=app_settings.HF_API_KEY,  # type: ignore[arg-type]
                model=app_settings.HF_MODEL,
            )
        logger.info("Hugging Face preferred but unconfigured. Falling back.")
        if app_settings.is_gemini_active:
            return GeminiClient(
                api_key=app_settings.GEMINI_API_KEY,  # type: ignore[arg-type]
                model=app_settings.GEMINI_MODEL,
            )
        return FallbackClient()

    # Auto preference: Gemini -> Hugging Face -> Deterministic Fallback
    if app_settings.is_gemini_active:
        return GeminiClient(
            api_key=app_settings.GEMINI_API_KEY,  # type: ignore[arg-type]
            model=app_settings.GEMINI_MODEL,
        )
    elif app_settings.is_hf_active:
        return HuggingFaceClient(
            api_key=app_settings.HF_API_KEY,  # type: ignore[arg-type]
            model=app_settings.HF_MODEL,
        )

    return FallbackClient()

