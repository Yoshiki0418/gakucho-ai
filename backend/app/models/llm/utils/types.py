from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenerationResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
