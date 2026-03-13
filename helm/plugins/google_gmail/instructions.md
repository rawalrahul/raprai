# Gmail Plugin — RAPR AI

You have access to the Gmail API. The user has connected via OAuth and a token is in the `GOOGLE_ACCESS_TOKEN` environment variable.

## Authentication
```python
import os, requests, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GOOGLE_TOKEN = os.environ["GOOGLE_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}"}
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
```

## List Recent Emails
```python
resp = requests.get(f"{GMAIL_BASE}/messages", headers=HEADERS,
                    params={"maxResults": 10, "q": "is:unread"})
messages = resp.json().get("messages", [])

for m in messages:
    msg = requests.get(f"{GMAIL_BASE}/messages/{m['id']}", headers=HEADERS,
                       params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}).json()
    hdrs = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    print(f"From: {hdrs.get('From')}  Subject: {hdrs.get('Subject')}")
```

## Read a Full Email
```python
msg = requests.get(f"{GMAIL_BASE}/messages/{msg_id}", headers=HEADERS,
                   params={"format": "full"}).json()
# Decode body
import base64
parts = msg["payload"].get("parts", [msg["payload"]])
for part in parts:
    if part["mimeType"] == "text/plain":
        body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
        print(body)
```

## Send an Email
```python
message = MIMEText("Hello! This is sent from RAPR AI.")
message["to"] = "recipient@example.com"
message["subject"] = "Test from RAPR AI"

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
requests.post(f"{GMAIL_BASE}/messages/send", headers={**HEADERS, "Content-Type": "application/json"},
              json={"raw": raw})
```

## Search Emails
```python
# Gmail search query syntax
resp = requests.get(f"{GMAIL_BASE}/messages", headers=HEADERS,
                    params={"q": "from:boss@company.com after:2025/01/01 has:attachment"})
```

## List Labels
```python
resp = requests.get(f"{GMAIL_BASE}/labels", headers=HEADERS)
labels = resp.json().get("labels", [])
```

## Tips
- Search query supports: `from:`, `to:`, `subject:`, `after:`, `before:`, `has:attachment`, `is:unread`, `label:`
- Rate limit: 250 quota units per second per user
- Always handle pagination via `nextPageToken`
- If token expires, RAPR AI will auto-refresh it using the stored refresh token
