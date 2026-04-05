"""Journal entry endpoints: CRUD + tag filter."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.journal_entry import JournalEntry
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalOut, JournalUpdate
from app.services.journal_embedding import delete_journal_embedding, embed_journal_entry

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    entry = JournalEntry(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        mood_score=body.mood_score,
        tags=body.tags,
        source=body.source,
        conversation_id=body.conversation_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Auto-embed in background (best-effort, does not block response)
    await embed_journal_entry(db, entry.id, current_user.id, entry.content)
    await db.commit()

    return entry


@router.get("", response_model=list[JournalOut])
async def list_entries(
    tag: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JournalEntry]:
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id)
        .order_by(JournalEntry.created_at.desc())
    )
    if tag:
        # Use raw SQL @> (JSONB containment) to check if the tags array contains the tag.
        # jsonb_build_array builds a proper JSONB literal from the bound parameter value.
        stmt = stmt.where(
            text("journal_entries.tags::jsonb @> jsonb_build_array(:tag)").bindparams(tag=tag)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{entry_id}", response_model=JournalOut)
async def get_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")
    return entry


@router.patch("/{entry_id}", response_model=JournalOut)
async def update_entry(
    entry_id: uuid.UUID,
    body: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    update_data = body.model_dump(exclude_unset=True)
    content_changed = "content" in update_data
    for key, value in update_data.items():
        setattr(entry, key, value)
    await db.commit()
    await db.refresh(entry)

    if content_changed:
        await embed_journal_entry(db, entry.id, current_user.id, entry.content)
        await db.commit()

    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    await delete_journal_embedding(db, entry_id)
    await db.delete(entry)
    await db.commit()
