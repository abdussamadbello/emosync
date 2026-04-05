from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.voice import InputTextFinal, VoiceClientEvent, VoiceServerEvent
from app.services.audio.buffer import AudioBuffer
from app.services.realtime.gemini_live import gemini_live_enabled, open_gemini_live_voice_bridge
from app.services.realtime.orchestrator import VoiceOrchestrator
from app.services.stt.elevenlabs_stt import build_stt_service
from app.services.tts.elevenlabs import build_tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


def _extract_bearer_token(websocket: WebSocket) -> str | None:
    auth = websocket.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    token = websocket.query_params.get("token")
    if token:
        return token.strip()
    return None


async def _resolve_token(token: str) -> User | None:
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    async with SessionLocal() as session:
        return await session.get(User, uid)


async def _resolve_socket_user(websocket: WebSocket) -> User | None:
    token = _extract_bearer_token(websocket)
    if not token:
        return None
    return await _resolve_token(token)


async def _load_conversation_history(conversation_id: uuid.UUID) -> list[dict[str, str]]:
    async with SessionLocal() as session:
        history_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]


async def _persist_turn(
    *,
    conversation_id: uuid.UUID,
    transcript: str,
    assistant_text: str,
) -> None:
    transcript = transcript.strip()
    assistant_text = assistant_text.strip()
    if not transcript:
        return

    async with SessionLocal() as session:
        async with session.begin():
            session.add(Message(conversation_id=conversation_id, role="user", content=transcript))
            if assistant_text:
                session.add(Message(conversation_id=conversation_id, role="assistant", content=assistant_text))


def _decode_audio_b64(raw_audio: str) -> bytes:
    try:
        return base64.b64decode(raw_audio)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid audio encoding.") from exc


@router.websocket("/voice/ws/{conversation_id}")
async def voice_ws(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    user = await _resolve_socket_user(websocket)

    if user is None:
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
            if raw.get("type") == "auth" and isinstance(raw.get("data"), dict):
                token = raw["data"].get("token", "")
                user = await _resolve_token(token)
        except (asyncio.TimeoutError, Exception):
            pass
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    else:
        await websocket.accept()

    async with SessionLocal() as session:
        conv = await session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    try:

        if gemini_live_enabled():
            history = await _load_conversation_history(conversation_id)
            await _stream_gemini_live_voice_session(
                websocket=websocket,
                conversation_id=conversation_id,
                conversation_history=history,
            )
            return

        await _stream_legacy_voice_session(websocket=websocket, conversation_id=conversation_id)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Voice stream failed.")
        if websocket.client_state.name == "CONNECTED":
            await websocket.send_json(
                VoiceServerEvent(
                    type="error",
                    data={"code": "voice_stream_failed", "message": "Voice stream failed."},
                ).model_dump()
            )


async def _stream_gemini_live_voice_session(
    *,
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    conversation_history: list[dict[str, str]],
) -> None:
    async with open_gemini_live_voice_bridge(conversation_history=conversation_history) as bridge:
        await websocket.send_json(
            VoiceServerEvent(
                type="session.ready",
                data={
                    "conversation_id": str(conversation_id),
                    "provider": "gemini_live",
                    "model": settings.gemini_live_model,
                    "input_audio_format": "pcm_s16le",
                    "input_sample_rate_hz": settings.gemini_live_input_sample_rate_hz,
                    "output_audio_format": "pcm_s16le",
                    "output_sample_rate_hz": settings.gemini_live_output_sample_rate_hz,
                },
            ).model_dump()
        )

        # If this is a new conversation (no history), have the AI greet first
        if not conversation_history:
            await bridge.send_greeting_prompt()

        forward_task = asyncio.create_task(
            _forward_gemini_live_events(
                websocket=websocket,
                bridge=bridge,
                conversation_id=conversation_id,
            )
        )

        try:
            while True:
                raw = await websocket.receive_json()
                event = VoiceClientEvent.model_validate(raw)

                if event.type == "ping":
                    await websocket.send_json(VoiceServerEvent(type="pong", data={}).model_dump())
                    continue

                if event.type == "turn.cancel":
                    await bridge.end_audio()
                    await websocket.send_json(
                        VoiceServerEvent(type="turn.done", data={"cancelled": True}).model_dump()
                    )
                    continue

                if event.type == "input_audio.clear":
                    continue

                if event.type == "input_audio.append":
                    raw_audio = event.data.get("audio", "")
                    if not raw_audio:
                        continue
                    try:
                        decoded = _decode_audio_b64(raw_audio)
                    except ValueError:
                        await websocket.send_json(
                            VoiceServerEvent(
                                type="error",
                                data={"code": "invalid_audio", "message": "Invalid audio encoding."},
                            ).model_dump()
                        )
                        continue

                    await bridge.send_audio_chunk(
                        decoded,
                        mime_type=event.data.get("mime_type"),
                    )
                    continue

                if event.type == "input_audio.commit":
                    await bridge.end_audio()
                    continue

                if event.type == "input_text.final":
                    payload = InputTextFinal.model_validate(event.data)
                    await bridge.send_text(payload.text)
                    continue

                await websocket.send_json(
                    VoiceServerEvent(
                        type="error",
                        data={"code": "unsupported_event", "message": f"Unsupported event type: {event.type}"},
                    ).model_dump()
                )
        finally:
            forward_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await forward_task


async def _forward_gemini_live_events(
    *,
    websocket: WebSocket,
    bridge,
    conversation_id: uuid.UUID,
) -> None:
    current_transcript = ""
    current_assistant_text = ""

    try:
        async for server_event in bridge.stream_events():
            if server_event.type == "user.transcript":
                current_transcript = str(server_event.data.get("text", "")).strip()
            elif server_event.type == "assistant.text.done":
                current_assistant_text = str(server_event.data.get("text", "")).strip()
            elif server_event.type == "turn.interrupted":
                current_assistant_text = ""
            elif server_event.type == "turn.done":
                await _persist_turn(
                    conversation_id=conversation_id,
                    transcript=current_transcript,
                    assistant_text=current_assistant_text,
                )
                current_transcript = ""
                current_assistant_text = ""

            await websocket.send_json(server_event.model_dump())
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Gemini Live forward loop failed.")
        if websocket.client_state.name == "CONNECTED":
            await websocket.send_json(
                VoiceServerEvent(
                    type="error",
                    data={
                        "code": "voice_provider_failed",
                        "message": "Gemini Live session failed.",
                    },
                ).model_dump()
            )


async def _stream_legacy_voice_session(
    *,
    websocket: WebSocket,
    conversation_id: uuid.UUID,
) -> None:
    await websocket.send_json(
        VoiceServerEvent(
            type="session.ready",
            data={
                "conversation_id": str(conversation_id),
                "provider": "legacy",
            },
        ).model_dump()
    )

    orchestrator = VoiceOrchestrator(tts_service=build_tts_service())
    stt_service = build_stt_service()
    audio_buffer = AudioBuffer(max_bytes=settings.voice_input_buffer_max_bytes)

    while True:
        raw = await websocket.receive_json()
        event = VoiceClientEvent.model_validate(raw)

        if event.type == "ping":
            await websocket.send_json(VoiceServerEvent(type="pong", data={}).model_dump())
            continue

        if event.type == "turn.cancel":
            audio_buffer.reset()
            await websocket.send_json(VoiceServerEvent(type="turn.done", data={"cancelled": True}).model_dump())
            continue

        if event.type == "input_audio.clear":
            audio_buffer.reset()
            continue

        if event.type == "input_audio.append":
            raw_audio = event.data.get("audio", "")
            if raw_audio:
                try:
                    decoded = _decode_audio_b64(raw_audio)
                except ValueError:
                    await websocket.send_json(
                        VoiceServerEvent(
                            type="error",
                            data={"code": "invalid_audio", "message": "Invalid audio encoding."},
                        ).model_dump()
                    )
                    continue
                try:
                    audio_buffer.append(decoded)
                except ValueError:
                    audio_buffer.reset()
                    await websocket.send_json(
                        VoiceServerEvent(
                            type="error",
                            data={
                                "code": "audio_buffer_overflow",
                                "message": "Audio too long. Please try a shorter message.",
                            },
                        ).model_dump()
                    )
            continue

        if event.type == "input_audio.commit":
            audio_bytes = audio_buffer.flush()
            if not audio_bytes:
                await websocket.send_json(
                    VoiceServerEvent(
                        type="error",
                        data={"code": "empty_audio", "message": "No audio to transcribe."},
                    ).model_dump()
                )
                continue
            mime_type = event.data.get("mime_type", "audio/wav")
            transcript = await stt_service.transcribe(audio_bytes, mime_type=mime_type)
            if not transcript.strip():
                await websocket.send_json(
                    VoiceServerEvent(
                        type="error",
                        data={"code": "empty_transcript", "message": "No speech detected."},
                    ).model_dump()
                )
                continue
        elif event.type == "input_text.final":
            payload = InputTextFinal.model_validate(event.data)
            transcript = payload.text
        else:
            await websocket.send_json(
                VoiceServerEvent(
                    type="error",
                    data={"code": "unsupported_event", "message": f"Unsupported event type: {event.type}"},
                ).model_dump()
            )
            continue

        await websocket.send_json(VoiceServerEvent(type="user.transcript", data={"text": transcript}).model_dump())

        history = await _load_conversation_history(conversation_id)

        user_message_id = uuid.uuid4()
        assistant_text = ""
        async for server_event in orchestrator.stream_transcript_turn(
            transcript=transcript,
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            conversation_history=history,
        ):
            if server_event.type == "assistant.text.delta":
                assistant_text += server_event.data.get("text", "")
            await websocket.send_json(server_event.model_dump())

        await _persist_turn(
            conversation_id=conversation_id,
            transcript=transcript,
            assistant_text=assistant_text,
        )
