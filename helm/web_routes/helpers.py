"""
helm/web_routes/helpers.py — Helper functions for model discovery (Claude, Ollama, Gemini, OpenAI, Codex).
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import urllib.request
from typing import Optional

from helm.subprocess_utils import hidden_kwargs


def _npm_global_roots() -> list[pathlib.Path]:
    """Return candidate npm global node_modules directories (cached).

    FAST — avoids subprocess calls (npm root -g can hang on Windows).
    Uses only environment variables and well-known paths.
    """
    if hasattr(_npm_global_roots, "_cache"):
        return _npm_global_roots._cache

    roots: list[pathlib.Path] = []
    # 1. Common Windows npm locations (FAST — no subprocess)
    if os.environ.get("APPDATA"):
        roots.append(pathlib.Path(os.environ["APPDATA"]) / "npm" / "node_modules")
    # 2. Derive from CLI binary location (instant — just path manipulation)
    for cli_name in ("gemini", "gemini.cmd", "codex", "codex.cmd"):
        cli = shutil.which(cli_name)
        if cli:
            roots.append(pathlib.Path(cli).resolve().parent / "node_modules")
            break  # all npm CLIs share the same root
    # 3. nvm-windows locations
    if os.environ.get("NVM_SYMLINK"):
        roots.append(pathlib.Path(os.environ["NVM_SYMLINK"]) / "node_modules")
    # 4. Unix locations
    roots += [
        pathlib.Path("/usr/lib/node_modules"),
        pathlib.Path("/usr/local/lib/node_modules"),
        pathlib.Path("/opt/homebrew/lib/node_modules"),
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[pathlib.Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    _npm_global_roots._cache = deduped
    return deduped


def _scan_npm_package(package_names: list[str], pattern, min_len: int = 8,
                      max_files: int = 15) -> list[str]:
    """Scan code files in a globally-installed npm package for model IDs.

    FAST — uses only shallow (non-recursive) globs to avoid scanning
    hundreds of files.  Checks only the most-likely bundle locations.
    """
    for root in _npm_global_roots():
        if not root.exists():
            continue
        for pkg_name in package_names:
            parts = pkg_name.split("/")
            pkg_dir = root.joinpath(*parts)
            if not pkg_dir.exists():
                continue
            found: set[str] = set()
            try:
                # Shallow globs only — fast on Windows (no recursive **)
                candidates: list[pathlib.Path] = []
                for ext in ("*.js", "*.mjs", "*.cjs"):
                    candidates.extend(pkg_dir.glob(ext))
                    for d in ("dist", "build", "lib", "bin", "src"):
                        subdir = pkg_dir / d
                        if subdir.is_dir():
                            candidates.extend(subdir.glob(ext))
                # Sort by size descending (cheap — only a handful of files)
                candidates.sort(key=lambda f: f.stat().st_size, reverse=True)
                for code_file in candidates[:max_files]:
                    try:
                        text = code_file.read_text(encoding="utf-8", errors="ignore")
                        for m in pattern.findall(text):
                            if len(m) >= min_len:
                                found.add(m)
                    except Exception:
                        continue
            except Exception:
                pass
            if found:
                return sorted(found, reverse=True)
    return []


def _fetch_claude_models() -> list[str]:
    """Return available Claude models.
    Priority: (1) `claude api models list` CLI, (2) Anthropic REST API,
    (3) scan Claude Code npm package for hardcoded model IDs (no API key needed).
    """
    # ── Method 1: claude CLI ──────────────────────────────────────────────────
    cli = shutil.which("claude") or shutil.which("claude.cmd")
    if cli:
        try:
            r = subprocess.run(
                [cli, "api", "models", "list"],
                capture_output=True, text=True, timeout=10, **hidden_kwargs(),
            )
            if r.returncode == 0:
                data = json.loads(r.stdout)
                ids = [m["id"] for m in data.get("data", [])
                       if m.get("id", "").startswith("claude-")]
                if ids:
                    return ids
        except Exception:
            pass

    # ── Method 2: Anthropic REST API (needs ANTHROPIC_API_KEY) ───────────────
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models?limit=50",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                ids = [m["id"] for m in data.get("data", [])
                       if m.get("id", "").startswith("claude-")]
                if ids:
                    return ids
        except Exception:
            pass

    # ── Method 3: scan Claude Code npm package for hardcoded model IDs ───────
    # Works with OAuth-only auth — no API key needed.  The Claude Code CLI
    # (@anthropic-ai/claude-code) JS bundle contains every model name the CLI
    # itself knows about.
    _claude_model_pat = re.compile(
        r'["\'\`](claude-(?:opus|sonnet|haiku)-\d[\w.-]*)["\'\`]'
    )
    found = _scan_npm_package(
        ["@anthropic-ai/claude-code", "@anthropic-ai/claude"],
        _claude_model_pat, min_len=12,
    )
    if found:
        return found

    # ── Method 4: scan Claude Code native binary install directory ────────
    # When installed via `winget` or direct download, Claude Code lives at
    # ~/.local/bin/claude.EXE with support files nearby or in ~/.claude/.
    _claude_native_dirs: list[pathlib.Path] = []
    if cli:
        cli_dir = pathlib.Path(cli).resolve().parent
        _claude_native_dirs.append(cli_dir)
        _claude_native_dirs.append(cli_dir / "resources")
    _claude_native_dirs += [
        pathlib.Path.home() / ".claude",
        pathlib.Path.home() / ".claude" / "local",
    ]
    if os.environ.get("LOCALAPPDATA"):
        _claude_native_dirs.append(
            pathlib.Path(os.environ["LOCALAPPDATA"]) / "Programs" / "claude-code"
        )
    for d in _claude_native_dirs:
        if not d.exists():
            continue
        try:
            # Scan code/config files (shallow only — no recursive globs)
            files: list[pathlib.Path] = []
            for ext in ("*.js", "*.mjs", "*.json", "*.cjs"):
                files.extend(d.glob(ext))
            files.sort(key=lambda f: f.stat().st_size, reverse=True)
            found_native: set[str] = set()
            for f in files[:10]:
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    for m in _claude_model_pat.findall(text):
                        if len(m) > 12:
                            found_native.add(m)
                except Exception:
                    continue
            if found_native:
                return sorted(found_native, reverse=True)
        except Exception:
            continue

    # ── Method 5: `claude --version` + derive model family ───────────────
    # As a last resort, check if the CLI responds at all. If it does, it
    # supports the current model families — return the known latest models
    # for that CLI version.
    if cli:
        try:
            r = subprocess.run([cli, "--version"],
                               capture_output=True, text=True, timeout=5, **hidden_kwargs())
            if r.returncode == 0 and r.stdout.strip():
                # CLI is alive — it must support the current model families.
                # Extract version-aware model names from the version output.
                ver_text = r.stdout.strip().lower()
                # Try to detect model names embedded in version output
                for m in _claude_model_pat.findall(ver_text):
                    if m:
                        found_ver = set(_claude_model_pat.findall(ver_text))
                        if found_ver:
                            return sorted(found_ver, reverse=True)
        except Exception:
            pass

    return []


def _fetch_ollama_models() -> list[str]:
    """Return locally installed Ollama models via `ollama list`."""
    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5, **hidden_kwargs(),
        )
        models = []
        for line in r.stdout.splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        pass
    return []


def _fetch_openai_models() -> list[str]:
    """Return available OpenAI/Codex models via REST API or fallback to known list."""
    # ── Method 1: OpenAI REST API (needs OPENAI_API_KEY) ──────────────────────
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                ids = sorted([m["id"] for m in data.get("data", [])], reverse=True)
                if ids:
                    return ids
        except Exception:
            pass

    # ── Method 2: scan @codexconfig npm package for hardcoded model names ────
    _codex_model_pat = re.compile(
        r'["\'\`](gpt-\d+(?:-turbo)?(?:-[a-z]*)?)["\'\`]'
    )
    found = _scan_npm_package(
        ["@codexconfig/codex", "codex"],
        _codex_model_pat, min_len=5,
    )
    if found:
        return found

    # ── Method 3: known models (fallback) ──────────────────────────────────
    return [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]


def _fetch_gemini_models() -> list[str]:
    """Return available Gemini models via REST API or fallback to known list."""
    # ── Method 1: Google Generative AI REST API ────────────────────────────
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        try:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                ids = sorted([m.get("name", "").split("/")[-1] for m in data.get("models", [])],
                             reverse=True)
                if ids and ids != [""]:
                    return ids
        except Exception:
            pass

    # ── Method 2: scan google/generative-ai npm package ───────────────────────
    _gemini_model_pat = re.compile(
        r'["\'\`](gemini-[^\s"\'\`]+)["\'\`]'
    )
    found = _scan_npm_package(
        ["@google/generative-ai"],
        _gemini_model_pat, min_len=7,
    )
    if found:
        return found

    # ── Method 3: known models (fallback) ──────────────────────────────────
    return [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ]
