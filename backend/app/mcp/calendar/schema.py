from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    id: str
    title: str
    date: datetime
    type: str  # "anniversary" | "holiday" | "memory" | "personal"
    metadata: Dict

class CalendarContext(BaseModel):
    upcoming_events: List[CalendarEvent]
    relevant_today: List[CalendarEvent]
