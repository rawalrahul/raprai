# Google Sheets Plugin — RAPR AI

You have access to the Google Sheets API. The user has connected via OAuth and a token is in the `GOOGLE_ACCESS_TOKEN` environment variable.

## Authentication
```python
import os, requests, json

GOOGLE_TOKEN = os.environ["GOOGLE_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}", "Content-Type": "application/json"}
SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
```

## Read a Sheet
```python
sheet_id = "YOUR_SPREADSHEET_ID"
range_name = "Sheet1!A1:D10"

resp = requests.get(f"{SHEETS_BASE}/{sheet_id}/values/{range_name}", headers=HEADERS)
rows = resp.json().get("values", [])
for row in rows:
    print(row)
```

## Write to a Sheet
```python
resp = requests.put(
    f"{SHEETS_BASE}/{sheet_id}/values/{range_name}",
    headers=HEADERS,
    params={"valueInputOption": "USER_ENTERED"},
    json={"values": [["Name", "Score", "Grade"], ["Alice", 95, "A"], ["Bob", 87, "B+"]]}
)
```

## Create a New Spreadsheet
```python
resp = requests.post(SHEETS_BASE, headers=HEADERS, json={
    "properties": {"title": "Sales Report 2026"},
    "sheets": [{"properties": {"title": "Q1 Data"}}]
})
new_sheet = resp.json()
new_id = new_sheet["spreadsheetId"]
print(f"Created: https://docs.google.com/spreadsheets/d/{new_id}")
```

## Append Rows
```python
requests.post(
    f"{SHEETS_BASE}/{sheet_id}/values/Sheet1!A:D:append",
    headers=HEADERS,
    params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
    json={"values": [["Carol", 92, "A-"], ["Dave", 78, "C+"]]}
)
```

## Get Spreadsheet Metadata
```python
resp = requests.get(f"{SHEETS_BASE}/{sheet_id}", headers=HEADERS,
                    params={"fields": "sheets.properties"})
sheets = resp.json().get("sheets", [])
for s in sheets:
    print(f"Sheet: {s['properties']['title']} (ID: {s['properties']['sheetId']})")
```

## List Spreadsheets from Drive
```python
DRIVE_HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}"}
resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=DRIVE_HEADERS,
                    params={"q": "mimeType='application/vnd.google-apps.spreadsheet'",
                            "fields": "files(id,name)", "pageSize": 20})
files = resp.json().get("files", [])
for f in files:
    print(f"{f['name']}: https://docs.google.com/spreadsheets/d/{f['id']}")
```

## Tips
- Spreadsheet ID is in the URL: `docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
- Range notation: `Sheet1!A1:D10`, `Sheet1!A:D` (entire columns), `Sheet1` (entire sheet)
- `valueInputOption`: `USER_ENTERED` (parses formulas) or `RAW` (literal values)
- Rate limit: 100 requests per 100 seconds per user
