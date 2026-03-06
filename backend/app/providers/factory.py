from __future__ import annotations

from app.providers.base import ProviderConfig, SummaryProvider
from app.providers.ollama import OllamaProvider


def build_provider(config: ProviderConfig) -> SummaryProvider:
    if config.provider_mode == "ollama":
        return OllamaProvider(config)
    raise ValueError(f"Unsupported provider mode: {config.provider_mode}")

