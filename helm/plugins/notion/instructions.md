# Notion Plugin — RAPR AI

You have access to the Notion API via the `NOTION_API_KEY` environment variable.

## Authentication
```python
import os, requests

NOTION_KEY = os.environ["NOTION_API_KEY"]
HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
BASE = "https://api.notion.com/v1"
```

## Common Operations

### Search all pages and databases
```python
resp = requests.post(f"{BASE}/search", headers=HEADERS, json={
    "query": "meeting notes",
    "sort": {"direction": "descending", "timestamp": "last_edited_time"}
})
results = resp.json().get("results", [])
```

### Get a page
```python
resp = requests.get(f"{BASE}/pages/{page_id}", headers=HEADERS)
page = resp.json()
title = page["properties"]["title"]["title"][0]["plain_text"]
```

### Create a page
```python
requests.post(f"{BASE}/pages", headers=HEADERS, json={
    "parent": {"database_id": "YOUR_DB_ID"},
    "properties": {
        "Name": {"title": [{"text": {"content": "New Item"}}]},
        "Status": {"select": {"name": "In Progress"}}
    },
    "children": [
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"text": {"content": "Page content here."}}]}}
    ]
})
```

### Query a database
```python
resp = requests.post(f"{BASE}/databases/{db_id}/query", headers=HEADERS, json={
    "filter": {
        "property": "Status",
        "select": {"equals": "In Progress"}
    },
    "sorts": [{"property": "Created", "direction": "descending"}]
})
items = resp.json().get("results", [])
```

### Update a page property
```python
requests.patch(f"{BASE}/pages/{page_id}", headers=HEADERS, json={
    "properties": {
        "Status": {"select": {"name": "Done"}}
    }
})
```

### Append blocks to a page
```python
requests.patch(f"{BASE}/blocks/{page_id}/children", headers=HEADERS, json={
    "children": [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"text": {"content": "New Section"}}]}},
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"text": {"content": "Content goes here."}}]}}
    ]
})
```

## Tips
- Page and database IDs are 32-char hex strings (with or without dashes).
- The integration must be shared with pages/databases to access them (user does this in Notion UI).
- Use `search` first to discover available pages and databases.
- Rich text is always an array of text objects: `[{"text": {"content": "..."}}]`.
- Database properties vary (title, rich_text, select, multi_select, date, number, etc.).
- Rate limit: ~3 requests/second. Add `time.sleep(0.4)` in loops.
