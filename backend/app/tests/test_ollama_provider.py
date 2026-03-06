import httpx
import pytest

from app.providers.base import ProviderConfig
from app.providers.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_connection_and_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"response": "Summary output"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    provider = OllamaProvider(
        ProviderConfig(provider_mode="ollama", ollama_base_url="http://testserver", ollama_model="llama3.1"),
        client=client,
    )

    ok, message = await provider.test_connection()
    summary = await provider.summarize_chunk("prompt")

    assert ok is True
    assert "Connected to Ollama" in message
    assert summary == "Summary output"

