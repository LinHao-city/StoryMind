"""Bounded retry decision for character-film takes."""

from __future__ import annotations

from typing import Literal


FailureKind = Literal["policy", "technical", "quality", "privacy", "budget"]


def next_take_action(
    kind: FailureKind, *, attempts: int, max_attempts: int = 3,
    estimated_next_usd: float = 0, remaining_usd: float = 0,
) -> str:
    """Return retry, human_review, or block without changing provider."""
    if kind in {"policy", "privacy"}:
        return "human_review"
    if kind == "budget" or estimated_next_usd > remaining_usd:
        return "block"
    if attempts >= max_attempts:
        return "human_review"
    if kind in {"technical", "quality"}:
        return "retry"
    raise ValueError(f"Unknown failure kind: {kind}")
