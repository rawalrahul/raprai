"""
helm/version.py — Single source of truth for the RAPR AI app version.

Every module that needs the current version imports from here:
    from helm.version import APP_VERSION

Update ONLY this file when preparing a new release.
build.bat, installer.iss, and marketplace all reference this value
at build/runtime rather than hardcoding their own strings.
"""

APP_VERSION = "2.0.0"
