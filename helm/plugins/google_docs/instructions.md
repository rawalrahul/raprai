# Google Docs Plugin — RAPR AI

You have access to the Google Docs API. The user has connected via OAuth and a token is in the `GOOGLE_ACCESS_TOKEN` environment variable.

## Authentication
```python
import os, requests, json

GOOGLE_TOKEN = os.environ["GOOGLE_ACCESS_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}", "Content-Type": "application/json"}
DOCS_BASE = "https://docs.googleapis.com/v1/documents"
```

## Read a Document
```python
doc_id = "YOUR_DOCUMENT_ID"
resp = requests.get(f"{DOCS_BASE}/{doc_id}", headers=HEADERS)
doc = resp.json()

# Extract plain text
content = doc.get("body", {}).get("content", [])
text = ""
for element in content:
    if "paragraph" in element:
        for elem in element["paragraph"]["elements"]:
            text += elem.get("textRun", {}).get("content", "")
print(text)
```

## Create a New Document
```python
resp = requests.post(DOCS_BASE, headers=HEADERS, json={"title": "Meeting Notes — March 2026"})
new_doc = resp.json()
doc_id = new_doc["documentId"]
print(f"Created: https://docs.google.com/document/d/{doc_id}")
```

## Insert Text into a Document
```python
requests.post(f"{DOCS_BASE}/{doc_id}:batchUpdate", headers=HEADERS, json={
    "requests": [
        {"insertText": {"location": {"index": 1}, "text": "Meeting Notes\n\nAttendees: Alice, Bob, Carol\n\nAgenda:\n1. Project updates\n2. Budget review\n3. Next steps\n"}}
    ]
})
```

## Format Text (Bold, Heading, etc.)
```python
requests.post(f"{DOCS_BASE}/{doc_id}:batchUpdate", headers=HEADERS, json={
    "requests": [
        # Make "Meeting Notes" bold (characters 1-14)
        {"updateTextStyle": {
            "range": {"startIndex": 1, "endIndex": 15},
            "textStyle": {"bold": True, "fontSize": {"magnitude": 18, "unit": "PT"}},
            "fields": "bold,fontSize"
        }},
        # Set as heading
        {"updateParagraphStyle": {
            "range": {"startIndex": 1, "endIndex": 15},
            "paragraphStyle": {"namedStyleType": "HEADING_1"},
            "fields": "namedStyleType"
        }}
    ]
})
```

## List Documents from Drive
```python
DRIVE_HEADERS = {"Authorization": f"Bearer {GOOGLE_TOKEN}"}
resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=DRIVE_HEADERS,
                    params={"q": "mimeType='application/vnd.google-apps.document'",
                            "fields": "files(id,name,modifiedTime)", "pageSize": 20,
                            "orderBy": "modifiedTime desc"})
files = resp.json().get("files", [])
for f in files:
    print(f"{f['name']}: https://docs.google.com/document/d/{f['id']}")
```

## Tips
- Document ID is in the URL: `docs.google.com/document/d/{DOCUMENT_ID}/edit`
- Index positions start at 1 (index 0 is the document start marker)
- Use `batchUpdate` for all mutations — insert, delete, format
- For complex documents, consider creating locally with python-docx and uploading to Drive
- Rate limit: 300 requests per minute per user
