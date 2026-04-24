import os
import sys


def test_custom_command_supports_python_placeholder_and_model():
    from helm.integrations import _build_command_fn

    build = _build_command_fn(
        "{python} -m helm.ai_runner._openai_compat_cli --base-url http://localhost:1234/v1 --model {model}",
        stdin_prompt=True,
    )

    cmd = build("ignored prompt", model="local-model")
    assert cmd[0] == sys.executable
    assert "{python}" not in cmd
    assert "ignored prompt" not in cmd
    assert "local-model" in cmd


def test_openai_compat_cli_reads_api_key_from_env(monkeypatch):
    from helm.ai_runner import _openai_compat_cli

    monkeypatch.setenv("CUSTOM_AI_TEST_API_KEY", "secret-token")
    args = [
        "--base-url", "http://localhost:1234/v1",
        "--model", "test-model",
        "--api-key-env", "CUSTOM_AI_TEST_API_KEY",
    ]

    def arg(flag, default=""):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return default

    api_key = arg("--api-key")
    api_key_env = arg("--api-key-env")
    if not api_key and api_key_env:
        api_key = os.environ.get(api_key_env, "").strip()

    assert api_key == "secret-token"


def test_frontend2_has_openai_compatible_helper():
    from pathlib import Path

    js = Path("frontend2/js/custom_ai.js").read_text(encoding="utf-8")
    assert "function addOpenAICompatIntegration()" in js
    assert "--api-key-env" in js
    assert "--api-key', apiKey" not in js


def test_provider_settings_are_user_configurable():
    from pathlib import Path

    from helm.security import VAULT_ELIGIBLE_KEYS
    from helm.web_routes.app import _SETTINGS_KEYS

    assert "GROQ_API_KEY" in VAULT_ELIGIBLE_KEYS
    assert "OPENROUTER_API_KEY" in VAULT_ELIGIBLE_KEYS
    assert "LOCAL_AI_URL" in _SETTINGS_KEYS
    assert "LOCAL_AI_MODEL" in _SETTINGS_KEYS

    html = Path("frontend2/index.html").read_text(encoding="utf-8")
    js = Path("frontend2/js/complete.js").read_text(encoding="utf-8")
    assert "st-GROQ_API_KEY" in html
    assert "st-OPENROUTER_API_KEY" in html
    assert "st-LOCAL_AI_URL" in html
    assert "settings/api-keys" in js


def test_builtin_api_integrations_use_env_key_reference(monkeypatch):
    import integrations.groq as groq
    import integrations.openrouter as openrouter

    monkeypatch.setenv("GROQ_API_KEY", "secret-groq")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret-openrouter")

    groq_cmd = groq.build_command("prompt")
    openrouter_cmd = openrouter.build_command("prompt")

    assert "--api-key-env" in groq_cmd
    assert "GROQ_API_KEY" in groq_cmd
    assert "secret-groq" not in groq_cmd
    assert "--api-key-env" in openrouter_cmd
    assert "OPENROUTER_API_KEY" in openrouter_cmd
    assert "secret-openrouter" not in openrouter_cmd
