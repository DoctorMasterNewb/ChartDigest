from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ProviderConfig:
    provider_mode: str
    ollama_base_url: str
    ollama_model: str


class SummaryProvider(Protocol):
    name: str

    async def test_connection(self) -> tuple[bool, str]:
        ...

    async def summarize_chunk(self, prompt: str) -> str:
        ...

