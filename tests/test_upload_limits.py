"""Uploads: an oversized file is refused without being read whole, and a
package upload can't choose where it's written."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

from helm import security


class _File:
    def __init__(self, size):
        self.size, self.asked = size, None

    async def read(self, n=-1):
        self.asked = n
        return b"x" * (self.size if n < 0 else min(n, self.size))


def test_validate_upload_enforces_the_allowlist():
    # Known-safe extensions pass (including code files the app never serves).
    for name in ("notes.txt", "script.py", "page.html", "app.js", "icon.svg"):
        assert security.validate_upload(name, 10) is None, name
    # Dangerous executables are blocked with a clear message.
    for name in ("virus.exe", "x.dll", "run.scr", "setup.msi"):
        assert security.validate_upload(name, 10) is not None, name
    # Anything not on the allowlist is refused, even if it isn't a known-dangerous type.
    for name in ("data.foobar", "payload.php", "shell.jsp", "README"):
        assert security.validate_upload(name, 10) is not None, name


def test_validate_upload_rejects_path_traversal():
    for name in ("../../etc/passwd", "a/b.txt", "a\\b.txt"):
        assert security.validate_upload(name, 10) is not None, name


def test_an_oversized_upload_is_refused_after_one_byte_past_the_limit():
    big = _File(10_000)
    assert asyncio.run(security.read_upload(big, limit=100)) is None
    assert big.asked == 101
    assert asyncio.run(security.read_upload(_File(100), limit=100)) == b"x" * 100


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PIN_SALT", raising=False)
    monkeypatch.delenv("PIN_HASH", raising=False)
    from helm.web_routes import app as webapp
    c = TestClient(webapp)
    c.get("/health")
    if c.cookies.get("hq_csrf"):
        c.headers["X-CSRF-Token"] = c.cookies.get("hq_csrf")
    return c


def test_upload_route_answers_413_when_too_big(client, monkeypatch):
    monkeypatch.setattr(security, "MAX_UPLOAD_SIZE", 10)
    real = security.read_upload
    monkeypatch.setattr(security, "read_upload", lambda f, limit=10: real(f, limit))
    r = client.post("/upload", files={"file": ("a.txt", b"x" * 50)})
    assert r.status_code == 413


def test_a_package_upload_cant_pick_its_folder(client, monkeypatch):
    saved = []
    import helm.packages.installer as installer
    monkeypatch.setattr(installer, "install_package",
                        lambda path, force=False: saved.append(path) or {"ok": True})
    r = client.post("/packages/install/upload",
                    files={"file": ("../../escaped.raprpkg", b"PK")})
    assert r.status_code == 200, r.text
    assert saved and saved[0].name == "escaped.raprpkg"
    assert saved[0].parent.name.startswith("packages_upload_")
