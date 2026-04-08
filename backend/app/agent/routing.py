"""Heuristics for selecting a lower-latency response path per turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RouteMode = Literal["fast", "guarded", "contextual", "full"]

_CRISIS_CUES = (
    "suicide",
    "kill myself",
    "end my life",
    "self-harm",
    "hurt myself",
    "don't want to live",
    "i want to die",
    "can't go on",
)

_DISTRESS_CUES = (
    "panic",
    "overwhelmed",
    "falling apart",
    "hopeless",
    "worthless",
    "empty",
    "devastated",
    "can't cope",
    "breaking down",
    "spiraling",
)

_CONTEXT_CUES = (
    "birthday",
    "anniversary",
    "journal",
    "last week",
    "last month",
    "again",
    "still",
    "plan",
    "goal",
    "assessment",
    "therapy",
    "trigger",
    "calendar",
    "yesterday",
    "tomorrow",
)

_CASUAL_CUES = (
    "thanks",
    "thank you",
    "okay",
    "ok",
    "got it",
    "cool",
    "hi",
    "hello",
    "hey",
    "good morning",
    "good night",
)


@dataclass(frozen=True)
class TurnRoute:
    mode: RouteMode
    use_historian: bool
    use_retrieval: bool
    use_anchor: bool
    reason: str


def decide_turn_route(
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> TurnRoute:
    """Pick the cheapest route that still covers the user's risk level."""
    history = conversation_history or []
    normalized = " ".join(user_message.lower().split())
    history_depth = len(history)

    has_crisis = any(cue in normalized for cue in _CRISIS_CUES)
    has_distress = has_crisis or any(cue in normalized for cue in _DISTRESS_CUES)
    needs_context = (
        history_depth >= 6
        or len(normalized) >= 220
        or any(cue in normalized for cue in _CONTEXT_CUES)
    )
    is_casual = (
        len(normalized) <= 80
        and any(cue in normalized for cue in _CASUAL_CUES)
        and not has_distress
        and not needs_context
    )

    if has_crisis:
        return TurnRoute(
            mode="full",
            use_historian=needs_context,
            use_retrieval=needs_context,
            use_anchor=True,
            reason="crisis cues require the anchor safety layer",
        )

    if has_distress and needs_context:
        return TurnRoute(
            mode="full",
            use_historian=True,
            use_retrieval=True,
            use_anchor=True,
            reason="distress plus contextual references need full review",
        )

    if needs_context:
        return TurnRoute(
            mode="contextual",
            use_historian=True,
            use_retrieval=True,
            use_anchor=False,
            reason="contextual turn benefits from historian grounding",
        )

    if has_distress:
        return TurnRoute(
            mode="guarded",
            use_historian=False,
            use_retrieval=False,
            use_anchor=True,
            reason="distress without extra context still gets anchor review",
        )

    if is_casual:
        return TurnRoute(
            mode="fast",
            use_historian=False,
            use_retrieval=False,
            use_anchor=False,
            reason="short low-intensity turn can use the fast path",
        )

    return TurnRoute(
        mode="fast",
        use_historian=False,
        use_retrieval=False,
        use_anchor=False,
        reason="defaulting to specialist-only fast path",
    )
