"""Update check for source installs: install record, GitHub comparison, Update now."""
import json

import pytest

import helm.paths
import helm.updater as u


class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _commit(sha, title, parents=1):
    return {"sha": sha, "parents": [{}] * parents,
            "commit": {"message": title + "\n\nbody", "committer": {"date": "2026-10-16T17:00:00Z"}}}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(helm.paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(helm.paths, "user_data_dir", lambda: tmp_path / "data")
    (tmp_path / "data").mkdir()
    monkeypatch.setenv("RAPR_INSTALL_KIND", "source-windows")
    monkeypatch.delenv("RAPR_REF", raising=False)
    monkeypatch.delenv("RAPR_COMMIT", raising=False)
    return tmp_path


def test_install_record_written_by_powershell_with_a_bom(root):
    (root / ".rapr-install.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"kind": "source-windows", "ref": "main", "commit": "abc123"}).encode())
    info = u.install_info()
    assert info["commit"] == "abc123" and info["ref"] == "main" and info["self_update"]


def test_compare_lists_new_changes_newest_first_without_merges(root, monkeypatch):
    (root / ".rapr-install.json").write_text(json.dumps({"ref": "main", "commit": "old"}))
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        return _Resp({"ahead_by": 3, "commits": [
            _commit("c1", "First change"), _commit("m1", "Merge pull request #1", parents=2), _commit("c2", "Second change")]})

    monkeypatch.setattr("requests.get", fake_get)
    r = u._check_source_update(u.install_info())
    assert seen[0].endswith("/compare/old...main")
    assert r["update_available"] is True and r["behind_by"] == 3 and r["latest_commit"] == "c2"
    assert [c["title"] for c in r["changes"]] == ["Second change", "First change"]


def test_up_to_date_and_unknown_commit(root, monkeypatch):
    monkeypatch.setattr("requests.get", lambda url, **kw: _Resp({"ahead_by": 0, "commits": []}))
    (root / ".rapr-install.json").write_text(json.dumps({"ref": "main", "commit": "tip"}))
    assert u._check_source_update(u.install_info())["update_available"] is False

    (root / ".rapr-install.json").unlink()
    monkeypatch.setattr("requests.get", lambda url, **kw: _Resp({"sha": "tip", "commit": {"committer": {"date": "2026-10-16"}}}))
    r = u._check_source_update(u.install_info())
    assert r["update_available"] is None and r["latest_commit"] == "tip"


def test_update_now_only_for_source_installs_and_safe_branch_names(root, monkeypatch):
    spawned = []
    monkeypatch.setattr(u.subprocess, "Popen", lambda *a, **k: spawned.append(a[0]))
    assert u.start_source_update()["ok"] and spawned[-1][:2] == ["cmd.exe", "/c"]
    assert (root / "data" / "logs" / "update-from-ui.ps1").read_bytes().startswith(b"\xef\xbb\xbf")
    assert u.take_quiet_start() is True and u.take_quiet_start() is False

    monkeypatch.setenv("RAPR_INSTALL_KIND", "docker")
    assert not u.start_source_update()["ok"]

    monkeypatch.setenv("RAPR_INSTALL_KIND", "source-mac")
    monkeypatch.setenv("RAPR_REF", "main; rm -rf ~")
    assert not u.start_source_update()["ok"]


def test_no_install_record_is_a_checkout_even_when_bundled(root, monkeypatch):
    monkeypatch.delenv("RAPR_INSTALL_KIND")
    monkeypatch.setattr(helm.paths, "is_bundled", lambda: True)
    info = u.install_info()
    assert info["kind"] == "dev" and info["self_update"] is False


def test_exe_download_routes_are_gone():
    from helm.web_routes.update_routes import router
    paths = {r.path for r in router.routes}
    assert "/update/download" not in paths and "/update/apply" not in paths
    assert "/update/now" in paths
