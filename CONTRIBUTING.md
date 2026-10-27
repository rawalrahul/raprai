# Contributing

Thanks for your interest in RAPR AI.

## Getting started

1. Install Python 3.11+ and at least one AI CLI (Claude Code, Gemini, Codex or Ollama).
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in what you need.
4. `python web_app.py`, then open http://localhost:8000.

See `README.md` for configuration and troubleshooting.

## Layout

| Path | What lives there |
|------|------------------|
| `web_app.py` | Entry point (FastAPI + Telegram bot) |
| `helm/` | Core: sessions, AI runners, memory, council, pipelines, plugins, MCP |
| `frontend2/` | Web UI (vanilla JS) |
| `tests/` | Test suite (`pytest`) |
| `.skills/skills/` | Built-in skill library loaded at startup |

## Pull requests

- Keep changes focused; one feature or fix per PR.
- Run `pytest` before opening a PR.
- Do not commit secrets, local databases, logs or `node_modules/`.

## Dependencies

`requirements.lock` is the exact, cross-platform set of versions RAPR is tested
with (`pip install -r requirements.lock` reproduces it). After changing
`requirements.txt`, regenerate it with:

    uv pip compile --universal --python-version 3.11 requirements.txt -o requirements.lock
