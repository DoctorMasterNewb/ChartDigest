from __future__ import annotations

import re
from dataclasses import dataclass


DATE_PATTERN = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},\s+\d{4})\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class TextChunk:
    index: int
    total: int
    content: str
    anchor_hint: str | None


def split_into_chunks(text: str, target_chars: int = 2200, overlap_chars: int = 250) -> list[TextChunk]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    last_overlap = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > target_chars:
            chunks.append(current)
            tail = current[-overlap_chars:].strip()
            last_overlap = f"{tail}\n\n" if tail else ""
            current = f"{last_overlap}{paragraph}".strip()
            continue
        current = candidate

    if current:
        chunks.append(current)

    total = len(chunks)
    return [
        TextChunk(
            index=index,
            total=total,
            content=chunk,
            anchor_hint=_extract_anchor_hint(chunk),
        )
        for index, chunk in enumerate(chunks)
    ]


def _extract_anchor_hint(chunk: str) -> str | None:
    match = DATE_PATTERN.search(chunk)
    if match:
        return match.group(0)
    first_line = chunk.splitlines()[0].strip()
    return first_line[:80] if first_line else None

