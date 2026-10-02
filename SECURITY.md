# Security Policy

RAPR AI runs AI CLIs and shell commands on your machine, so please treat security
issues seriously and report them privately.

## Reporting a vulnerability

Open a [private security advisory](../../security/advisories/new) on this repository
instead of a public issue. Include steps to reproduce and the impact you observed.
You should get a first response within a week.

## Secrets

- Never commit `.env`, `.vault_key`, `credentials.json`, `helmhq.db*` or `chat_logs/`.
  They are listed in `.gitignore`.
- No OAuth client IDs or secrets are bundled. Cloud backup and plugin integrations
  read credentials from environment variables (see `.env.example`) or the encrypted
  token vault configured in the Settings UI.
