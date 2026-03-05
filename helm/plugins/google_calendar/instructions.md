# Google Calendar Plugin — RAPR AI

You have access to the Google Calendar API. The user has connected via OAuth and a token is in the `GOOGLE_ACCESS_TOKEN` environment variable.

## Authentication
```python
import os, requests, json
from datetime import datetime, timezone, timedelta

GOOGLE_TOKEN = os.environ["GOOGLE_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}", "Content-Type": "application/json"}
CAL_BASE = "https://www.googleapis.com/calendar/v3"
```

## List Upcoming Events
```python
now = datetime.now(timezone.utc).isoformat()
resp = requests.get(f"{CAL_BASE}/calendars/primary/events", headers=HEADERS,
                    params={"timeMin": now, "maxResults": 10, "singleEvents": True,
                            "orderBy": "startTime"})
events = resp.json().get("items", [])
for e in events:
    start = e["start"].get("dateTime", e["start"].get("date"))
    print(f"{start} — {e['summary']}")
```

## Create an Event
```python
event = {
    "summary": "Team Standup",
    "description": "Daily sync with the engineering team",
    "start": {
        "dateTime": "2026-03-05T10:00:00",
        "timeZone": "Asia/Kolkata"
    },
    "end": {
        "dateTime": "2026-03-05T10:30:00",
        "timeZone": "Asia/Kolkata"
    },
    "attendees": [
        {"email": "alice@example.com"},
        {"email": "bob@example.com"}
    ],
    "reminders": {
        "useDefault": False,
        "overrides": [
            {"method": "popup", "minutes": 10}
        ]
    }
}
resp = requests.post(f"{CAL_BASE}/calendars/primary/events", headers=HEADERS, json=event)
print(f"Created: {resp.json().get('htmlLink')}")
```

## Create an All-Day Event
```python
event = {
    "summary": "Project Deadline",
    "start": {"date": "2026-03-15"},
    "end": {"date": "2026-03-16"},
    "colorId": "11"  # Red
}
requests.post(f"{CAL_BASE}/calendars/primary/events", headers=HEADERS, json=event)
```

## Update an Event
```python
event_id = "EVENT_ID"
requests.patch(f"{CAL_BASE}/calendars/primary/events/{event_id}", headers=HEADERS,
               json={"summary": "Updated: Team Standup", "location": "Zoom"})
```

## Delete an Event
```python
requests.delete(f"{CAL_BASE}/calendars/primary/events/{event_id}", headers=HEADERS)
```

## Search Events
```python
resp = requests.get(f"{CAL_BASE}/calendars/primary/events", headers=HEADERS,
                    params={"q": "standup", "timeMin": "2026-03-01T00:00:00Z",
                            "timeMax": "2026-03-31T23:59:59Z", "singleEvents": True})
```

## List Calendars
```python
resp = requests.get(f"{CAL_BASE}/users/me/calendarList", headers=HEADERS)
for cal in resp.json().get("items", []):
    print(f"{cal['summary']} ({cal['id']})")
```

## Tips
- Use `singleEvents=True` to expand recurring events into individual instances
- Color IDs: 1=Lavender, 2=Sage, 3=Grape, 4=Flamingo, 5=Banana, 6=Tangerine, 7=Peacock, 8=Graphite, 9=Blueberry, 10=Basil, 11=Tomato
- Time zones: use IANA format (e.g., "Asia/Kolkata", "America/New_York")
- For recurring events: add `recurrence: ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"]`
- Rate limit: 500 requests per 100 seconds per user
