"""Shared helpers for keeping agent context within a sane token budget."""

from __future__ import annotations

from collections.abc import Iterable

MAX_HISTORY_MESSAGES = 10
MAX_PROMPT_HISTORY_MESSAGES = 6
MAX_HISTORY_MESSAGE_CHARS = 280
MAX_USER_MESSAGE_CHARS = 1_200
MAX_CONTEXT_ITEMS = 3
MAX_CONTEXT_ITEM_CHARS = 240


def truncate_text(text: str, max_chars: int) -> str:
    """Trim long text blocks without breaking the prompt structure."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def trim_conversation_history(
    history: list[dict[str, str]] | None,
    *,
    max_messages: int = MAX_HISTORY_MESSAGES,
    max_chars_per_message: int = MAX_HISTORY_MESSAGE_CHARS,
) -> list[dict[str, str]]:
    """Keep only the most recent messages and clip oversized content."""
    trimmed: list[dict[str, str]] = []
    for item in (history or [])[-max_messages:]:
        role = str(item.get("role", "")).strip() or "user"
        content = truncate_text(str(item.get("content", "")), max_chars_per_message)
        if content:
            trimmed.append({"role": role, "content": content})
    return trimmed


def trim_string_list(
    items: Iterable[str] | None,
    *,
    max_items: int = MAX_CONTEXT_ITEMS,
    max_chars: int = MAX_CONTEXT_ITEM_CHARS,
) -> list[str]:
    """Clip noisy context sections such as journal snippets or calendar events."""
    trimmed: list[str] = []
    for item in list(items or [])[:max_items]:
        text = truncate_text(str(item), max_chars)
        if text:
            trimmed.append(text)
    return trimmed
