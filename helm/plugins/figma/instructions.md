# Figma Plugin — RAPR AI

You have access to the Figma API via the `FIGMA_API_TOKEN` environment variable.

## Authentication
```python
import os, requests

FIGMA_TOKEN = os.environ["FIGMA_API_TOKEN"]
HEADERS = {"X-Figma-Token": FIGMA_TOKEN}
BASE = "https://api.figma.com/v1"
```

## Common Operations

### List user files (recent)
```python
resp = requests.get(f"{BASE}/me", headers=HEADERS)
user = resp.json()
print(f"Logged in as: {user.get('handle', 'Unknown')}")
```

### Get a file
```python
file_key = "abc123XYZ"  # from the Figma URL
resp = requests.get(f"{BASE}/files/{file_key}", headers=HEADERS)
file_data = resp.json()
print(f"File: {file_data['name']} — Last modified: {file_data['lastModified']}")
```

### Get file components
```python
resp = requests.get(f"{BASE}/files/{file_key}/components", headers=HEADERS)
components = resp.json().get("meta", {}).get("components", [])
for c in components:
    print(f"{c['name']} — {c['description']}")
```

### Get comments on a file
```python
resp = requests.get(f"{BASE}/files/{file_key}/comments", headers=HEADERS)
comments = resp.json().get("comments", [])
for c in comments:
    print(f"{c['user']['handle']}: {c['message']}")
```

### Post a comment
```python
requests.post(f"{BASE}/files/{file_key}/comments", headers=HEADERS, json={
    "message": "Looks great! Ready for handoff."
})
```

### Export frames as PNG
```python
node_ids = "1:2,3:4"  # comma-separated node IDs
resp = requests.get(f"{BASE}/images/{file_key}", headers=HEADERS,
                    params={"ids": node_ids, "format": "png", "scale": 2})
images = resp.json().get("images", {})
for node_id, url in images.items():
    print(f"Node {node_id}: {url}")
```

### Get file styles
```python
resp = requests.get(f"{BASE}/files/{file_key}/styles", headers=HEADERS)
styles = resp.json().get("meta", {}).get("styles", [])
for s in styles:
    print(f"{s['name']} ({s['style_type']})")
```

### List team projects
```python
team_id = "123456"
resp = requests.get(f"{BASE}/teams/{team_id}/projects", headers=HEADERS)
projects = resp.json().get("projects", [])
for p in projects:
    print(f"{p['name']} (id: {p['id']})")
```

## Tips
- File key is in the Figma URL: figma.com/file/{file_key}/...
- Node IDs use the format "1:2" — find them in the Figma URL after `node-id=`
- Rate limit: 30 req/minute. Check response headers for limits.
- Export formats: png, jpg, svg, pdf
- Use `geometry=paths` param on /files to get vector paths.
