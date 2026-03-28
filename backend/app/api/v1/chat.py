from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import SessionLocal, get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    MessageOut,
    StreamTurnRequest,
)
from app.services.chat_turn import run_turn

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conv = Conversation(title=body.title, user_id=current_user.id)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageOut]
)
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Message]:
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message_turn(
    conversation_id: uuid.UUID,
    body: StreamTurnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    user_msg = Message(
        conversation_id=conversation_id, role="user", content=body.content
    )
    db.add(user_msg)
    await db.flush()
    user_message_id = str(user_msg.id)
    await db.commit()

    cid_str = str(conversation_id)
    content = body.content

    # Load conversation history for agent context
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_result.scalars().all()
    ]

    async def event_stream() -> AsyncIterator[str]:
        yield _sse(
            "meta", {"conversation_id": cid_str, "user_message_id": user_message_id}
        )
        chunks: list[str] = []
        try:
            async for fragment in run_turn(
                user_message=content,
                conversation_id=cid_str,
                user_message_id=user_message_id,
                conversation_history=history,
            ):
                chunks.append(fragment)
                yield _sse("token", {"text": fragment})
            full = "".join(chunks)
            async with SessionLocal() as session:
                async with session.begin():
                    session.add(
                        Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full,
                        )
                    )
                    await session.execute(
                        update(Conversation)
                        .where(Conversation.id == conversation_id)
                        .values(updated_at=func.now())
                    )
            yield _sse("done", {"assistant_text": full})
        except Exception:
            logger.exception("Assistant stream failed")
            yield _sse(
                "error", {"code": "stream_failed", "message": "Assistant stream failed"}
            )
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
