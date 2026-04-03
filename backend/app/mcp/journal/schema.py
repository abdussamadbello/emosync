from datetime import datetime
from typing import List
from pydantic import BaseModel

class JournalEntry(BaseModel):
    id: str
    content: str
    created_at: datetime
    tags: List[str]
    score: float  # similarity score
