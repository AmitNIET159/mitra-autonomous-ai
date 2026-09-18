from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for MITRA."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "MITRA"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Gemini LLM Configuration (Flash 3.8 High)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ENABLE_LLM: bool = True

    # Hugging Face AI Configuration (Optional Fallback)
    HF_API_KEY: Optional[str] = None
    HF_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"

    # AI Provider Preference: 'auto' | 'gemini' | 'huggingface' | 'fallback'
    AI_PROVIDER_PREFERENCE: str = "auto"

    # Deterministic Guardrail Defaults
    MAX_CAMPAIGN_BUDGET_INR: float = 5000.0
    MAX_DISCOUNT_PERCENT: float = 25.0
    MAX_DAILY_ACTIONS: int = 5

    # Simulation / Digital-Twin Principle
    # Must always be true for the hackathon prototype
    SIMULATION_MODE: bool = True

    @property
    def is_gemini_active(self) -> bool:
        """Determines if live Gemini integration is configured and enabled."""
        return bool(self.ENABLE_LLM and self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    @property
    def is_hf_active(self) -> bool:
        """Determines if live Hugging Face integration is configured and enabled."""
        return bool(self.ENABLE_LLM and self.HF_API_KEY and self.HF_API_KEY.strip())

    @property
    def is_llm_active(self) -> bool:
        """Determines if any live LLM integration (Gemini or Hugging Face) should be engaged."""
        return self.is_gemini_active or self.is_hf_active


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
