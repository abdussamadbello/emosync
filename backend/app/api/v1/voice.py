from __future__ import annotations

import base64
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
from app.services.realtime.orchestrator import VoiceOrchestrator
from app.services.stt.elevenlabs_stt import build_stt_service
from app.services.tts.elevenlabs import build_tts_service

router = APIRouter(tags=["voice"])


def _extract_bearer_token(websocket: WebSocket) -> str | None:
    auth = websocket.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    token = websocket.query_params.get("token")
    if token:
        return token.strip()
    return None


async def _resolve_socket_user(websocket: WebSocket) -> User | None:
    token = _extract_bearer_token(websocket)
    if not token:
        return None

    user_id = decode_access_token(token)
    if user_id is None:
        return None

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None

    async with SessionLocal() as session:
        return await session.get(User, uid)


@router.websocket("/voice/ws/{conversation_id}")
async def voice_ws(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    user = await _resolve_socket_user(websocket)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with SessionLocal() as session:
        conv = await session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    await websocket.send_json(VoiceServerEvent(type="session.ready", data={"conversation_id": str(conversation_id)}).model_dump())

    orchestrator = VoiceOrchestrator(tts_service=build_tts_service())
    stt_service = build_stt_service()
    audio_buffer = AudioBuffer(max_bytes=settings.voice_input_buffer_max_bytes)

    try:
        while True:
            raw = await websocket.receive_json()
            event = VoiceClientEvent.model_validate(raw)

            if event.type == "ping":
                await websocket.send_json(VoiceServerEvent(type="pong", data={}).model_dump())
                continue

            if event.type == "turn.cancel":
                await websocket.send_json(VoiceServerEvent(type="turn.done", data={"cancelled": True}).model_dump())
                continue

            if event.type == "input_audio.append":
                raw_audio = event.data.get("audio", "")
                if raw_audio:
                    audio_buffer.append(base64.b64decode(raw_audio))
                continue

            if event.type == "input_audio.commit":
                audio_bytes = audio_buffer.flush()
                if not audio_bytes:
                    await websocket.send_json(
                        VoiceServerEvent(type="error", data={"code": "empty_audio", "message": "No audio to transcribe."}).model_dump()
                    )
                    continue
                mime_type = event.data.get("mime_type", "audio/wav")
                transcript = await stt_service.transcribe(audio_bytes, mime_type=mime_type)
                if not transcript.strip():
                    await websocket.send_json(
                        VoiceServerEvent(type="error", data={"code": "empty_transcript", "message": "No speech detected."}).model_dump()
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

            async with SessionLocal() as session:
                user_message = Message(conversation_id=conversation_id, role="user", content=transcript)
                session.add(user_message)
                await session.flush()

                history_result = await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at.asc())
                )
                history = [{"role": m.role, "content": m.content} for m in history_result.scalars().all()]
                await session.commit()

            assistant_text = ""
            async for server_event in orchestrator.stream_transcript_turn(
                transcript=transcript,
                conversation_id=conversation_id,
                user_message_id=user_message.id,
                conversation_history=history,
            ):
                if server_event.type == "assistant.text.delta":
                    assistant_text += server_event.data.get("text", "")
                await websocket.send_json(server_event.model_dump())

            if assistant_text:
                async with SessionLocal() as session:
                    session.add(
                        Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=assistant_text,
                        )
                    )
                    await session.commit()

    except WebSocketDisconnect:
        return
    except Exception:
        if websocket.client_state.name == "CONNECTED":
            await websocket.send_json(
                VoiceServerEvent(
                    type="error",
                    data={"code": "voice_stream_failed", "message": "Voice stream failed."},
                ).model_dump()
            )
