"""
helm/cloud/deploy.py — "Use my server": set up RAPR on your own server, step by step.

Steps (each one logs what it did; a failure stops with the line to fix):
  1. connect and check the server (Linux, memory, disk)
  2. install Docker if it's missing
  3. write the settings and compose file, locked to your user
  4. pull the RAPR and tunnel images and start them
  5. wait for RAPR's health check, then find its public address

Works with any Linux server you can SSH into. Day-to-day: status, update
(pull the newest image), restart, logs, and remove.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from helm.cloud import plan
from helm.cloud.ssh import Runner

HEALTH_ATTEMPTS = 30     # every 5 seconds: about 2.5 minutes


@dataclass
class Job:
    id: str
    name: str
    status: str = "running"        # running | done | failed
    steps: list[dict] = field(default_factory=list)
    url: str = ""
    error: str = ""

    def log(self, step: str, state: str = "ok", detail: str = "") -> None:
        self.steps.append({"step": step, "state": state, "detail": detail[-600:]})

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status, "steps": self.steps,
                "url": self.url, "error": self.error}


def _sudo(runner: Runner, user: str) -> str:
    return "" if user == "root" else "sudo -n "


def deploy(job: Job, opts: plan.CloudOptions, connect: Callable[[], Runner],
           sleep: Callable[[float], None] = time.sleep) -> Job:
    """Run every step. Returns the job (status done or failed)."""
    try:
        plan.validate(opts)
    except ValueError as exc:
        job.log("check the details", "fail", str(exc))
        job.status, job.error = "failed", str(exc)
        return job

    try:
        runner = connect()
    except Exception as exc:
        job.log("connect to the server", "fail", f"{exc}. Check the address, port, user and key or password.")
        job.status, job.error = "failed", "could not connect"
        return job
    job.log("connect to the server")

    try:
        _run_steps(job, opts, runner, sleep)
    except _Stop:
        pass
    except Exception as exc:
        job.log("unexpected problem", "fail", str(exc))
        job.status, job.error = "failed", str(exc)
    finally:
        runner.close()
    return job


class _Stop(Exception):
    pass


def _check(job: Job, step: str, ok: bool, detail: str = "") -> None:
    if not ok:
        job.log(step, "fail", detail)
        job.status = "failed"
        job.error = detail or step
        raise _Stop()
    job.log(step)


def _run_steps(job: Job, opts: plan.CloudOptions, r: Runner, sleep: Callable[[float], None]) -> None:
    sudo = _sudo(r, opts.user)

    code, out, err = r.run("uname -s && . /etc/os-release && echo $ID")
    _check(job, "check the system", code == 0 and "Linux" in out,
           "This server isn't Linux. RAPR cloud setup supports Ubuntu, Debian and similar.")

    code, mem, _ = r.run("awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo")
    mem_mb = int(mem.strip() or 0)
    if mem_mb and mem_mb < 900:
        _check(job, "check memory", False,
               f"The server has {mem_mb} MB of memory. RAPR needs about 1 GB. "
               "Oracle's free server has 1 GB, so pick the bigger shape or add swap.")
    job.log("check memory", "ok", f"{mem_mb} MB")

    code, disk, _ = r.run("df -BG --output=avail / | tail -1 | tr -dc '0-9'")
    free_gb = int(disk.strip() or 0)
    _check(job, "check disk space", not disk.strip() or free_gb >= 4,
           f"Only {free_gb} GB free. RAPR and its AI tools need about 4 GB.")

    code, _, _ = r.run("docker --version")
    if code != 0:
        code, out, err = r.run(f"curl -fsSL https://get.docker.com | {sudo}sh", timeout=900)
        _check(job, "install Docker", code == 0, (err or out)[-400:])
    else:
        job.log("install Docker", "ok", "already installed")
    code, _, _ = r.run(f"{sudo}docker compose version")
    _check(job, "check Docker Compose", code == 0,
           "Docker Compose is missing. Install the docker-compose-plugin package and try again.")

    d = plan.DEFAULT_DIR + "/" + opts.name
    code, _, err = r.run(f"{sudo}mkdir -p {d} && {sudo}chmod 700 {d}")
    _check(job, "prepare the folder", code == 0, err[-300:])
    r.put(f"/tmp/rapr-{opts.name}.env", plan.server_env(opts), 0o600)
    r.put(f"/tmp/rapr-{opts.name}.yml", plan.compose_file(opts), 0o644)
    code, _, err = r.run(
        f"{sudo}mv /tmp/rapr-{opts.name}.env {d}/.env && {sudo}mv /tmp/rapr-{opts.name}.yml {d}/docker-compose.yml"
        f" && {sudo}chmod 600 {d}/.env", timeout=60)
    _check(job, "write the settings", code == 0, err[-300:])
    job.log("write the settings", "ok", "your PIN is stored as a hash only")

    code, out, err = r.run(f"cd {d} && {sudo}docker compose pull", timeout=1200)
    _check(job, "download RAPR (first time takes a few minutes)", code == 0,
           (err or out)[-400:] + " If this is the first deploy, RAPR's image may not be published yet.")
    code, out, err = r.run(f"cd {d} && {sudo}docker compose up -d", timeout=300)
    _check(job, "start RAPR", code == 0, (err or out)[-400:])

    healthy = False
    for _ in range(HEALTH_ATTEMPTS):
        code, _, _ = r.run(f"cd {d} && {sudo}docker compose exec -T rapr curl -fsS http://127.0.0.1:8000/health", timeout=30)
        if code == 0:
            healthy = True
            break
        sleep(5)
    _check(job, "wait for RAPR to start", healthy, "RAPR didn't answer its health check. Use 'View logs' to see why.")

    url = find_url(r, d, sudo)
    job.url = url
    job.log("find your address", "ok" if url else "fail",
            url or "No public address yet. Give the tunnel a minute, then press Refresh status.")
    job.status = "done"


def find_url(r: Runner, d: str, sudo: str) -> str:
    code, out, err = r.run(f"cd {d} && {sudo}docker compose logs tunnel --no-color 2>&1 | tail -200", timeout=60)
    m = plan.TUNNEL_URL.search(out + err)
    return m.group(0) if m else ""


def status(r: Runner, name: str, user: str) -> dict:
    sudo = _sudo(r, user)
    d = plan.DEFAULT_DIR + "/" + name
    _, ps, _ = r.run(f"cd {d} && {sudo}docker compose ps --format '{{{{.Service}}}} {{{{.State}}}} {{{{.Status}}}}' 2>&1", timeout=60)
    return {"containers": ps.strip().splitlines(), "url": find_url(r, d, sudo)}


def action(r: Runner, name: str, user: str, what: str) -> str:
    """update | restart | logs | remove"""
    sudo = _sudo(r, user)
    d = plan.DEFAULT_DIR + "/" + name
    commands = {
        "update": f"cd {d} && {sudo}docker compose pull && {sudo}docker compose up -d",
        "restart": f"cd {d} && {sudo}docker compose restart",
        "logs": f"cd {d} && {sudo}docker compose logs rapr --tail 120 --no-color",
        "remove": f"cd {d} && {sudo}docker compose down -v && {sudo}rm -rf {d}",
    }
    if what not in commands:
        raise ValueError("unknown action")
    _, out, err = r.run(commands[what], timeout=1200)
    return (out + err)[-4000:]
