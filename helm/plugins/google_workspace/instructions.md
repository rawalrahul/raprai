# Google Workspace Plugin — RAPR AI

You have access to Google APIs. The user has connected via OAuth and a token is in the `GOOGLE_ACCESS_TOKEN` environment variable.

## Authentication — OAuth Token (auto-managed by RAPR AI)
```python
import os, requests

GOOGLE_TOKEN = os.environ["GOOGLE_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}"}
```

> If you prefer the google-api-python-client library:
> `pip install --break-system-packages google-api-python-client google-auth`
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(token=os.environ["GOOGLE_ACCESS_TOKEN"])
```

## Gmail

### List recent messages
```python
gmail = build("gmail", "v1", credentials=creds)
results = gmail.users().messages().list(userId="me", maxResults=10, q="is:unread").execute()
messages = results.get("messages", [])
for m in messages:
    msg = gmail.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    print(f"From: {headers.get('From')} Subject: {headers.get('Subject')}")
```

### Send an email
```python
import base64
from email.mime.text import MIMEText

message = MIMEText("Hello from RAPR AI!")
message["to"] = "recipient@example.com"
message["subject"] = "Test Email"
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
```

## Google Drive

### List files
```python
drive = build("drive", "v3", credentials=creds)
results = drive.files().list(pageSize=20, fields="files(id,name,mimeType)").execute()
for f in results.get("files", []):
    print(f"{f['name']} ({f['mimeType']})")
```

### Upload a file
```python
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload("report.pdf", mimetype="application/pdf")
drive.files().create(body={"name": "report.pdf"}, media_body=media).execute()
```

## Google Sheets

### Read a sheet
```python
sheets = build("sheets", "v4", credentials=creds)
result = sheets.spreadsheets().values().get(
    spreadsheetId="SHEET_ID", range="Sheet1!A1:D10"
).execute()
rows = result.get("values", [])
```

### Write to a sheet
```python
sheets.spreadsheets().values().update(
    spreadsheetId="SHEET_ID", range="Sheet1!A1",
    valueInputOption="USER_ENTERED",
    body={"values": [["Name", "Score"], ["Alice", 95], ["Bob", 87]]}
).execute()
```

## Google Calendar

### List upcoming events
```python
from datetime import datetime, timezone

cal = build("calendar", "v3", credentials=creds)
now = datetime.now(timezone.utc).isoformat()
events = cal.events().list(calendarId="primary", timeMin=now, maxResults=10).execute()
for e in events.get("items", []):
    print(f"{e['summary']} at {e['start'].get('dateTime', e['start'].get('date'))}")
```

## Tips
- Token is auto-managed by RAPR AI via OAuth. User clicked "Connect" in Settings.
- Install client library: `pip install --break-system-packages google-api-python-client google-auth`
- Works with personal Google accounts (gmail.com) — free, no Workspace plan needed.
- Rate limits vary by API; generally generous (100+ req/sec for Drive, Sheets).
- If token expires, RAPR AI will auto-refresh it using the stored refresh token.
