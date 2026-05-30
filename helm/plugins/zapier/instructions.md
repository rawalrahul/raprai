# Zapier — RETIRED (NLA) → now Zapier MCP

This legacy plugin used Zapier's **NLA API** (`nla.zapier.com`), which Zapier
**shut down in 2023**. It is disabled (`manifest.json.disabled`) and must NOT be
re-enabled.

Zapier is now a **Tier-2 universal connector** wired in as core MCP
infrastructure, not a prompt-injection plugin:

- Connector: `helm/mcp/zapier_mcp.py`
- Transport: hosted Zapier MCP endpoint bridged via `npx -y mcp-remote <url>`
- Connect UI: `GET /mcp/zapier/connect` (user pastes their mcp.zapier.com server URL)
- The per-user URL is stored encrypted in the token vault (`ZAPIER_MCP_URL`)
  and registered as the `zapier` server in `mcp_servers.json`.

Once connected, Zapier tools appear automatically as `zapier_*` MCP tools for
every AI runner (Claude / Gemini / Codex / Ollama). No Python/NLA code path.
