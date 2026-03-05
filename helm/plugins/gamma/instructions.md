# Gamma Plugin — RAPR AI

You have access to the Gamma API for generating beautiful presentations, documents, and webpages.
The user's API key is in the `GAMMA_API_KEY` environment variable.

## Authentication
```python
import os, requests, json, time

GAMMA_KEY = os.environ["GAMMA_API_KEY"]
HEADERS = {"X-API-KEY": GAMMA_KEY, "Content-Type": "application/json"}
BASE = "https://public-api.gamma.app/v1.0"
```

## Generate a Presentation
```python
# Step 1: Start generation
resp = requests.post(f"{BASE}/generate", headers=HEADERS, json={
    "topic": "Q1 2026 Business Review",
    "outputType": "presentation",
    "numCards": 8,
    "language": "en",
    "tone": "professional",
    "audience": "executives"
})
generation = resp.json()
generation_id = generation["id"]
print(f"Generation started: {generation_id}")

# Step 2: Poll until complete
while True:
    status_resp = requests.get(f"{BASE}/generate/{generation_id}", headers=HEADERS)
    status = status_resp.json()
    if status["status"] == "completed":
        print(f"Done! URL: {status['url']}")
        break
    elif status["status"] == "failed":
        print(f"Failed: {status.get('error')}")
        break
    time.sleep(3)
```

## Generate a Document
```python
resp = requests.post(f"{BASE}/generate", headers=HEADERS, json={
    "topic": "Product Requirements Document for Mobile App v2",
    "outputType": "document",
    "numCards": 10,
    "language": "en",
    "tone": "professional"
})
```

## Generate a Webpage
```python
resp = requests.post(f"{BASE}/generate", headers=HEADERS, json={
    "topic": "Company Landing Page for TechStartup Inc",
    "outputType": "webpage",
    "numCards": 6,
    "tone": "modern"
})
```

## Generate with Detailed Content
```python
resp = requests.post(f"{BASE}/generate", headers=HEADERS, json={
    "topic": "AI Trends in 2026",
    "outputType": "presentation",
    "numCards": 10,
    "language": "en",
    "tone": "engaging",
    "audience": "tech professionals",
    "additionalContext": "Focus on: LLM agents, multimodal AI, AI in healthcare, autonomous vehicles, and AI regulation. Include statistics and real-world examples."
})
```

## Generate from Outline
```python
resp = requests.post(f"{BASE}/generate", headers=HEADERS, json={
    "topic": "Sales Training Program",
    "outputType": "presentation",
    "outline": [
        "Introduction to Our Sales Methodology",
        "Understanding the Customer Journey",
        "Prospecting Best Practices",
        "Handling Objections",
        "Closing Techniques",
        "Follow-up and Retention",
        "Key Metrics and KPIs",
        "Q&A and Next Steps"
    ]
})
```

## List Recent Generations
```python
resp = requests.get(f"{BASE}/generations", headers=HEADERS,
                    params={"limit": 10})
for g in resp.json().get("generations", []):
    print(f"{g['topic']} — {g['status']} — {g.get('url', 'pending')}")
```

## Parameters Reference
- `outputType`: `"presentation"`, `"document"`, `"webpage"`, `"social_post"`
- `numCards`: Number of slides/sections (1-30)
- `tone`: `"professional"`, `"casual"`, `"engaging"`, `"academic"`, `"modern"`
- `language`: ISO 639-1 code (`"en"`, `"es"`, `"fr"`, `"de"`, `"hi"`, `"ja"`, etc.)
- `audience`: Free text describing target audience
- `additionalContext`: Extra details to guide content generation
- `outline`: Array of strings for explicit section titles (overrides numCards)

## Tips
- API key format: `sk-gamma-xxxxxxxx` — passed as `X-API-KEY` header (NOT Bearer)
- Requires Gamma Pro, Ultra, Teams, or Business plan
- Generation takes 30-90 seconds typically — always poll for completion
- Generated content is editable in the Gamma app after creation
- Rate limits vary by plan; generally 100+ generations per day on Pro
- The `url` in the response opens directly in gamma.app for editing
