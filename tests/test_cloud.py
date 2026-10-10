"""Cloud mode: plan, deploy steps and day-2 actions, against a scripted server."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.cloud import deploy as dep
from helm.cloud import plan
from helm.cloud.ssh import FakeRunner

GOOD_HOST = {
    "uname -s": (0, "Linux\nubuntu\n", ""),
    "awk '/MemTotal/": (0, "3900\n", ""),
    "df -BG": (0, "30\n", ""),
    "docker --version": (0, "Docker version 27\n", ""),
    "docker compose version": (0, "v2\n", ""),
    "docker-compose.yml exec": (0, "{}", ""),
    "docker-compose.yml logs tunnel": (0, "https://quiet-river-1234.trycloudflare.com\n", ""),
}


def opts(**kw):
    base = dict(host="203.0.113.7", user="ubuntu", name="rapr", pin_salt="s", pin_hash="h",
                copy_settings=["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "BOGUS"],
                local_env={"GEMINI_API_KEY": "g-1", "TELEGRAM_BOT_TOKEN": "t-1", "BOGUS": "x", "OTHER": "no"})
    base.update(kw)
    return plan.CloudOptions(**base)


def run_deploy(answers=None, o=None):
    r = FakeRunner({**GOOD_HOST, **(answers or {})})
    job = dep.Job(id="j1", name="rapr")
    dep.deploy(job, o or opts(), lambda: r, sleep=lambda s: None)
    return job, r


def test_happy_path_deploys_and_reports_the_address():
    job, r = run_deploy()
    assert job.status == "done", job.error
    assert job.url == "https://quiet-river-1234.trycloudflare.com"
    assert any("up -d --pull missing" in c for c in r.commands)
    assert r.files["/tmp/rapr-rapr.env"][1] == 0o600          # settings: owner-only
    assert any("mv /tmp/rapr-rapr.env /opt/rapr/rapr/rapr.env" in c for c in r.commands)


def test_only_chosen_and_allowed_settings_are_copied():
    env = plan.server_env(opts())
    assert "GEMINI_API_KEY=g-1" in env and "TELEGRAM_BOT_TOKEN=t-1" in env
    assert "BOGUS" not in env and "OTHER" not in env
    assert "PIN_HASH=h" in env and "RAPR_HEADLESS=1" in env


def test_compose_uses_tunnel_and_keeps_rapr_private():
    text = plan.compose_file(opts())
    assert "cloudflare/cloudflared" in text and "http://rapr:8000" in text
    assert "ports:" not in text          # RAPR is not published to the internet


def test_non_linux_server_stops_early():
    job, r = run_deploy({"uname -s": (0, "FreeBSD\n", "")})
    assert job.status == "failed" and "isn't Linux" in job.error
    assert not any("compose up" in c for c in r.commands)


def test_low_memory_is_explained():
    job, _ = run_deploy({"awk '/MemTotal/": (0, "512\n", "")})
    assert job.status == "failed" and "1 GB" in job.error


def test_docker_is_installed_when_missing():
    job, r = run_deploy({"docker --version": (127, "", "not found")})
    assert job.status == "done"
    assert any("get.docker.com" in c for c in r.commands)


def test_non_root_user_uses_sudo_and_never_cds_into_the_private_folder():
    job, r = run_deploy(o=opts(user="ubuntu"))
    assert any(c.startswith("sudo -n docker compose --project-directory /opt/rapr/rapr") for c in r.commands)
    assert not any(c.startswith("cd /opt/rapr") for c in r.commands)   # the folder is root-only


def test_root_does_not_use_sudo():
    job, r = run_deploy(o=opts(user="root"))
    assert not any("sudo" in c for c in r.commands)


def test_unhealthy_rapr_reports_logs_hint():
    job, _ = run_deploy({"docker-compose.yml exec": (1, "", "refused")})
    assert job.status == "failed" and "View logs" in job.error


def test_bad_details_are_refused_before_connecting():
    job = dep.Job(id="j", name="x")
    dep.deploy(job, opts(host="bad host!"), lambda: FakeRunner(), sleep=lambda s: None)
    assert job.status == "failed" and "IP address" in job.error


def test_pin_is_required():
    with pytest.raises(ValueError, match="PIN"):
        plan.validate(opts(pin_salt="", pin_hash=""))


def test_connect_failure_is_explained():
    def boom():
        raise OSError("timed out")
    job = dep.Job(id="j", name="x")
    dep.deploy(job, opts(), boom, sleep=lambda s: None)
    assert job.status == "failed" and "could not connect" in job.error


def test_day_two_actions():
    r = FakeRunner({"docker-compose.yml ps": (0, "rapr running Up 2 hours\n", ""),
                    "docker-compose.yml logs tunnel": (0, "https://a-b-c.trycloudflare.com", "")})
    st = dep.status(r, "rapr", "ubuntu")
    assert st["containers"] == ["rapr running Up 2 hours"] and st["url"].endswith("trycloudflare.com")
    dep.action(r, "rapr", "ubuntu", "update")
    assert any("docker-compose.yml pull" in c for c in r.commands)
    with pytest.raises(ValueError):
        dep.action(r, "rapr", "ubuntu", "explode")
    dep.action(r, "rapr", "ubuntu", "remove")
    assert any("rm -rf /opt/rapr/rapr" in c for c in r.commands)


def test_dockerfile_and_requirements_are_headless():
    root = os.path.join(os.path.dirname(__file__), '..')
    df = open(os.path.join(root, "Dockerfile")).read()
    assert "RAPR_HEADLESS=1" in df and "/data" in df and "/health" in df
    req = open(os.path.join(root, "requirements-server.txt")).read().lower()
    for windows_only in ("pystray", "pywin32", "pywinauto", "comtypes"):
        assert windows_only not in req


def test_settings_file_is_mounted_where_the_app_reads_it():
    text = plan.compose_file(opts())
    assert "./rapr.env:/data/.env" in text   # without this the app shows its setup wizard
    assert "env_file" not in text           # Compose would mangle the "$" in the PIN hash
    assert "RAPR_DATA_DIR=/data" in plan.server_env(opts())


def test_tunnel_address_skips_cloudflare_api_and_takes_newest():
    logs = ('failed to request quick Tunnel: Post "https://api.trycloudflare.com/tunnel"\n'
            "https://old-one.trycloudflare.com\nhttps://new-one.trycloudflare.com\n")
    r = FakeRunner({"docker-compose.yml logs tunnel": (0, logs, "")})
    assert dep.find_url(r, "/opt/rapr/rapr", "") == "https://new-one.trycloudflare.com"
    r = FakeRunner({"docker-compose.yml logs tunnel": (0, 'Post "https://api.trycloudflare.com/tunnel"', "")})
    assert dep.find_url(r, "/opt/rapr/rapr", "") == ""


def test_server_files_writes_same_setup_as_the_app(tmp_path, monkeypatch):
    """scripts/install-server.sh: settings and compose file made on the server itself."""
    from helm import auth
    from helm.cloud import server_files
    server_files.write(tmp_path, "rapr", "4321")
    env = (tmp_path / "rapr.env").read_text()
    assert oct((tmp_path / "rapr.env").stat().st_mode & 0o777) == "0o600"
    assert "4321" not in env and "RAPR_HEADLESS=1" in env
    vals = dict(l.split("=", 1) for l in env.splitlines() if "=" in l and not l.startswith("#"))
    monkeypatch.setenv("PIN_SALT", vals["PIN_SALT"])
    monkeypatch.setenv("PIN_HASH", vals["PIN_HASH"])
    assert auth.verify_pin("4321") and not auth.verify_pin("0000")
    assert (tmp_path / "docker-compose.yml").read_text() == plan.compose_file(
        plan.CloudOptions(host="localhost", name="rapr", pin_salt="x", pin_hash="y"))
    with pytest.raises(ValueError):
        server_files.write(tmp_path, "rapr", "12")
