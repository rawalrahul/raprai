# Airtable Plugin — RAPR AI

You have access to the Airtable API via the `AIRTABLE_API_KEY` environment variable.

## Authentication
```python
import os, requests

AT_TOKEN = os.environ["AIRTABLE_API_KEY"]
HEADERS = {
    "Authorization": f"Bearer {AT_TOKEN}",
    "Content-Type": "application/json"
}
BASE = "https://api.airtable.com/v0"
```

## Common Operations

### List bases
```python
resp = requests.get("https://api.airtable.com/v0/meta/bases", headers=HEADERS)
bases = resp.json().get("bases", [])
for b in bases:
    print(f"{b['name']} (id={b['id']})")
```

### List tables in a base
```python
resp = requests.get(f"https://api.airtable.com/v0/meta/bases/{base_id}/tables", headers=HEADERS)
tables = resp.json().get("tables", [])
```

### List records
```python
resp = requests.get(f"{BASE}/{base_id}/{table_name}", headers=HEADERS,
                    params={"maxRecords": 50, "view": "Grid view"})
records = resp.json().get("records", [])
for r in records:
    print(r["id"], r["fields"])
```

### Query with filter
```python
resp = requests.get(f"{BASE}/{base_id}/{table_name}", headers=HEADERS, params={
    "filterByFormula": "AND({Status}='Active', {Priority}='High')",
    "sort[0][field]": "Created",
    "sort[0][direction]": "desc"
})
```

### Create a record
```python
requests.post(f"{BASE}/{base_id}/{table_name}", headers=HEADERS, json={
    "records": [
        {"fields": {"Name": "New Task", "Status": "Todo", "Priority": "Medium"}}
    ]
})
```

### Update a record
```python
requests.patch(f"{BASE}/{base_id}/{table_name}", headers=HEADERS, json={
    "records": [
        {"id": "rec123ABC", "fields": {"Status": "Done"}}
    ]
})
```

### Delete records
```python
requests.delete(f"{BASE}/{base_id}/{table_name}", headers=HEADERS,
                params={"records[]": ["rec123ABC", "rec456DEF"]})
```

### Create multiple records (batch)
```python
# Airtable supports up to 10 records per request
batch = [{"fields": {"Name": f"Item {i}"}} for i in range(10)]
requests.post(f"{BASE}/{base_id}/{table_name}", headers=HEADERS, json={"records": batch})
```

## Tips
- Use a Personal Access Token (PAT) — classic API keys are deprecated.
- Table names can be the display name (URL-encoded) or the table ID (tblXXX).
- `filterByFormula` uses Airtable's formula syntax (similar to Excel).
- Rate limit: 5 requests/second per base. Add `time.sleep(0.25)` in loops.
- Pagination: if `resp.json()` has `"offset"`, pass it as a param to get the next page.
- Max 10 records per create/update batch. Loop for larger datasets.
