# NotebookLM Plugin — RAPR AI

You can interact with Google NotebookLM using the `notebooklm-py` Python library.
This gives you source-grounded, citation-backed answers from user-uploaded documents.

**IMPORTANT**: This plugin uses unofficial APIs. If you get auth errors, tell the
user to run `notebooklm login` in their terminal to refresh their Google session.

## Setup (one-time)
```bash
pip install "notebooklm-py[browser]"
python -m playwright install chromium
notebooklm login          # Opens Chromium browser for Google sign-in
```

## Authentication
```python
from notebooklm import NotebookLMClient

# Client auto-reads stored credentials from notebooklm login
client = NotebookLMClient()
```

## Core Operations

### List all notebooks
```python
notebooks = client.notebooks.list()
for nb in notebooks:
    print(f"- {nb.title} (id={nb.id})")
```

### Create a notebook
```python
nb = client.notebooks.create("Research: AI Memory Systems")
print(f"Created: {nb.id}")
```

### Delete a notebook
```python
client.notebooks.delete(notebook_id)
```

## Sources (Adding Documents to a Notebook)

### Add a URL source
```python
source = client.sources.add_url(notebook_id, "https://example.com/article")
print(f"Source added: {source.title}")
```

### Add a YouTube video
```python
source = client.sources.add_url(notebook_id, "https://youtube.com/watch?v=VIDEO_ID")
```

### Add a Google Drive file
```python
source = client.sources.add_drive(notebook_id, drive_file_id)
```

### Add text content directly
```python
source = client.sources.add_text(notebook_id, title="Meeting Notes", content="...")
```

### List sources in a notebook
```python
sources = client.sources.list(notebook_id)
for s in sources:
    print(f"- {s.title} ({s.type})")
```

### Delete a source
```python
client.sources.delete(notebook_id, source_id)
```

## Chat (RAG — Query Your Documents)

### Ask a question (gets source-grounded answer with citations)
```python
response = client.chat.send(notebook_id, "What are the key findings?")
print(response.text)
# Citations are included in the response
for citation in response.citations:
    print(f"  Source: {citation.source_title}, passage: {citation.text[:100]}")
```

### Multi-turn conversation
```python
r1 = client.chat.send(notebook_id, "Summarize the main arguments")
r2 = client.chat.send(notebook_id, "How does the author support point #2?")
# Conversation context is maintained within the notebook
```

## Artifacts (Content Generation)

### Generate an Audio Overview (Podcast)
```python
audio = client.artifacts.generate(notebook_id, "audio_overview")
# Returns audio file info
print(f"Audio: {audio.url}")
```

### Generate other artifact types
```python
# Available types: audio_overview, briefing_doc, study_guide,
#                  timeline, faq, quiz, mind_map

quiz = client.artifacts.generate(notebook_id, "quiz")
study = client.artifacts.generate(notebook_id, "study_guide")
mindmap = client.artifacts.generate(notebook_id, "mind_map")
faq = client.artifacts.generate(notebook_id, "faq")
```

## Research (Web Search + Auto-Import)

### Run a research query
```python
results = client.research.query(notebook_id, "latest advances in RAG systems")
# Finds relevant sources and optionally imports them
for r in results:
    print(f"- {r.title}: {r.url}")
```

## Notes

### Save a chat response as a note
```python
note = client.notes.create(notebook_id, title="Key Findings", content=response.text)
```

### List notes
```python
notes = client.notes.list(notebook_id)
```

## Settings & Sharing

### Update notebook settings
```python
client.settings.update(notebook_id, language="en", response_style="detailed")
```

### Share a notebook
```python
client.sharing.add(notebook_id, email="partner@example.com", role="viewer")
```

## Typical Workflow for Users

1. User says "Research X using NotebookLM"
2. Create a notebook: `client.notebooks.create("Research: X")`
3. Add sources: URLs, documents, YouTube videos
4. Query the documents: `client.chat.send(notebook_id, question)`
5. Generate artifacts: audio overview, study guide, quiz, etc.
6. Return the answers with citations to the user

## Error Handling
```python
try:
    response = client.chat.send(notebook_id, question)
except Exception as e:
    if "auth" in str(e).lower() or "401" in str(e) or "403" in str(e):
        # Auth expired — tell user to re-login
        print("NotebookLM auth expired. Run: notebooklm login")
    else:
        raise
```

## Tips
- Auth cookies expire every 1-2 weeks. User must run `notebooklm login` to refresh.
- Each notebook can have up to 50 sources (NotebookLM limit).
- Audio overviews take 2-5 minutes to generate.
- Chat responses include citations — always show these to the user.
- This uses unofficial APIs — if NotebookLM updates, the plugin may break.
- For production use, recommend Google NotebookLM Enterprise API instead.
