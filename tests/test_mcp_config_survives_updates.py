"""Your MCP servers and switches outlive an update.

They used to be written into the app folder's mcp_servers.json, which an update
replaces (and the bundled app unpacks fresh every start): servers installed from
the marketplace, and servers you switched on, quietly went away.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

import helm.paths as paths
from helm.mcp import config


SHIPPED = {"zapier": {"type": "subprocess", "command": "npx -y mcp-remote x", "enabled": False}}


@pytest.fixture
def folders(tmp_path, monkeypatch):
    app, data = tmp_path / "app", tmp_path / "data"
    app.mkdir()
    data.mkdir()
    (app / "mcp_servers.json").write_text(json.dumps(SHIPPED))
    monkeypatch.setattr(paths, "PROJECT_ROOT", app)
    monkeypatch.setenv("RAPR_DATA_DIR", str(data))
    return app, data


def _update_the_app(app):
    (app / "mcp_servers.json").write_text(json.dumps(SHIPPED))


def test_a_switch_you_turn_on_stays_on_after_an_update(folders):
    app, data = folders
    cfg = config.load_config()
    cfg["zapier"]["enabled"] = True
    config.save_config(cfg)
    assert json.loads((app / "mcp_servers.json").read_text()) == SHIPPED   # app folder untouched
    _update_the_app(app)
    assert config.load_config()["zapier"]["enabled"] is True


def test_an_installed_server_stays_after_an_update(folders):
    app, _ = folders
    mine = config.read_user_raw()
    mine["notes"] = {"command": "notes-mcp", "enabled": True}
    config.write_user_raw(mine)
    _update_the_app(app)
    loaded = config.load_config()
    assert "notes" in loaded and "zapier" in loaded


def test_a_server_installed_before_this_change_can_still_be_removed(folders):
    app, _ = folders
    legacy = {**SHIPPED, "old-pkg": {"command": "old-mcp", "enabled": True}}
    (app / "mcp_servers.json").write_text(json.dumps(legacy))
    from helm.packages.mcp_installer import uninstall_mcp
    uninstall_mcp("old-pkg")
    assert "old-pkg" not in config.load_config()
