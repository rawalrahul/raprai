// What the RAPR MCP server writes to ~/.config/rapr/mcp-usage.json (helm/mcp_usage.py).
export type AgentUsage = { name: string; calls: number; failed: number; seconds: number; tokens: number }

export type Bucket = {
  calls: number
  failed: number
  seconds: number
  tokens: number
  agents: { [agent: string]: AgentUsage }
}

export type Usage = {
  version: number
  day: string
  updated: number
  today: Bucket
  total: Bucket
  last: { agent: string; name: string; seconds: number; tokens: number; ok: boolean; at: number } | null
}

export type View = { usage: Usage | null; details: boolean }

declare module 'claude-code' {
  interface PluginState {
    'rapr-usage': { view: View }
  }
}
