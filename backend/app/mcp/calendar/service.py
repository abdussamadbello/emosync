from datetime import datetime, timedelta,UTC
from .mock_data import EVENTS
from .schema import CalendarEvent, CalendarContext

class CalendarService:
    async def get_context(self, user_id: str):
        today = datetime.now(UTC).date()
        upcoming_window = today + timedelta(days=7)

        relevant_today = []
        upcoming = []

        for event in EVENTS:
            event_date = datetime.fromisoformat(event["date"]).date()
            event_obj = CalendarEvent(**event)
            if event_date == today:
                relevant_today.append(event_obj)
            if today <= event_date <= upcoming_window:
                upcoming.append(event_obj)

        return CalendarContext(
            relevant_today=relevant_today,
            upcoming_events=upcoming
        )
