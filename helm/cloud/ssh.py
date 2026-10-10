"""SSH to your server: run commands and copy files. Real (paramiko) and fake (tests)."""

from __future__ import annotations

from typing import Optional, Protocol


class Runner(Protocol):
    def run(self, cmd: str, timeout: int = 600) -> tuple[int, str, str]: ...
    def put(self, path: str, content: str, mode: int = 0o644) -> None: ...
    def close(self) -> None: ...


class ParamikoRunner:
    """Connects with a password or a private key that you paste in."""

    def __init__(self, host: str, user: str, port: int = 22, password: str = "",
                 private_key: str = "", timeout: int = 20):
        import io
        import paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = dict(hostname=host, port=port, username=user, timeout=timeout,
                      look_for_keys=False, allow_agent=False)
        if private_key.strip():
            key = None
            for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
                try:
                    key = cls.from_private_key(io.StringIO(private_key), password or None)
                    break
                except Exception:
                    continue
            if key is None:
                raise ValueError("that private key can't be read (paste the whole key, OpenSSH format)")
            kwargs["pkey"] = key
        else:
            kwargs["password"] = password
        self.client.connect(**kwargs)

    def run(self, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
        _, out, err = self.client.exec_command(cmd, timeout=timeout)
        code = out.channel.recv_exit_status()
        return code, out.read().decode(errors="replace"), err.read().decode(errors="replace")

    def put(self, path: str, content: str, mode: int = 0o644) -> None:
        sftp = self.client.open_sftp()
        try:
            with sftp.open(path, "w") as f:
                f.write(content)
            sftp.chmod(path, mode)
        finally:
            sftp.close()

    def close(self) -> None:
        self.client.close()


class FakeRunner:
    """Scripted server for tests: answers commands from a table, records everything."""

    def __init__(self, answers: Optional[dict[str, tuple[int, str, str]]] = None):
        self.answers = answers or {}
        self.commands: list[str] = []
        self.files: dict[str, tuple[str, int]] = {}

    def run(self, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
        self.commands.append(cmd)
        for needle, answer in self.answers.items():
            if needle in cmd:
                return answer
        return 0, "", ""

    def put(self, path: str, content: str, mode: int = 0o644) -> None:
        self.files[path] = (content, mode)

    def close(self) -> None:
        pass
