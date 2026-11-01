// What the RAPR MCP server writes to ~/.config/rapr/mcp-usage.json (helm/mcp_usage.py).
export type AgentUsage = {
  name: string
  calls: number
  failed: number
  seconds: number
  tokens: number
  estimated?: number
  cost_usd?: number
}

export type Bucket = {
  calls: number
  failed: number
  seconds: number
  tokens: number
  estimated?: number
  cost_usd?: number
  agents: { [agent: string]: AgentUsage }
}

// One window of an AI's plan, as the AI itself reported it (pct 0-100, resets_at unix seconds).
export type Window = { key: string; label: string; pct: number; resets_at?: number | null }

export type Limits = { name: string; windows: Window[]; source: string; at: number }

export type Usage = {
  version: number
  day: string
  updated: number
  today: Bucket
  total: Bucket
  last: { agent: string; name: string; seconds: number; tokens: number; ok: boolean; at: number } | null
  limits?: { [agent: string]: Limits }
}

// What the band draws: the file, plus Claude Code's own figures for this session.
export type Live = { claude: Window[]; cost: number | null }

export type View = { usage: Usage | null; live: Live; details: boolean }

declare module 'claude-code' {
  interface PluginState {
    'rapr-usage': { view: Shaped<View> }
  }
}
