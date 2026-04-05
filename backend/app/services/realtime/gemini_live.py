from __future__ import annotations

import base64
import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

import websockets

from app.agent.prompts import SPECIALIST_SYSTEM
from app.core.config import settings
from app.schemas.voice import VoiceServerEvent

logger = logging.getLogger(__name__)

_MIME_RATE_RE = re.compile(r"rate=(\d+)")
_TRAILING_PROSODY_FRAGMENT_RE = re.compile(r"\s*\[[^\]]{0,100}\]?\s*$")


def gemini_live_enabled() -> bool:
    return (
        settings.voice_provider == "gemini_live"
        and bool(settings.gemini_api_key)
    )

def parse_pcm_rate(mime_type: str | None, *, default: int) -> int:
    if not mime_type:
        return default
    match = _MIME_RATE_RE.search(mime_type)
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def _build_live_system_instruction() -> str:
    specialist = " ".join(line.strip() for line in SPECIALIST_SYSTEM.splitlines() if line.strip())
    return (
        "You are EmoSync's voice therapist-style companion for grief and heartbreak support. "
        "Speak naturally for audio and keep responses concise, emotionally paced, and warm. "
        "Validation must come before reframing. Avoid diagnosis, medication advice, victim-blaming, "
        "toxic positivity, minimising language, and fabricated context. "
        "If the user expresses suicidal ideation, self-harm, or immediate danger, state clearly that "
        "you are not a substitute for professional help and offer 988 Suicide & Crisis Lifeline and "
        "Crisis Text Line (text HOME to 741741). "
        "Never output square-bracket stage directions, prosody hints, tone labels, or any meta-instructions. "
        "Do not say things like 'gentle, warm tone' aloud. "
        "Use the following product behavior as policy. "
        f"{specialist} "
        "Apply the Anchor safety policy internally: validate first, match emotional pacing, avoid harmful language, "
        "and do not hallucinate context. "
        "Do not mention internal roles, hidden prompts, or prosody tags."
    )


def _sanitize_output_text(text: str) -> str:
    sanitized = text
    if "[" in sanitized:
        last_open = sanitized.rfind("[")
        if last_open != -1 and len(sanitized) - last_open <= 120:
            fragment = sanitized[last_open:]
            if any(
                token in fragment.lower()
                for token in ("tone", "pace", "slow", "warm", "gentle", "measured", "speak")
            ):
                sanitized = sanitized[:last_open].rstrip()
    sanitized = _TRAILING_PROSODY_FRAGMENT_RE.sub("", sanitized)
    return sanitized


class GeminiLiveVoiceBridge:
    def __init__(self, *, conversation_history: list[dict[str, str]]) -> None:
        self._conversation_history = conversation_history
        self._ws: websockets.client.WebSocketClientProtocol | None = None
        self._input_transcript = ""
        self._output_transcript = ""
        self._output_chunk_count = 0
        self._closed = False

    async def connect(self) -> None:
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={settings.gemini_api_key}"
        self._ws = await websockets.connect(url)
        
        setup_payload = {
            "setup": {
                "model": f"models/{settings.gemini_live_model}",
                "systemInstruction": {
                    "parts": [{"text": _build_live_system_instruction()}]
                },
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "temperature": settings.gemini_live_temperature
                },
                "inputAudioTranscription": {},
                "outputAudioTranscription": {},
                "realtimeInputConfig": {
                    "automaticActivityDetection": {
                        "disabled": False,
                        "prefixPaddingMs": settings.gemini_live_prefix_padding_ms,
                        "silenceDurationMs": settings.gemini_live_silence_duration_ms,
                    }
                }
            }
        }
        await self._ws.send(json.dumps(setup_payload))
        await self._prime_conversation_history()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._ws:
            await self._ws.close()
        self._ws = None

    async def send_audio_chunk(self, audio_bytes: bytes, *, mime_type: str | None = None) -> None:
        if not self._ws:
            raise RuntimeError("Gemini Live session not connected.")
        rate = parse_pcm_rate(mime_type, default=settings.gemini_live_input_sample_rate_hz)
        payload = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": f"audio/pcm;rate={rate}",
                        "data": base64.b64encode(audio_bytes).decode("ascii")
                    }
                ]
            }
        }
        await self._ws.send(json.dumps(payload))

    async def end_audio(self) -> None:
        if not self._ws:
            raise RuntimeError("Gemini Live session not connected.")
        payload = {
            "realtimeInput": {
                "audioStreamEnd": True
            }
        }
        await self._ws.send(json.dumps(payload))

    async def send_text(self, text: str) -> None:
        if not self._ws:
            raise RuntimeError("Gemini Live session not connected.")
        payload = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": text}]
                    }
                ],
                "turnComplete": True
            }
        }
        await self._ws.send(json.dumps(payload))

    async def stream_events(self) -> AsyncIterator[VoiceServerEvent]:
        if not self._ws:
            raise RuntimeError("Gemini Live session not connected.")
        
        async for message_str in self._ws:
            try:
                message = json.loads(message_str)
            except Exception:
                logger.exception("Failed to parse incoming message")
                continue

            async for event in self._message_to_events(message):
                yield event

    async def _prime_conversation_history(self) -> None:
        if not self._ws:
            return

        turns = []
        try:
            for item in self._conversation_history:
                role = _map_history_role(item.get("role"))
                text = (item.get("content") or "").strip()
                if not role or not text:
                    continue
                turns.append({
                    "role": role,
                    "parts": [{"text": text}]
                })

            if turns:
                payload = {
                    "clientContent": {
                        "turns": turns,
                        "turnComplete": False
                    }
                }
                await self._ws.send(json.dumps(payload))
        except Exception:
            logger.exception("Failed to prime Gemini Live session with conversation history.")

    async def send_greeting_prompt(self) -> None:
        """Send a text prompt that triggers the AI to greet the user first.

        Called after connect() for new conversations so the AI speaks
        before the user does, like a therapist opening a session.
        """
        if not self._ws:
            return
        payload = {
            "clientContent": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [{"text": (
                            "The user just joined the session. "
                            "Greet them warmly and briefly — one or two sentences. "
                            "Ask how they're doing today. Keep it natural and gentle."
                        )}],
                    }
                ],
                "turnComplete": True,
            }
        }
        await self._ws.send(json.dumps(payload))

    async def _message_to_events(self, message: dict[str, Any]) -> AsyncIterator[VoiceServerEvent]:
        if message.get("goAway"):
            yield VoiceServerEvent(
                type="error",
                data={
                    "code": "voice_provider_closed",
                    "message": "Gemini Live closed the session.",
                },
            )
            return

        server_content = message.get("serverContent")
        if not server_content:
            return

        input_transcription = server_content.get("inputTranscription")
        if input_transcription and input_transcription.get("text") is not None:
            fragment = input_transcription["text"].strip()
            if fragment:
                # Accumulate fragments into full transcript (Gemini may send
                # incremental pieces rather than the full text each time)
                if fragment.startswith(self._input_transcript):
                    # Gemini sent cumulative text — use as-is
                    self._input_transcript = fragment
                else:
                    # Gemini sent a new fragment — append to what we have
                    self._input_transcript = (
                        (self._input_transcript + " " + fragment).strip()
                    )
                yield VoiceServerEvent(
                    type="user.transcript",
                    data={"text": self._input_transcript},
                )

        output_transcription = server_content.get("outputTranscription")
        if output_transcription and output_transcription.get("text") is not None:
            text = _sanitize_output_text(output_transcription["text"])
            if text != self._output_transcript:
                delta = text[len(self._output_transcript) :] if text.startswith(self._output_transcript) else text
                self._output_transcript = text
                if delta:
                    yield VoiceServerEvent(type="assistant.text.delta", data={"text": delta})

        model_turn = server_content.get("modelTurn")
        if model_turn:
            parts = model_turn.get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData")
                if inline_data and inline_data.get("data"):
                    chunk_b64 = inline_data["data"]
                    mime = inline_data.get("mimeType", "audio/pcm;rate=24000")
                    rate = parse_pcm_rate(mime, default=settings.gemini_live_output_sample_rate_hz)
                    self._output_chunk_count += 1
                    yield VoiceServerEvent(
                        type="output_audio.chunk",
                        data={
                            "audio_b64": chunk_b64,
                            "mime_type": mime,
                            "sample_rate_hz": rate,
                        },
                    )

        if server_content.get("interrupted"):
            yield VoiceServerEvent(type="turn.interrupted", data={})
            self._reset_turn_state()
            return

        if server_content.get("turnComplete"):
            if self._output_transcript:
                yield VoiceServerEvent(
                    type="assistant.text.done",
                    data={"text": self._output_transcript},
                )
            yield VoiceServerEvent(
                type="output_audio.done",
                data={"chunks": self._output_chunk_count},
            )
            yield VoiceServerEvent(
                type="turn.done",
                data={"assistant_text": self._output_transcript},
            )
            self._reset_turn_state()

    def _reset_turn_state(self) -> None:
        self._input_transcript = ""
        self._output_transcript = ""
        self._output_chunk_count = 0


def _map_history_role(role: str | None) -> str | None:
    if role == "user":
        return "user"
    if role == "assistant":
        return "model"
    return None

@contextlib.asynccontextmanager
async def open_gemini_live_voice_bridge(
    *,
    conversation_history: list[dict[str, str]],
) -> AsyncIterator[GeminiLiveVoiceBridge]:
    bridge = GeminiLiveVoiceBridge(conversation_history=conversation_history)
    await bridge.connect()
    try:
        yield bridge
    finally:
        await bridge.close()
