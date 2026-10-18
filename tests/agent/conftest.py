import pytest


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path, monkeypatch):
    """Workflow runs save each step's output in their folder, which defaults to
    the current one or RAPR's last folder; keep that out of the repo."""
    import helm.state as _st
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_st, "last_cwd", str(tmp_path), raising=False)
