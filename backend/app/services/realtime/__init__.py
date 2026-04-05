from __future__ import annotations

from typing import Any

__all__ = ["GeminiLiveVoiceBridge", "VoiceOrchestrator", "VoiceSession", "gemini_live_enabled"]


def __getattr__(name: str) -> Any:
    if name in {"GeminiLiveVoiceBridge", "gemini_live_enabled"}:
        from app.services.realtime.gemini_live import GeminiLiveVoiceBridge, gemini_live_enabled

        return {
            "GeminiLiveVoiceBridge": GeminiLiveVoiceBridge,
            "gemini_live_enabled": gemini_live_enabled,
        }[name]
    if name == "VoiceOrchestrator":
        from app.services.realtime.orchestrator import VoiceOrchestrator

        return VoiceOrchestrator
    if name == "VoiceSession":
        from app.services.realtime.session import VoiceSession

        return VoiceSession
    raise AttributeError(name)
