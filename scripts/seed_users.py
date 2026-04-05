"""Seed the database with demo users and therapeutic data.

Usage (from repo root, with DATABASE_URL set and migrations applied):

    python -m scripts.seed_users

Credentials:
    alice@example.com   / password123
    bob@example.com     / password123
    carol@example.com   / password123

Alice gets full therapeutic data (profile, journal, calendar, assessments,
treatment plan, mood logs). Bob and Carol get just profiles.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure backend/ is importable when run from repo root
sys.path.insert(0, "backend")

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.assessment import Assessment  # noqa: E402
from app.models.calendar_event import CalendarEvent  # noqa: E402
from app.models.journal_entry import JournalEntry  # noqa: E402
from app.models.mood_log import MoodLog  # noqa: E402
from app.models.treatment_plan import TreatmentGoal, TreatmentPlan  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_profile import UserProfile  # noqa: E402

SEED_USERS = [
    {
        "email": "alice@example.com",
        "password": "password123",
        "display_name": "Alice",
    },
    {
        "email": "bob@example.com",
        "password": "password123",
        "display_name": "Bob",
    },
    {
        "email": "carol@example.com",
        "password": "password123",
        "display_name": "Carol",
    },
]


async def _ensure_user(session: AsyncSession, entry: dict) -> User:
    result = await session.execute(
        select(User).where(User.email == entry["email"])
    )
    user = result.scalar_one_or_none()
    if user is not None:
        print(f"  skip user {entry['email']} (already exists)")
        return user

    user = User(
        email=entry["email"],
        password_hash=hash_password(entry["password"]),
        display_name=entry["display_name"],
    )
    session.add(user)
    await session.flush()
    print(f"  created user {entry['email']}")
    return user


async def _ensure_profile(session: AsyncSession, user: User, **kwargs) -> None:
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    if result.scalar_one_or_none() is not None:
        print(f"  skip profile for {user.email} (already exists)")
        return

    profile = UserProfile(user_id=user.id, **kwargs)
    session.add(profile)
    print(f"  created profile for {user.email}")


async def _seed_alice_data(session: AsyncSession, alice: User) -> None:
    """Seed Alice with full therapeutic data for demo purposes."""

    # --- Profile ---
    await _ensure_profile(
        session,
        alice,
        grief_type="loss",
        grief_subject="my mother",
        grief_duration_months=8,
        support_system="some",
        prior_therapy=True,
        preferred_approaches=["cbt", "journaling", "mindfulness"],
        onboarding_completed=True,
    )

    # --- Check if data already seeded (use journal as indicator) ---
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.user_id == alice.id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        print(f"  skip therapeutic data for {alice.email} (already seeded)")
        return

    today = date.today()

    # --- Journal entries ---
    journals = [
        {
            "title": "First day here",
            "content": (
                "I decided to try this app today. It's been 8 months since mom passed "
                "and I still feel lost some days. My therapist suggested journaling might "
                "help me process things between sessions. I'm not sure what to write, "
                "but I guess starting is the hardest part."
            ),
            "mood_score": 4,
            "tags": ["grief", "reflection"],
            "source": "manual",
            "created_at": datetime.now(timezone.utc) - timedelta(days=14),
        },
        {
            "title": "A good memory",
            "content": (
                "I found an old photo of mom and me at the beach. For the first time, "
                "I smiled instead of cried. I remembered how she always brought too much "
                "food for picnics and insisted everyone eat seconds. I think she'd want "
                "me to remember the happy times."
            ),
            "mood_score": 6,
            "tags": ["gratitude", "progress"],
            "source": "manual",
            "created_at": datetime.now(timezone.utc) - timedelta(days=10),
        },
        {
            "title": "Hard day",
            "content": (
                "Saw someone who looked like mom at the grocery store. Had to leave "
                "my cart and go sit in the car for 20 minutes. The waves of grief still "
                "come without warning. I know this is normal but it still catches me "
                "off guard every time."
            ),
            "mood_score": 3,
            "tags": ["grief", "trigger"],
            "source": "manual",
            "created_at": datetime.now(timezone.utc) - timedelta(days=7),
        },
        {
            "title": "Therapy insight",
            "content": (
                "My therapist pointed out that I tend to catastrophize — when one thing "
                "goes wrong, I think everything is falling apart. She called it a cognitive "
                "distortion. I noticed it happening today when I burned dinner and caught "
                "myself thinking 'I can't do anything right without mom.' But that's not "
                "true — I've been managing a lot on my own."
            ),
            "mood_score": 5,
            "tags": ["therapy", "progress", "reflection"],
            "source": "manual",
            "created_at": datetime.now(timezone.utc) - timedelta(days=3),
        },
        {
            "title": "Small win",
            "content": (
                "Made mom's recipe for lemon cake today. It came out almost right — "
                "a little less sweet than hers, but close. Shared it with the neighbors. "
                "It felt good to do something she loved."
            ),
            "mood_score": 7,
            "tags": ["gratitude", "progress"],
            "source": "manual",
            "created_at": datetime.now(timezone.utc) - timedelta(days=1),
        },
    ]

    for j in journals:
        created_at = j.pop("created_at")
        entry = JournalEntry(user_id=alice.id, **j)
        entry.created_at = created_at
        session.add(entry)
    print(f"  created {len(journals)} journal entries for {alice.email}")

    # --- Calendar events ---
    events = [
        {
            "title": "Mom's birthday",
            "date": today + timedelta(days=12),
            "event_type": "anniversary",
            "recurrence": "yearly",
            "notes": "She would have been 67. Plan something to honor her memory.",
            "notify_agent": True,
        },
        {
            "title": "Therapy session",
            "date": today + timedelta(days=2),
            "event_type": "therapy",
            "notes": "Biweekly session with Dr. Chen",
            "notify_agent": True,
        },
        {
            "title": "Grief support group",
            "date": today + timedelta(days=5),
            "event_type": "therapy",
            "notes": "Community center, 7pm",
            "notify_agent": True,
        },
        {
            "title": "Anniversary of mom's passing",
            "date": today + timedelta(days=25),
            "event_type": "trigger",
            "recurrence": "yearly",
            "notes": "This will be a hard day. Have support lined up.",
            "notify_agent": True,
        },
        {
            "title": "Beach picnic with friends",
            "date": today + timedelta(days=8),
            "event_type": "milestone",
            "notes": "First social outing in a while. Mom would approve.",
            "notify_agent": False,
        },
    ]

    for e in events:
        session.add(CalendarEvent(user_id=alice.id, **e))
    print(f"  created {len(events)} calendar events for {alice.email}")

    # --- Assessments (onboarding baseline) ---
    # PHQ-9: score 12 = moderate depression
    phq9 = Assessment(
        user_id=alice.id,
        instrument="phq9",
        responses={f"q{i}": v for i, v in enumerate([2, 2, 1, 2, 1, 1, 1, 1, 1], 1)},
        total_score=12,
        severity="moderate",
        source="onboarding",
    )
    phq9.created_at = datetime.now(timezone.utc) - timedelta(days=14)
    session.add(phq9)

    # GAD-7: score 8 = mild anxiety
    gad7 = Assessment(
        user_id=alice.id,
        instrument="gad7",
        responses={f"q{i}": v for i, v in enumerate([2, 1, 1, 1, 1, 1, 1], 1)},
        total_score=8,
        severity="mild",
        source="onboarding",
    )
    gad7.created_at = datetime.now(timezone.utc) - timedelta(days=14)
    session.add(gad7)
    print(f"  created baseline assessments for {alice.email} (PHQ-9: 12/moderate, GAD-7: 8/mild)")

    # --- Treatment plan ---
    plan = TreatmentPlan(user_id=alice.id, title="Grief recovery plan", status="active")
    session.add(plan)
    await session.flush()

    goals = [
        TreatmentGoal(
            plan_id=plan.id,
            description="Write in journal at least 3 times per week",
            target_date=today + timedelta(days=30),
            status="in_progress",
            progress_notes=[
                {"date": str(today - timedelta(days=7)), "note": "Wrote 2 entries this week. Getting easier."},
                {"date": str(today - timedelta(days=2)), "note": "Hit 3 entries! Feeling more consistent."},
            ],
        ),
        TreatmentGoal(
            plan_id=plan.id,
            description="Practice 5-minute mindfulness meditation daily",
            target_date=today + timedelta(days=30),
            status="in_progress",
            progress_notes=[
                {"date": str(today - timedelta(days=5)), "note": "Did 3 days in a row, then forgot."},
            ],
        ),
        TreatmentGoal(
            plan_id=plan.id,
            description="Attend grief support group at least twice this month",
            target_date=today + timedelta(days=30),
            status="not_started",
            progress_notes=[],
        ),
        TreatmentGoal(
            plan_id=plan.id,
            description="Identify and challenge one cognitive distortion per week",
            target_date=today + timedelta(days=60),
            status="in_progress",
            progress_notes=[
                {"date": str(today - timedelta(days=3)), "note": "Caught catastrophizing about burning dinner. Reframed successfully."},
            ],
        ),
    ]
    for g in goals:
        session.add(g)
    print(f"  created treatment plan with {len(goals)} goals for {alice.email}")

    # --- Mood logs (14 days of data for trend) ---
    mood_data = [
        (14, 4, "sad"),
        (13, 3, "numb"),
        (12, 4, "anxious"),
        (11, 5, None),
        (10, 6, "hopeful"),
        (9, 5, None),
        (8, 4, "sad"),
        (7, 3, "anxious"),
        (6, 5, None),
        (5, 5, "calm"),
        (4, 6, "hopeful"),
        (3, 5, None),
        (2, 6, None),
        (1, 7, "hopeful"),
    ]
    for days_ago, score, label in mood_data:
        mood = MoodLog(
            user_id=alice.id,
            score=score,
            label=label,
            source="check_in",
        )
        mood.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        session.add(mood)
    print(f"  created {len(mood_data)} mood logs for {alice.email} (trending up: 4→7)")


async def seed(session: AsyncSession) -> None:
    users = {}
    for entry in SEED_USERS:
        users[entry["email"]] = await _ensure_user(session, entry)

    # Alice gets full data
    await _seed_alice_data(session, users["alice@example.com"])

    # Bob and Carol get basic profiles
    await _ensure_profile(
        session,
        users["bob@example.com"],
        grief_type="breakup",
        support_system="strong",
        prior_therapy=False,
        preferred_approaches=["just talking"],
        onboarding_completed=True,
    )
    await _ensure_profile(
        session,
        users["carol@example.com"],
        grief_type="life_transition",
        support_system="none",
        prior_therapy=True,
        preferred_approaches=["cbt", "mindfulness"],
        onboarding_completed=True,
    )

    await session.commit()


async def main() -> None:
    print("Seeding users and therapeutic data...")
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
