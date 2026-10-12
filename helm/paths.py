"""
helm/paths.py — Runtime path resolver for both development and PyInstaller bundle.

When running from source:
    PROJECT_ROOT = the directory containing web_app.py
    __file__ works normally, all relative paths resolve as expected.

When running from a PyInstaller bundle:
    sys._MEIPASS points to the temporary extraction directory (one-dir mode)
    or the embedded filesystem (one-file mode).  We set PROJECT_ROOT to
    the bundle root and provide helper functions that resolve paths
    relative to it.

Every module that needs to find files (frontend, integrations, plugins,
skills, static assets) should import from here instead of using
``Path(__file__).parent``.

Public API:
    PROJECT_ROOT        pathlib.Path   — root of the app (source or bundle)
    HELM_DIR            pathlib.Path   — helm/ package directory
    is_bundled()        bool           — True when running inside PyInstaller
    resolve(rel)        pathlib.Path   — resolve a path relative to PROJECT_ROOT
    user_data_dir()     pathlib.Path   — writable directory for runtime data
"""

import os
import pathlib
import sys


def is_bundled() -> bool:
    """Return True when running inside a PyInstaller or Nuitka bundle."""
    # PyInstaller sets sys.frozen and sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return True
    # Nuitka sets __compiled__ at module level in compiled modules
    if "__compiled__" in globals():
        return True
    return False


if is_bundled():
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller sets sys._MEIPASS to the bundle extraction directory
        PROJECT_ROOT = pathlib.Path(sys._MEIPASS)
    else:
        # Nuitka --standalone: the .exe sits inside web_app.dist/
        PROJECT_ROOT = pathlib.Path(sys.executable).resolve().parent
else:
    # Development: helm/ is one level below the project root
    PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

HELM_DIR = PROJECT_ROOT / "helm"


def resolve(*parts: str) -> pathlib.Path:
    """Resolve a path relative to the project root (works in both modes)."""
    return PROJECT_ROOT.joinpath(*parts)


def user_data_dir() -> pathlib.Path:
    """
    Return the writable directory for runtime data (chat logs, .env, etc.).

    In development this is PROJECT_ROOT itself.
    In a bundled build this is the directory containing the .exe, which is
    writable and persists across runs (unlike _MEIPASS which is temporary).
    """
    override = os.environ.get("RAPR_DATA_DIR", "").strip()   # set in the server container
    if override:
        p = pathlib.Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if is_bundled():
        return pathlib.Path(sys.executable).parent
    return PROJECT_ROOT


def packages_cache_dir() -> pathlib.Path:
    """Return the directory for cached marketplace data (catalogs, downloads)."""
    d = user_data_dir() / "packages_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def packages_staging_dir() -> pathlib.Path:
    """Return the directory for temporary package extraction during install."""
    d = user_data_dir() / "packages_staging"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Backward compatibility aliases
helmpack_cache_dir = packages_cache_dir
helmpack_staging_dir = packages_staging_dir


def child_env(cmd, extra_env=None):
    """Environment for an AI subprocess, or None to inherit RAPR's unchanged.

    A command that runs RAPR's own Python (``python -m helm.ai_runner…``, used by
    Groq, OpenRouter, GitHub Models and local servers) needs RAPR's code on its
    path: sessions start in the project folder, not the app folder, so
    ``-m helm…`` can't find RAPR from the working directory. Other AIs get no
    PYTHONPATH change, so RAPR's folders can't shadow a Python-based AI's modules.
    """
    own_python = bool(cmd) and os.path.normcase(os.path.abspath(str(cmd[0]))) == \
        os.path.normcase(os.path.abspath(sys.executable))
    if not own_python:
        return {**os.environ, **extra_env} if extra_env else None
    env = {**os.environ, **(extra_env or {})}
    root = str(PROJECT_ROOT)
    parts = [x for x in env.get("PYTHONPATH", "").split(os.pathsep) if x]
    if root not in parts:
        env["PYTHONPATH"] = os.pathsep.join([root] + parts)
    return env
