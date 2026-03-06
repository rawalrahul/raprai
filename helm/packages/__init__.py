"""
helm/packages — Universal package format for RAPR AI marketplace.

A .raprpkg file is a ZIP archive containing:
  - manifest.json  (required — metadata + install instructions)
  - content files   (type-specific: SKILL.md, instructions.md, server code, etc.)

Supports three package types:
  - MCP servers  (merged into mcp_servers.json, hot-started)
  - Skills       (copied to .skills/skills/, hot-loaded)
  - Plugins      (copied to helm/plugins/, hot-loaded)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORMAT_VERSION = "1.0"
RAPRPKG_EXTENSION = ".raprpkg"

# Backward compat alias
HELMPACK_EXTENSION = RAPRPKG_EXTENSION

# ---------------------------------------------------------------------------
# Package type enum
# ---------------------------------------------------------------------------


class PackageType(str, Enum):
    MCP = "mcp"
    SKILL = "skill"
    PLUGIN = "plugin"


# ---------------------------------------------------------------------------
# Manifest dataclass
# ---------------------------------------------------------------------------


@dataclass
class RaprPackageManifest:
    """Parsed manifest.json from a .raprpkg file."""
    format_version: str
    type: PackageType
    id: str
    name: str
    description: str
    version: str
    author: str = ""
    keywords: list[str] = field(default_factory=list)
    min_app_version: str = ""
    icon: str = ""  # relative path to icon file in ZIP

    # Type-specific config (only one will be populated)
    mcp: Optional[dict] = None       # {"command": [...], "env": {...}}
    skill: Optional[dict] = None     # {"category": "...", "for_ai": [...]}
    plugin: Optional[dict] = None    # {"emoji": "...", "auth": {...}}

    # Integrity (populated after validation)
    package_hash: str = ""           # SHA256 of entire ZIP


# Backward compat alias
HelmPackManifest = RaprPackageManifest


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RaprPackageError(Exception):
    """Base exception for RAPR Package operations."""
    pass


# Backward compat alias
HelmPackError = RaprPackageError


class ManifestError(RaprPackageError):
    """Invalid or missing manifest."""
    pass


class ValidationError(RaprPackageError):
    """Package validation failed."""
    pass


class InstallError(RaprPackageError):
    """Installation failed."""
    pass


class ConflictError(RaprPackageError):
    """Package already installed (and force=False)."""
    pass
