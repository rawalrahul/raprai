"""The registry manifest (.codex-plugin/plugin.json) must track the app version."""

import json
import os

from helm.version import APP_VERSION

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_manifest_version_matches_app_version():
    with open(os.path.join(ROOT, ".codex-plugin", "plugin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["version"] == APP_VERSION
