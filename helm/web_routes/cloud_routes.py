"""helm/web_routes/cloud_routes.py — "Use my server": deploy RAPR to a server you own."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm.cloud import deploy as dep
from helm.cloud import plan
from helm.cloud.ssh import ParamikoRunner, Runner

router = APIRouter()
_jobs: dict[str, dep.Job] = {}


class ServerBody(BaseModel):
    host: str
    user: str = "ubuntu"
    port: int = 22
    name: str = "rapr"
    password: str = ""
    private_key: str = ""


class DeployBody(ServerBody):
    pin: str
    copy_settings: list[str] = []


class ActionBody(ServerBody):
    what: str   # update | restart | logs | remove | status


def _connector(b: ServerBody):
    return lambda: ParamikoRunner(b.host, b.user, b.port, password=b.password, private_key=b.private_key)


def _remember(b: ServerBody, url: str = "") -> None:
    """Keep the server's address (never the password or key) so the screen can show it."""
    from helm.paths import user_data_dir
    path = user_data_dir() / "cloud.json"
    data = {"host": b.host, "user": b.user, "port": b.port, "name": b.name, "url": url}
    try:
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _saved() -> dict:
    from helm.paths import user_data_dir
    try:
        return json.loads((user_data_dir() / "cloud.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/api/cloud")
async def cloud_state():
    return JSONResponse({"server": _saved()})


@router.post("/api/cloud/deploy")
async def start_deploy(body: DeployBody):
    from helm import auth
    if not body.pin or len(body.pin) < 4:
        return JSONResponse({"error": "choose a PIN of at least 4 characters for the server"}, status_code=400)
    salt, pin_hash = auth.set_pin(body.pin)
    local_env = {k: os.environ.get(k, "") for k in plan.COPYABLE}
    opts = plan.CloudOptions(host=body.host, user=body.user, port=body.port, name=body.name,
                             pin_salt=salt, pin_hash=pin_hash,
                             copy_settings=body.copy_settings, local_env=local_env)
    job = dep.Job(id=uuid.uuid4().hex[:10], name=body.name)
    _jobs[job.id] = job
    _remember(body)

    def work():
        dep.deploy(job, opts, _connector(body))
        if job.url:
            _remember(body, job.url)
    threading.Thread(target=work, daemon=True, name=f"cloud-deploy-{job.id}").start()
    return JSONResponse(job.as_dict())


@router.get("/api/cloud/job/{job_id}")
async def job(job_id: str):
    j = _jobs.get(job_id)
    if not j:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(j.as_dict())


@router.post("/api/cloud/action")
async def server_action(body: ActionBody):
    def work() -> dict:
        r: Runner = _connector(body)()
        try:
            if body.what == "status":
                return dep.status(r, body.name, body.user)
            return {"output": dep.action(r, body.name, body.user, body.what)}
        finally:
            r.close()
    try:
        result = await asyncio.to_thread(work)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": f"could not reach the server: {exc}"}, status_code=502)
    if body.what == "remove":
        _remember(body)
    return JSONResponse(result)
