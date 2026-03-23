"""
helm/helmpack/marketplace.py — Marketplace catalog manager.

Fetches a catalog JSON from a configurable URL, caches it locally
(1-hour TTL), and provides search/browse functionality.  Works
offline using the last cached version.

Public API:
    get_catalog(force_refresh=False) → list[dict]
    search_catalog(query, pkg_type=None) → list[dict]
    get_catalog_entry(package_id) → dict | None
    get_download_url(package_id) → str | None
"""

import json
import os
import time
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Default catalog URL — override with HELMPACK_CATALOG_URL env var
_DEFAULT_CATALOG_URL = "https://raprai.com/marketplace/catalog.json"

_CACHE_TTL = 3600  # 1 hour

# In-memory cache
_cached_catalog: list[dict] = []
_cached_at: float = 0.0


# ---------------------------------------------------------------------------
# Cache file management
# ---------------------------------------------------------------------------

def _cache_file_path():
    """Return path to the local catalog cache file."""
    from helm.paths import helmpack_cache_dir
    return helmpack_cache_dir() / "catalog.json"


def _load_cache() -> list[dict]:
    """Load catalog from local cache file."""
    path = _cache_file_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("packages", [])
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.warning("HelmPack: failed to load cached catalog: %s", e)
        return []


def _save_cache(catalog: list[dict]):
    """Save catalog to local cache file."""
    path = _cache_file_path()
    try:
        data = {
            "cached_at": time.time(),
            "packages": catalog,
        }
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("HelmPack: failed to save catalog cache: %s", e)


# ---------------------------------------------------------------------------
# Catalog fetching
# ---------------------------------------------------------------------------

def _catalog_url() -> str:
    """Return the catalog URL from env or default."""
    return os.environ.get("HELMPACK_CATALOG_URL", _DEFAULT_CATALOG_URL)


def _normalize_catalog_entry(entry: dict) -> dict:
    """Normalize a catalog entry so downstream code can rely on consistent fields.

    The website catalog uses ``slug`` / ``category`` while the app expects
    ``id`` / ``type``.  This function ensures both sets of keys exist.
    """
    if "slug" in entry and "id" not in entry:
        entry["id"] = entry["slug"]
    if "id" in entry and "slug" not in entry:
        entry["slug"] = entry["id"]
    if "category" in entry and "type" not in entry:
        entry["type"] = entry["category"]
    if "type" in entry and "category" not in entry:
        entry["category"] = entry["type"]
    return entry


def _fetch_remote_catalog() -> list[dict]:
    """Fetch catalog JSON from the remote URL."""
    import requests

    url = _catalog_url()
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "RAPR-AI-HelmPack/1.0",
            "Accept": "application/json",
        })
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict):
            items = data.get("packages", data.get("items", []))
        elif isinstance(data, list):
            items = data
        else:
            return []

        return [_normalize_catalog_entry(p) for p in items]

    except Exception as e:
        logger.warning("HelmPack: failed to fetch catalog from %s: %s", url, e)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_catalog(force_refresh: bool = False) -> list[dict]:
    """
    Return the marketplace catalog.

    Uses a 1-hour cache. Falls back to local cache if remote
    fetch fails (offline mode).

    Args:
        force_refresh: Bypass cache TTL and fetch from remote

    Returns: List of package dicts with at minimum:
        {id, type, name, description, version, author, keywords, download_url}
    """
    global _cached_catalog, _cached_at

    now = time.time()

    # Return in-memory cache if fresh
    if not force_refresh and _cached_catalog and (now - _cached_at) < _CACHE_TTL:
        return _cached_catalog

    # Try remote fetch
    remote = _fetch_remote_catalog()
    if remote:
        _cached_catalog = remote
        _cached_at = now
        _save_cache(remote)
        logger.info("HelmPack: catalog refreshed — %d packages", len(remote))
        return _cached_catalog

    # Fall back to local file cache
    local = _load_cache()
    if local:
        _cached_catalog = local
        _cached_at = now  # Prevent repeated fetch attempts
        logger.info("HelmPack: using cached catalog — %d packages (offline mode)", len(local))
        return _cached_catalog

    # Fall back to built-in demo catalog so the UI isn't empty
    builtin = _builtin_catalog()
    if builtin:
        _cached_catalog = builtin
        _cached_at = now
        logger.info("HelmPack: using built-in catalog — %d packages", len(builtin))
        return _cached_catalog

    logger.info("HelmPack: no catalog available (offline, no cache)")
    return []


def search_catalog(
    query: str = "",
    pkg_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search the catalog by keyword and/or type.

    Args:
        query: Search terms (matched against name, description, keywords)
        pkg_type: Filter by type ("mcp", "skill", "plugin")
        limit: Max results

    Returns: Matching catalog entries sorted by relevance
    """
    catalog = get_catalog()
    if not catalog:
        return []

    results = catalog

    # Filter by type
    if pkg_type:
        pkg_type = pkg_type.lower()
        results = [p for p in results if p.get("type", "").lower() == pkg_type]

    # Search by query
    if query:
        query_lower = query.lower()
        terms = query_lower.split()

        scored = []
        for pkg in results:
            score = _score_package(pkg, terms)
            if score > 0:
                scored.append((score, pkg))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [pkg for _, pkg in scored]

    # Mark installed packages
    try:
        from helm.helmpack.installer import list_installed
        installed_ids = {p["id"] for p in list_installed()}
        for pkg in results:
            pkg_id = pkg.get("id") or pkg.get("slug") or ""
            pkg["installed"] = pkg_id in installed_ids
    except Exception:
        pass

    return results[:limit]


def get_catalog_entry(package_id: str) -> Optional[dict]:
    """Return a specific catalog entry by ID or slug."""
    catalog = get_catalog()
    for pkg in catalog:
        if pkg.get("id") == package_id or pkg.get("slug") == package_id:
            return pkg
    return None


def get_download_url(package_id: str) -> Optional[str]:
    """Return the absolute download URL for a catalog package.

    Relative paths (e.g. ``/marketplace/packages/foo.raprpkg``) are
    resolved against the catalog base URL (``raprai.com``).
    """
    entry = get_catalog_entry(package_id)
    if not entry:
        return None
    url = entry.get("download_url") or entry.get("url") or ""
    if not url:
        return None
    # Resolve relative paths against the catalog origin
    if url.startswith("/"):
        from urllib.parse import urlparse
        catalog_url = _catalog_url()
        parsed = urlparse(catalog_url)
        url = f"{parsed.scheme}://{parsed.netloc}{url}"
    return url


# ---------------------------------------------------------------------------
# Built-in catalog (demo entries when no remote/local cache exists)
# ---------------------------------------------------------------------------

def _builtin_catalog() -> list[dict]:
    """Return an empty list — real catalog comes from raprai.com.

    The marketplace UI shows "Catalog unavailable (offline?)" when
    no remote catalog can be fetched and no local cache exists.
    """
    return []


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_package(pkg: dict, terms: list[str]) -> float:
    """Score a package against search terms. Higher = better match."""
    score = 0.0
    name = (pkg.get("name") or "").lower()
    desc = (pkg.get("description") or "").lower()
    pkg_id = (pkg.get("id") or "").lower()
    keywords = [k.lower() for k in pkg.get("keywords", [])]
    author = (pkg.get("author") or "").lower()

    for term in terms:
        # Exact ID match — highest relevance
        if term == pkg_id:
            score += 10.0
        elif term in pkg_id:
            score += 5.0

        # Name match
        if term in name:
            score += 4.0

        # Keyword match
        for kw in keywords:
            if term == kw:
                score += 3.0
            elif term in kw:
                score += 1.5

        # Description match
        if term in desc:
            score += 1.0

        # Author match
        if term in author:
            score += 0.5

    return score


# ---------------------------------------------------------------------------
# Local catalog management (for self-hosted / dev)
# ---------------------------------------------------------------------------

def add_local_entry(entry: dict) -> None:
    """Add a package entry to the local catalog (for testing or self-hosting)."""
    global _cached_catalog, _cached_at

    catalog = get_catalog()
    # Remove existing entry with same ID
    catalog = [p for p in catalog if p.get("id") != entry.get("id")]
    catalog.append(entry)

    _cached_catalog = catalog
    _cached_at = time.time()
    _save_cache(catalog)


def remove_local_entry(package_id: str) -> None:
    """Remove a package entry from the local catalog."""
    global _cached_catalog, _cached_at

    catalog = get_catalog()
    catalog = [p for p in catalog if p.get("id") != package_id]

    _cached_catalog = catalog
    _cached_at = time.time()
    _save_cache(catalog)
