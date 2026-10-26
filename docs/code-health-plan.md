# Code health plan: large files and swallowed errors

Follow-up to the public review (Structure B-, Architecture B, Quality C+).
One pull request at a time. Each one is merged with CI green before the next
starts, changes behaviour in no way users can see, and ships with the tests
that prove it.

## Where things stand (26 Oct 2026)

| Problem | Size | Safety net today |
|---|---|---|
| `helm/ai_runner/core.py` | 1,996 lines; `process_message` 514 and `_run_single_ai` 498 of them | Tests run 38% of `process_message`, 30% of `_run_single_ai` |
| `frontend2/js/complete.js` | 3,606 lines, 173 global functions, called from `onclick` in `index.html` | No frontend tests at all |
| Unused frontend files | `app.js`, `api.js`, `ws.js`, `state.js`, `commands.js`, `toast.js`, `config.js` and `layout.css`: 6,100 lines no page loads (the service worker only caches them) | n/a |
| `except …: pass` | 256 places (web_routes 45, learning 37, ai_runner 36, agent 19, mcp 14, cloud_backup 11, web_app.py 11, auth.py 7, others 76) | Lint can find them (ruff S110) but doesn't enforce it yet |

The large files aren't the real problem: two functions are. Splitting the file
without breaking those functions up would only move the mess.

## Rules for every step

- **Tests first.** Code with low coverage gets tests that pin down what it does
  today before anyone moves it. A refactor PR doesn't change those tests.
- **Moves are moves.** A PR that moves code doesn't also change it. Where it can,
  it proves the move (for example, the new JS files joined together equal the
  old one).
- **Names stay reachable.** Tests and 38 modules import from `helm.ai_runner`
  and patch `helm.ai_runner.core.*`. Moved functions stay importable from
  their old place until nothing uses the old path.
- **Lint ratchets.** Once a part of the code is clean of swallowed errors,
  `ruff.toml` enforces S110 there, so it can't come back.

## Track A: unused frontend code (1 PR, small)

- **A1:** Delete the 8 unused files. The service worker caches exactly what
  `index.html` loads, under a new cache name so browsers drop the old copies;
  a test keeps the two in step. Found on the way: the web UI's own JS and CSS
  counted against the API rate limit, so three quick reloads made the UI's API
  calls fail with 429. They're exempt now.

## Track E: found along the way

- **E1, fonts:** the UI asks for Inter and JetBrains Mono from Google Fonts,
  but RAPR's Content Security Policy blocks that, so every user sees fallback
  system fonts. Ship the two fonts with RAPR (works offline, nothing sent to
  Google) and drop the external `@import`s.

## Track B: `complete.js`

- **B1, the safety net:** a Playwright smoke test in CI. It starts RAPR
  headless, opens the web UI, fails on any console error, checks that every
  function an `onclick` in `index.html` names exists, and goes through the main
  flows (open a session, send a message to a fake AI, open settings, the
  folder picker, history). This is the first frontend test RAPR has.
- **B2, the mechanical split:** cut `complete.js` along its existing section
  markers into about 8 plain scripts (connection and state, sessions and
  sidebar, messages, folder picker, thinking and activity, voice, onboarding,
  settings), loaded in the same order. No code changes. Proof: joining the new
  files gives back the old file; B1 passes.
- **Later, not planned yet:** move the pieces to ES modules, one file per PR.

## Track C: `core.py`

- **C1, characterisation tests:** cover `process_message` (budget block,
  `/model`, `/remember`, `/pipeline`, pipeline auto-suggest, the per-session
  lock, learning hooks, prompt preparation) and every branch of
  `_run_single_ai` (Claude with and without tools, other CLI AIs, Ollama,
  shell, Gemini's tier error, failure and retry) with a fake `run_ai_popen`.
  Target: both functions at 80% or more.
- **C2, slash commands out:** `/model`, `/remember` and `/pipeline` move from
  `process_message` to `ai_runner/slash_commands.py`. `process_message` asks
  that module whether a message is a command.
- **C3, one runner per AI type:** `_run_single_ai` becomes a short dispatcher.
  Its branches move next to the code they belong with: `run_claude` in
  `claude.py`, `run_ollama` in `ollama.py`, `run_cli_ai` in a new
  `cli_runner.py` (the short shell branch stays). The prompt enrichment and
  live-progress helper copied in the Claude and CLI branches become one
  function each (`prompt.py`, `streaming.py`).
- **C4, prompt preparation:** the safety preamble, learned context, memory and
  correction detection move to `ai_runner/prompt.py`, one function per step.
  What's left in `process_message` reads as the list of steps.

### Found while writing C1's tests (behaviour pinned as it is; not changed yet)

- **Claude's own cost is ignored for usage stats.** Claude Code reports what a
  reply cost; RAPR's usage stats (and so the budget page) price the tokens
  with its own table instead. The reported cost only reaches the learning
  system.
- **An AI that exits with an error but prints text "succeeds".** Only a silent
  non-zero exit, or text that looks like a CLI problem, counts as a failure;
  anything else is shown as the reply and isn't retried.
- **Some older tests share a database by accident.** They reuse a connection
  an earlier test left open. The new harness puts it back so they keep
  working; each should get its own database.

## Track D: swallowed errors

Each `except Exception: pass` becomes one of:
1. **A specific exception** when that failure is expected and harmless (a temp
   file that's already gone: `except OSError: pass` or `contextlib.suppress`).
2. **Logged** (`logger.warning(…, exc_info=True)`, or `debug` for noisy paths)
   when it's unexpected but shouldn't stop the work.
3. **Removed**, so the error surfaces, when hiding it was wrong (for example,
   it hides a failed security or data write).

Batches, the most important first:
- **D1, security and data (~33):** `auth.py` (a failed write of a wrong-PIN
  attempt is ignored, which quietly turns off the lockout), `token_vault.py`,
  `plugin_oauth.py`, `db_migrate.py`, `session_mgr.py`, `cloud_backup/`.
- **D2, web routes (~56):** `helm/web_routes/`, `web_app.py`.
- **D3, running AIs (~63):** `helm/ai_runner/`, `helm/telegram_bot/`, `helm/agent/`.
- **D4, the rest (~104):** `helm/learning/`, `helm/mcp/` and the remaining modules.

Since D1, S110 is on for the whole codebase except the files `ruff.toml` still
lists under D2, D3 and D4; each batch deletes its own lines from that list.

## Order and status

| Step | What | Status |
|---|---|---|
| A1 | Unused frontend files; UI files off the rate limit | Done (#104) |
| D1 | Swallowed errors: security and data | Done (#105) |
| C1 | Tests for `process_message` and `_run_single_ai` | Done (#106) |
| C2 | Slash commands out of `process_message` | Done (#107) |
| B1 | Browser smoke test in CI | Done (#108) |
| E1 | Ship the fonts | Done (#110) |
| B2 | Split `complete.js` | Done (#109) |
| C3 | One runner per AI type | Done (#111) |
| D2 | Swallowed errors: web routes | Done |
| C4 | Prompt preparation out of `process_message` | Done |
| D3 | Swallowed errors: running AIs | Done |
| D4 | Swallowed errors: the rest; S110 on everywhere | This PR |

Quick wins and the security batch come first. Each refactor follows the tests
it needs. Error batches are spread between refactors so no PR is huge.
