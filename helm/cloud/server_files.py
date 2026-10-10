"""
helm/cloud/server_files.py — Write a server's settings and compose file, on the server.

Used by scripts/install-server.sh (setting RAPR up from the server itself, with
no laptop). It runs inside the RAPR image, so the files are exactly the ones
the app's "Use my server" writes:

    docker run --rm -i --user 0 -v /opt/rapr/rapr:/out ghcr.io/rawalrahul/raprai \
        python -m helm.cloud.server_files rapr < pin

The PIN is read from stdin (never from the command line, where other users
could see it), hashed, and only the hash is written.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from helm import auth
from helm.cloud import plan


def write(out: Path, name: str, pin: str) -> None:
    if len(pin) < 4:
        raise ValueError("the PIN must be at least 4 characters")
    salt, pin_hash = auth.set_pin(pin)
    opts = plan.CloudOptions(host="localhost", name=name, pin_salt=salt, pin_hash=pin_hash)
    plan.validate(opts)
    env = out / "rapr.env"
    env.write_text(plan.server_env(opts), encoding="utf-8")
    os.chmod(env, 0o600)
    (out / "docker-compose.yml").write_text(plan.compose_file(opts), encoding="utf-8")
    if os.geteuid() == 0:
        os.chown(env, plan.CONTAINER_UID, plan.CONTAINER_UID)


def main(argv: list[str]) -> int:
    name = argv[1] if len(argv) > 1 else "rapr"
    pin = sys.stdin.readline().strip()
    try:
        write(Path(os.environ.get("RAPR_OUT", "/out")), name, pin)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
