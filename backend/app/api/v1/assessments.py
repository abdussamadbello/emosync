"""Assessment endpoints: submit, list, get latest."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import AssessmentCreate, AssessmentOut
from app.services.scoring import score_assessment

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
async def submit_assessment(
    body: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Assessment:
    try:
        total_score, severity = score_assessment(body.instrument, body.responses)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    assessment = Assessment(
        user_id=current_user.id,
        instrument=body.instrument,
        responses=body.responses,
        total_score=total_score,
        severity=severity,
        source=body.source,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.get("", response_model=list[AssessmentOut])
async def list_assessments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Assessment]:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.user_id == current_user.id)
        .order_by(Assessment.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/latest", response_model=AssessmentOut)
async def get_latest_assessment(
    instrument: str = Query(..., pattern=r"^(phq9|gad7)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Assessment:
    result = await db.execute(
        select(Assessment)
        .where(Assessment.user_id == current_user.id, Assessment.instrument == instrument)
        .order_by(Assessment.created_at.desc())
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {instrument} assessment found.",
        )
    return assessment
