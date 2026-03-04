# Slack Plugin — RAPR AI

You have access to the Slack API via the `SLACK_BOT_TOKEN` environment variable.

## Authentication
```python
import os, requests

SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
HEADERS = {"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
BASE = "https://slack.com/api"
```

## Common Operations

### Send a message
```python
requests.post(f"{BASE}/chat.postMessage", headers=HEADERS, json={
    "channel": "#general",   # channel name or ID
    "text": "Hello from RAPR AI!"
})
```

### List channels
```python
resp = requests.get(f"{BASE}/conversations.list", headers=HEADERS,
                    params={"types": "public_channel,private_channel", "limit": 100})
channels = resp.json().get("channels", [])
for ch in channels:
    print(f"#{ch['name']} (id={ch['id']})")
```

### Read channel history
```python
resp = requests.get(f"{BASE}/conversations.history", headers=HEADERS,
                    params={"channel": "C0123ABCDEF", "limit": 20})
messages = resp.json().get("messages", [])
```

### Search messages
```python
resp = requests.get(f"{BASE}/search.messages", headers=HEADERS,
                    params={"query": "project update", "count": 10})
matches = resp.json().get("messages", {}).get("matches", [])
```

### Reply in a thread
```python
requests.post(f"{BASE}/chat.postMessage", headers=HEADERS, json={
    "channel": "C0123ABCDEF",
    "thread_ts": "1234567890.123456",
    "text": "Threaded reply"
})
```

### Upload a file
```python
requests.post(f"{BASE}/files.uploadV2",
    headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
    data={"channels": "C0123ABCDEF", "title": "Report"},
    files={"file": ("report.txt", open("report.txt", "rb"))}
)
```

### List users
```python
resp = requests.get(f"{BASE}/users.list", headers=HEADERS, params={"limit": 100})
users = resp.json().get("members", [])
```

## Tips
- Channel IDs start with `C` (public) or `G` (private). Use `conversations.list` to find them.
- User IDs start with `U`. Use `users.list` to look up names.
- For DMs, use `conversations.open` with a user ID to get the DM channel ID.
- Rate limits: ~1 req/sec for most methods. Add `time.sleep(1)` in loops.
- Always check `resp.json()["ok"]` for success.
