import json
import pytest
from app.llm.client import FallbackClient, GeminiClient, get_llm_client


@pytest.mark.asyncio
async def test_fallback_client_execution():
    """FallbackClient must return valid structured response without any API key."""
    client = FallbackClient()
    assert client.is_available is True
    assert "Fallback" in client.provider_name

    response = await client.generate(prompt="Analyze merchant transaction dip")
    assert isinstance(response, str)
    data = json.loads(response)
    assert data["mode"] == "deterministic_fallback"
    assert data["status"] == "success"
    assert "confidence" in data


def test_factory_returns_fallback_when_unconfigured():
    """Factory must return FallbackClient safely when no API key is provided."""
    client = get_llm_client(force_fallback=True)
    assert isinstance(client, FallbackClient)


def test_gemini_client_availability_check():
    """GeminiClient must accurately reflect availability based on API key presence."""
    client_empty = GeminiClient(api_key="")
    assert client_empty.is_available is False

    client_valid = GeminiClient(api_key="fake-api-key")
    assert client_valid.is_available is True
