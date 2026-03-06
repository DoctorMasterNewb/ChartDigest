from __future__ import annotations

import httpx

from app.providers.base import ProviderConfig


class OllamaProvider:
    name = "ollama"

    def __init__(self, config: ProviderConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        # Local models on CPU/limited VRAM can take >60s for long prompts; use a safer default timeout.
        self.client = client or httpx.AsyncClient(base_url=config.ollama_base_url.rstrip("/"), timeout=300.0)

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - exercised in tests with mocks
            return False, f"Unable to reach Ollama: {exc}"
        return True, f"Connected to Ollama at {self.config.ollama_base_url}"

    async def summarize_chunk(self, prompt: str) -> str:
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
        except httpx.ReadTimeout as exc:
            raise ValueError(
                f"Ollama timed out while generating with model '{self.config.ollama_model}'. "
                "This is usually local inference latency (not API outage). Consider a smaller model or longer timeout."
            ) from exc
        if response.status_code >= 400:
            detail = ""
            try:
                detail = response.text
            except Exception:
                detail = ""
            raise ValueError(
                f"Ollama generation failed ({response.status_code}) for model '{self.config.ollama_model}'. {detail}".strip()
            )

        payload = response.json()
        text = payload.get("response", "").strip()
        if not text:
            raise ValueError("Ollama returned an empty response")
        return text

