# Zapier Plugin — RAPR AI

You can trigger Zapier automations via webhooks or use the Zapier Natural Language Actions (NLA) API.

## Method 1: Webhooks (simple, recommended)

The user sets up a "Catch Hook" trigger in Zapier and provides the webhook URL.

```python
import os, requests

WEBHOOK_URL = os.environ["ZAPIER_WEBHOOK_URL"]

# Trigger a Zap by sending JSON data
resp = requests.post(WEBHOOK_URL, json={
    "action": "send_email",
    "to": "team@example.com",
    "subject": "Weekly Report",
    "body": "Here is the weekly summary..."
})
print(f"Status: {resp.status_code}")  # 200 = success
```

### Multiple webhooks
If the user has multiple Zaps, the webhook URL env var can contain a comma-separated list or a JSON mapping:
```python
import json

webhooks = json.loads(os.environ.get("ZAPIER_WEBHOOK_URL", "{}"))
# e.g. {"email": "https://hooks.zapier.com/xxx", "slack": "https://hooks.zapier.com/yyy"}

# Trigger the email Zap
requests.post(webhooks["email"], json={"to": "boss@co.com", "subject": "Update"})
```

## Method 2: Natural Language Actions (NLA) API

The NLA API lets you execute pre-configured actions using natural language.

```python
import os, requests

NLA_KEY = os.environ["ZAPIER_NLA_API_KEY"]
HEADERS = {"x-api-key": NLA_KEY, "Content-Type": "application/json"}
NLA_BASE = "https://nla.zapier.com/api/v1"
```

### List available actions
```python
resp = requests.get(f"{NLA_BASE}/exposed/", headers=HEADERS)
actions = resp.json().get("results", [])
for a in actions:
    print(f"{a['id']}: {a['description']}")
```

### Execute an action
```python
resp = requests.post(f"{NLA_BASE}/exposed/{action_id}/execute/", headers=HEADERS, json={
    "instructions": "Send a Slack message to #general saying 'Deployment complete'"
})
result = resp.json()
print(result.get("result", result.get("error")))
```

### Preview an action (dry run)
```python
resp = requests.post(f"{NLA_BASE}/exposed/{action_id}/preview/", headers=HEADERS, json={
    "instructions": "Create a Google Calendar event for tomorrow at 3pm called Team Sync"
})
preview = resp.json()
print("Would do:", preview.get("input_params"))
```

## Tips
- **Webhooks** are the simplest approach — just POST JSON and Zapier handles the rest.
- **NLA API** is more flexible but requires the user to expose specific actions in their Zapier account.
- Webhook URLs look like: `https://hooks.zapier.com/hooks/catch/123456/abcdef/`
- Each Zap can have complex multi-step workflows. The AI just triggers step 1.
- For security, never expose webhook URLs in logs or responses.
- Rate limits: Zapier Free = 100 tasks/month, Pro = 2,000+.
