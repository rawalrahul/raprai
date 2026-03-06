"""
helm/helmpack/package.py — HelmPackage class for reading and validating .helmpack files.
"""

import hashlib
import json
import pathlib
import re
import shutil
import tempfile
import zipfile
from typing import Optional

from helm.helmpack import (
    FORMAT_VERSION, HelmPackManifest, ManifestError, PackageType, ValidationError,
)

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+")


def _validate_common(m: dict) -> list[str]:
    """Validate fields common to all package types."""
    errors = []
    if "format_version" not in m:
        errors.append("Missing 'format_version'")
    if "type" not in m:
        errors.append("Missing 'type'")
    elif m["type"] not in ("mcp", "skill", "plugin"):
        errors.append(f"Invalid type: {m['type']} (must be mcp/skill/plugin)")
    if "id" not in m or not m["id"]:
        errors.append("Missing 'id'")
    elif not _ID_RE.match(m["id"]):
        errors.append(f"Invalid id '{m['id']}' — must be lowercase alphanumeric with hyphens/underscores, 2-64 chars")
    if "name" not in m or not m["name"]:
        errors.append("Missing 'name'")
    if "version" not in m or not m["version"]:
        errors.append("Missing 'version'")
    elif not _VERSION_RE.match(m["version"]):
        errors.append(f"Invalid version '{m['version']}' — must be semver (e.g., 1.0.0)")
    return errors


def _validate_mcp(m: dict, zip_names: list[str]) -> list[str]:
    """Validate MCP-specific fields."""
    errors = []
    mcp = m.get("mcp", {})
    if not mcp:
        errors.append("MCP package must have a 'mcp' section in manifest")
        return errors
    cmd = mcp.get("command")
    if not cmd:
        errors.append("MCP manifest missing 'mcp.command'")
    elif isinstance(cmd, str):
        pass  # Will be split later
    elif not isinstance(cmd, list) or not all(isinstance(c, str) for c in cmd):
        errors.append("'mcp.command' must be a string or list of strings")
    env = mcp.get("env", {})
    if env and not isinstance(env, dict):
        errors.append("'mcp.env' must be a dict")
    return errors


def _validate_skill(m: dict, zip_names: list[str]) -> list[str]:
    """Validate skill-specific fields."""
    errors = []
    # Must contain SKILL.md
    has_skill_md = any(
        n.endswith("SKILL.md") or n.endswith("skill.md")
        for n in zip_names
    )
    if not has_skill_md:
        errors.append("Skill package must contain a SKILL.md file")
    return errors


def _validate_plugin(m: dict, zip_names: list[str]) -> list[str]:
    """Validate plugin-specific fields."""
    errors = []
    # Must contain instructions.md (optional but recommended)
    has_instructions = any(
        n.endswith("instructions.md") for n in zip_names
    )
    if not has_instructions:
        # Not an error — just a warning level issue
        pass
    return errors


# ---------------------------------------------------------------------------
# HelmPackage
# ---------------------------------------------------------------------------


class HelmPackage:
    """
    Represents a .helmpack ZIP file.

    Usage:
        pkg = HelmPackage("my-tool.helmpack")
        errors = pkg.validate()
        if not errors:
            pkg.extract_to(dest_dir)
    """

    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        self._manifest: Optional[dict] = None
        self._parsed: Optional[HelmPackManifest] = None
        self._zip_names: Optional[list[str]] = None

    @property
    def manifest_raw(self) -> dict:
        """Lazy-load manifest.json from ZIP."""
        if self._manifest is None:
            self._manifest = self._read_manifest()
        return self._manifest

    @property
    def manifest(self) -> HelmPackManifest:
        """Parsed manifest as a dataclass."""
        if self._parsed is None:
            m = self.manifest_raw
            self._parsed = HelmPackManifest(
                format_version=m.get("format_version", ""),
                type=PackageType(m.get("type", "plugin")),
                id=m.get("id", ""),
                name=m.get("name", ""),
                description=m.get("description", ""),
                version=m.get("version", ""),
                author=m.get("author", ""),
                keywords=m.get("keywords", []),
                min_app_version=m.get("min_app_version", ""),
                icon=m.get("icon", ""),
                mcp=m.get("mcp"),
                skill=m.get("skill"),
                plugin=m.get("plugin"),
                package_hash=self.compute_hash(),
            )
        return self._parsed

    @property
    def package_type(self) -> PackageType:
        return self.manifest.type

    def _read_manifest(self) -> dict:
        """Read manifest.json from the ZIP."""
        if not self.path.exists():
            raise ManifestError(f"Package not found: {self.path}")
        if not zipfile.is_zipfile(str(self.path)):
            raise ManifestError(f"Not a valid ZIP file: {self.path}")

        with zipfile.ZipFile(str(self.path), "r") as zf:
            self._zip_names = zf.namelist()
            # Look for manifest.json at root level
            manifest_candidates = [
                n for n in self._zip_names
                if n == "manifest.json" or n.endswith("/manifest.json")
            ]
            if not manifest_candidates:
                raise ManifestError("Package missing manifest.json")

            # Prefer root-level manifest
            manifest_name = "manifest.json" if "manifest.json" in manifest_candidates else manifest_candidates[0]
            try:
                data = zf.read(manifest_name)
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise ManifestError(f"Invalid JSON in manifest.json: {e}")

    def _get_zip_names(self) -> list[str]:
        """Get list of file names in the ZIP."""
        if self._zip_names is None:
            with zipfile.ZipFile(str(self.path), "r") as zf:
                self._zip_names = zf.namelist()
        return self._zip_names

    def validate(self) -> list[str]:
        """
        Validate the package.

        Returns a list of error strings. Empty list = valid.
        """
        errors = []

        # Try to load manifest
        try:
            m = self.manifest_raw
        except ManifestError as e:
            return [str(e)]

        # Common validation
        errors.extend(_validate_common(m))
        if errors:
            return errors  # Can't proceed without valid base fields

        # Type-specific validation
        pkg_type = m.get("type", "")
        zip_names = self._get_zip_names()

        if pkg_type == "mcp":
            errors.extend(_validate_mcp(m, zip_names))
        elif pkg_type == "skill":
            errors.extend(_validate_skill(m, zip_names))
        elif pkg_type == "plugin":
            errors.extend(_validate_plugin(m, zip_names))

        # Check for suspicious files
        dangerous = [n for n in zip_names if n.endswith((".exe", ".dll", ".bat", ".vbs"))]
        if dangerous:
            errors.append(f"Package contains dangerous file types: {dangerous[:3]}")

        # Check total uncompressed size (max 50 MB)
        try:
            with zipfile.ZipFile(str(self.path), "r") as zf:
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > 50 * 1024 * 1024:
                    errors.append(f"Package too large ({total_size / (1024*1024):.1f} MB, max 50 MB)")
        except Exception:
            pass

        return errors

    def extract_to(self, dest_dir: pathlib.Path) -> None:
        """Extract ZIP contents to destination directory."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(str(self.path), "r") as zf:
            # Security: prevent path traversal in ZIP entries
            for member in zf.infolist():
                member_path = pathlib.Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValidationError(
                        f"Unsafe path in ZIP: {member.filename}"
                    )
            zf.extractall(str(dest_dir))

    def compute_hash(self) -> str:
        """Compute SHA256 hash of the entire ZIP file."""
        h = hashlib.sha256()
        with open(str(self.path), "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def list_files(self) -> list[str]:
        """List all files in the package."""
        return self._get_zip_names()
