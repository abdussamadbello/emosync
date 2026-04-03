from datetime import datetime, timedelta
from datetime import UTC

today = datetime.now(UTC).date()
EVENTS = [
    {
        "id": "1",
        "title": "Test Event",
        "date": (today + timedelta(days=1)).isoformat(),  # always within upcoming window
        "type": "test",
        "metadata": {}
    }
]
