"""Treatment plan and goal CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.treatment_plan import TreatmentGoal, TreatmentPlan
from app.models.user import User
from app.schemas.treatment import GoalCreate, GoalOut, GoalUpdate, PlanCreate, PlanOut, PlanUpdate

router = APIRouter(tags=["plans"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_plan_for_user(
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    load_goals: bool = False,
) -> TreatmentPlan:
    stmt = select(TreatmentPlan).where(
        TreatmentPlan.id == plan_id,
        TreatmentPlan.user_id == user_id,
    )
    if load_goals:
        stmt = stmt.options(selectinload(TreatmentPlan.goals))
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment plan not found.")
    return plan


# ---------------------------------------------------------------------------
# Plan endpoints
# ---------------------------------------------------------------------------


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    plan = TreatmentPlan(user_id=current_user.id, title=body.title)
    db.add(plan)
    await db.commit()
    # Reload with goals (empty list) to satisfy response_model
    await db.refresh(plan)
    stmt = (
        select(TreatmentPlan)
        .where(TreatmentPlan.id == plan.id)
        .options(selectinload(TreatmentPlan.goals))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TreatmentPlan]:
    stmt = (
        select(TreatmentPlan)
        .where(TreatmentPlan.user_id == current_user.id)
        .options(selectinload(TreatmentPlan.goals))
        .order_by(TreatmentPlan.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    return await _get_plan_for_user(plan_id, current_user.id, db, load_goals=True)


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    body: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlan:
    plan = await _get_plan_for_user(plan_id, current_user.id, db, load_goals=True)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    # Re-fetch with goals to ensure relationship is loaded after refresh
    stmt = (
        select(TreatmentPlan)
        .where(TreatmentPlan.id == plan.id)
        .options(selectinload(TreatmentPlan.goals))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Goal endpoints
# ---------------------------------------------------------------------------


@router.post("/plans/{plan_id}/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def add_goal(
    plan_id: uuid.UUID,
    body: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentGoal:
    # Verify the plan belongs to the user
    await _get_plan_for_user(plan_id, current_user.id, db)
    goal = TreatmentGoal(
        plan_id=plan_id,
        description=body.description,
        target_date=body.target_date,
        status=body.status,
        progress_notes=[],
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    body: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TreatmentGoal:
    # JOIN through TreatmentPlan to verify user ownership
    stmt = (
        select(TreatmentGoal)
        .join(TreatmentPlan, TreatmentGoal.plan_id == TreatmentPlan.id)
        .where(
            TreatmentGoal.id == goal_id,
            TreatmentPlan.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    update_data = body.model_dump(exclude_unset=True)
    progress_note = update_data.pop("progress_note", None)

    for key, value in update_data.items():
        setattr(goal, key, value)

    if progress_note is not None:
        current_notes = list(goal.progress_notes or [])
        current_notes.append({"date": str(date.today()), "note": progress_note})
        goal.progress_notes = current_notes

    await db.commit()
    await db.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    # JOIN through TreatmentPlan to verify user ownership
    stmt = (
        select(TreatmentGoal)
        .join(TreatmentPlan, TreatmentGoal.plan_id == TreatmentPlan.id)
        .where(
            TreatmentGoal.id == goal_id,
            TreatmentPlan.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    await db.delete(goal)
    await db.commit()
