"""/static serves the logos and nothing else.

/static needs no login (the login page shows the logo), and it used to serve
the whole app folder. Run from source, that folder also holds .env, .vault_key
and the database, so anyone who could reach RAPR could download them.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

from helm import auth


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    salt, h = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)
    (tmp_path / ".env").write_text("RAPR_HEADLESS=1\n")
    from helm.web_routes import app as webapp
    return TestClient(webapp)


@pytest.mark.parametrize("name", [
    "rapr-logo.png", "logo-watermark-dark.png", "logo-watermark-light.png",
])
def test_logos_load_without_login(client, name):
    r = client.get(f"/static/{name}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


@pytest.mark.parametrize("path", [
    # Secrets and data that sit in the app folder when run from source
    ".env", ".vault_key", "helmhq.db",
    # Files that exist in the app folder in every checkout
    "web_app.py", ".env.example", ".gitignore", "helm/auth.py", "helm/paths.py",
    # Ways around a plain name check
    "helm/%2e%2e/web_app.py", "helm/../web_app.py", "./.env",
    "frontend2/index.html",
])
def test_nothing_else_is_served(client, path):
    r = client.get(f"/static/{path}")
    assert r.status_code == 404, f"/static/{path} was served"


def test_every_static_file_the_ui_uses_is_served():
    """A new /static/<file> in the UI needs adding to PUBLIC_ASSETS, or it 404s."""
    import re
    from helm.paths import PROJECT_ROOT
    from helm.web_routes.app import PUBLIC_ASSETS
    used = set()
    for folder, pattern in (("frontend2", "*"), ("helm", "*.py")):
        for p in (PROJECT_ROOT / folder).rglob(pattern):
            if p.suffix in (".html", ".js", ".json", ".css", ".py") and p.is_file():
                text = p.read_text(encoding="utf-8", errors="ignore")
                used |= set(re.findall(r"/static/([\w.-]+\.(?:png|ico|svg|jpg|webp))", text))
    assert used, "found no /static/ references; the scan is broken"
    assert used <= PUBLIC_ASSETS, sorted(used - PUBLIC_ASSETS)
    for name in PUBLIC_ASSETS:
        assert (PROJECT_ROOT / name).is_file(), name
