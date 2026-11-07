// RAPR's usage ribbon in Claude Code: a band above the prompt with
//   - on a Claude plan, its 5-hour and weekly usage exactly as Claude Code counts it
//     ($.session.usage(): the numbers of claude.ai's usage page); on an API key, which has no
//     such windows, this session's cost (/cost) instead. Never both: a plan's cost is a list
//     price nobody is billed, and an API key has no 5-hour or weekly limit,
//   - the other AIs' plan usage as they report it (Codex's 5-hour and weekly windows), and
//   - what the AIs RAPR ran for you (the `rapr` MCP server) did today.
// The last two come from ~/.config/rapr/mcp-usage.json, which helm/mcp_usage.py writes.
//
// The band shows in the terminal and the desktop app. Anywhere, /rapr-usage asks the `rapr`
// MCP server for every AI's usage live, prints it, and opens a RAPR usage pane that keeps
// itself current.
//
// /rapr-usage                 usage now, in the chat and a pane beside it
// /rapr-usage band [on|off]   show or hide the band (terminal, desktop app)
// /rapr-usage details         the band: one line, or a row per AI
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Bucket, Live, Usage, View, Window } from '../types'

const NO_LIVE: Live = { claude: [], cost: null, claudeMode: null }
const view = atom({ plugin: 'rapr-usage', key: 'view' } as const, { usage: null, live: NO_LIVE, details: false } as View, { shape: 'view-3' })
const HIDDEN = 'hidden'           // $.store key, kept across sessions
const REFRESH_MS = 20_000         // relays and bake-offs finish while you're idle
const PANE = 'rapr-usage'
// What /mcp may call RAPR's server: `claude mcp add rapr ...` (the README's), or its own name.
const SERVERS = ['rapr', 'rapr-ai', 'RAPR AI']

const EMPTY: Bucket = { calls: 0, failed: 0, seconds: 0, tokens: 0, agents: {} }

async function usageFile($: EngineInterface): Promise<string> {
  const own = await $.env.get('RAPR_MCP_USAGE_FILE')
  if (own) return own
  // Windows sets USERPROFILE, not HOME.
  const home = (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE')) ?? ''
  return `${home}/.config/rapr/mcp-usage.json`
}

function localDay(ms: number): string {
  const d = new Date(ms)
  const two = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}

const LABELS: { [kind: string]: string } = { five_hour: '5h', seven_day: 'week', spend_limit: 'spend' }

// Claude Code's own figures: the plan windows the last API response reported, and /cost.
async function live($: EngineInterface): Promise<Live> {
  const u = await $.session.usage().catch(() => undefined)
  if (!u) return NO_LIVE
  const claude: Window[] = u.rateLimits.map(r => ({
    key: r.kind,
    label: LABELS[r.kind] ?? r.kind.replace(/_/g, ' '),
    pct: r.percentUsed,
    resets_at: r.resetsAt ? Date.parse(r.resetsAt) / 1000 : null,
  }))
  let claudeMode: Live['claudeMode'] = claude.length ? 'plan' : null
  if (!claudeMode) {
    const flags = [
      await $.env.get('ANTHROPIC_API_KEY'),
      await $.env.get('CLAUDE_CODE_USE_BEDROCK'),
      await $.env.get('CLAUDE_CODE_USE_VERTEX'),
      await $.env.get('CLAUDE_CODE_USE_FOUNDRY'),
    ]
    if (flags.some(f => f !== undefined && !['', '0', 'false'].includes(f.trim()))) claudeMode = 'api'
  }
  return { claude, cost: u.cost?.usd ?? null, claudeMode }
}

// Plan or API key: what Claude Code says now, else what RAPR last saw.
export function modeOf(v: View, agent: string): 'plan' | 'api' | null {
  if (agent === 'claude' && v.live.claudeMode) return v.live.claudeMode
  return v.usage?.billing?.[agent]?.mode ?? null
}

async function readFile($: EngineInterface): Promise<Usage | null> {
  try {
    const parsed = JSON.parse(await $.fs.read(await usageFile($))) as Usage
    if (parsed && parsed.version === 1 && parsed.today && parsed.total) return parsed
  } catch {
    // no file yet: RAPR hasn't run an AI on this computer
  }
  return null
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b)

async function refresh($: EngineInterface): Promise<void> {
  let usage = await readFile($)
  const now = await $.clock.now()
  // The file's "today" is the day of its last write; past midnight it is yesterday's.
  if (usage && usage.day !== localDay(now)) usage = { ...usage, today: EMPTY }
  const fresh = await live($)
  const before = await read($, view)
  if (same(before.usage, usage) && same(before.live, fresh)) return
  await update($, view, v => ({ ...v, usage, live: fresh }))
}

// A window past its reset time has started over.
export function current(w: Window, nowSeconds: number): Window {
  return w.resets_at && w.resets_at < nowSeconds ? { ...w, pct: 0 } : w
}

export function windowsText(name: string, windows: Window[]): string {
  return `${name} ${windows.map(w => `${w.label} ${Math.round(w.pct)}%`).join(' · ')}`
}

export function resetText(w: Window, nowSeconds: number): string {
  if (!w.resets_at) return ''
  const s = Math.max(0, w.resets_at - nowSeconds)
  const h = Math.floor(s / 3600)
  return h >= 24 ? `${Math.floor(h / 24)}d ${h % 24}h` : `${h}h ${Math.floor((s % 3600) / 60)}m`
}

// Every AI's plan windows: Claude's from Claude Code itself, the others' from the file.
export function plans(v: View, nowSeconds: number): { agent: string; name: string; windows: Window[] }[] {
  const out: { agent: string; name: string; windows: Window[] }[] = []
  const fileClaude = v.usage?.limits?.claude?.windows ?? []
  const claude = v.live.claude.length ? v.live.claude : fileClaude
  if (claude.length && modeOf(v, 'claude') !== 'api') out.push({ agent: 'claude', name: 'Claude', windows: claude })
  for (const [agent, lim] of Object.entries(v.usage?.limits ?? {})) {
    if (agent !== 'claude' && lim.windows.length && modeOf(v, agent) !== 'api') {
      out.push({ agent, name: lim.name || agent, windows: lim.windows })
    }
  }
  return out.map(p => ({ ...p, windows: p.windows.map(w => current(w, nowSeconds)) }))
}

// Every AI's usage, asked live by RAPR's MCP server (its `usage` tool); null when no RAPR
// server is connected here. It also writes the file this plugin reads.
async function askRapr($: EngineInterface): Promise<string | null> {
  for (const server of SERVERS) {
    try {
      const r = await $.mcp.call(server, 'usage', {})
      if (r.isError) continue
      const text = r.content.map(c => (c.type === 'text' ? c.text : '')).join('\n').trim()
      if (text) return text
    } catch {
      // not this name: try the next
    }
  }
  return null
}

export function fmtSeconds(s: number): string {
  const t = Math.round(s)
  if (t < 60) return `${t}s`
  const m = Math.floor(t / 60)
  if (m < 60) return `${m}m ${String(t % 60).padStart(2, '0')}s`
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
}

export function fmtTokens(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`
  return String(n)
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function bucketText(b: Omit<Bucket, 'agents'>): string {
  const failed = b.failed ? `, ${b.failed} failed` : ''
  const cost = b.cost_usd && b.cost_usd >= 0.005 ? ` · $${b.cost_usd.toFixed(2)}` : ''
  return `${plural(b.calls, 'call')} · ${fmtSeconds(b.seconds)} · ${b.estimated ? '~' : ''}${fmtTokens(b.tokens)} tok${cost}${failed}`
}

// "Codex 3 · 4m 10s   Claude 2 · 1m 05s", busiest first.
export function agentsText(b: Bucket): string {
  return Object.entries(b.agents)
    .sort((x, y) => y[1].seconds - x[1].seconds)
    .map(([key, a]) => `${a.name || key} ${a.calls} · ${fmtSeconds(a.seconds)}`)
    .join('   ')
}

// The pane's text (and the chat's when RAPR's server isn't connected): every AI's plan
// windows with reset times, API keys with money spent, why others show nothing, RAPR's runs.
export function paneLines(v: View, nowSeconds: number): string[] {
  const out: string[] = []
  const planned = plans(v, nowSeconds)
  const live = v.usage?.live ?? {}
  if (planned.length) {
    out.push('Plan usage, as each AI reports it:')
    for (const p of planned) {
      const plan = live[p.agent]?.plan ? ` (${live[p.agent]?.plan})` : ''
      out.push(`${p.name}${plan}`)
      for (const w of p.windows) {
        const reset = w.resets_at ? `, resets in ${resetText(w, nowSeconds)}` : ''
        out.push(`  ${w.label} ${Math.round(w.pct)}% used${reset}`)
      }
    }
  }
  const apis = Object.entries(v.usage?.billing ?? {}).filter(([agent, b]) => b.mode === 'api' || modeOf(v, agent) === 'api')
  if (apis.length || modeOf(v, 'claude') === 'api') {
    out.push('On an API key (billed per token, no 5-hour or weekly limit):')
    if (modeOf(v, 'claude') === 'api' && v.live.cost !== null) out.push(`  Claude: this session $${v.live.cost.toFixed(2)}`)
    for (const [agent, b] of apis) {
      if (agent === 'claude') continue
      out.push(`  ${b.name || agent}: $${(v.usage?.today.agents[agent]?.cost_usd ?? 0).toFixed(2)} today through RAPR`)
    }
  }
  const shown = new Set([...planned.map(p => p.agent), ...apis.map(([a]) => a)])
  const quiet = Object.entries(live).filter(([agent, r]) => !shown.has(agent) && r.note)
  if (quiet.length) {
    out.push('Nothing to show for:')
    for (const [agent, r] of quiet) out.push(`  ${r.name || agent}: ${r.note}`)
  }
  const today = v.usage?.today
  if (today && today.calls) {
    out.push(`RAPR today: ${bucketText(today)}`)
    for (const [agent, a] of Object.entries(today.agents).sort((x, y) => y[1].seconds - x[1].seconds)) {
      out.push(`  ${a.name || agent}: ${bucketText(a)}`)
    }
  }
  if (!out.length) out.push('No usage yet: RAPR hasn\'t heard from any AI. Press "Ask every AI now".')
  return out
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'rapr-usage',
      description: "Every AI's real usage now, in the chat and a pane; 'band' shows or hides the band",
    })
    await refresh($)
    $.clock.every(REFRESH_MS, () => {
      void refresh($).catch(() => undefined)
    })
    return next(e)
  })

  on('command.run', { command: 'rapr-usage' }, async ($, e) => {
    const [arg = '', value = ''] = (e.args ?? '').trim().toLowerCase().split(/\s+/)
    if (arg === 'details') {
      const v = await update($, view, x => ({ ...x, details: !x.details }))
      await $.store.set(HIDDEN, false)
      return { text: v.details ? 'RAPR usage band: a row per AI.' : 'RAPR usage band: one line.' }
    }
    if (arg === 'band' || arg === 'on' || arg === 'off') {
      const want = arg === 'band' ? value : arg
      const hidden = want === 'on' ? false : want === 'off' ? true : !(await $.store.get(HIDDEN))
      await $.store.set(HIDDEN, hidden)
      await refresh($)
      $.ui.invalidate('ui.render')
      return { text: hidden ? 'RAPR usage band hidden. /rapr-usage band brings it back.'
                            : 'RAPR usage band shown (terminal and desktop app).' }
    }
    // Usage now: asked live of every AI by RAPR's MCP server, in the chat and a pane.
    const text = await askRapr($)
    await refresh($)
    await $.ui.open({ id: PANE, title: 'RAPR usage' }).catch(() => undefined)
    return {
      text: text ?? 'RAPR\'s MCP server isn\'t connected here, so the usage below is the last RAPR saw. '
        + 'Add it with: claude mcp add --scope user rapr -- rapr mcp\n\n' + paneLines(await read($, view), (await $.clock.now()) / 1000).join('\n'),
    }
  })

  // A RAPR tool just answered (ask_agent, second_opinion, a relay's status…): show its run now.
  on('tool.call', async ($, e, next) => {
    const result = await next(e)
    if (/^mcp__rapr/i.test(e.tool)) await refresh($).catch(() => undefined)
    return result
  })

  on('turn.complete', async ($, e, next) => {
    await refresh($).catch(() => undefined)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const v = await read($, view)
    if (e.props.hasSurvey || (await $.store.get(HIDDEN))) return next(e)
    const nowSeconds = (await $.clock.now()) / 1000
    const planned = plans(v, nowSeconds)
    const today = v.usage?.today ?? EMPTY
    const { Box, Text, Button } = $.ui.resolve(e)
    const width = e.surface === 'terminal' ? e.props.bodyColumns : undefined
    const colour = (pct: number) => (pct >= 90 ? 'error' : pct >= 70 ? 'warning' : undefined)
    // Money only on an API key; on a plan the session's cost is a list price nobody pays.
    const cost = modeOf(v, 'claude') === 'api' && v.live.cost !== null ? `Claude API key · session $${v.live.cost.toFixed(2)}` : ''
    // Other AIs on an API key: what RAPR spent on them today, no windows.
    const apis = Object.entries(v.usage?.billing ?? {})
      .filter(([agent, b]) => agent !== 'claude' && b.mode === 'api')
      .map(([agent, b]) => `${b.name || agent} API key · $${(today.agents[agent]?.cost_usd ?? 0).toFixed(2)} today`)
    if (!planned.length && today.calls === 0 && !cost && !apis.length) return next(e)
    const rapr = today.calls ? `RAPR today ${plural(today.calls, 'call')} · ${fmtSeconds(today.seconds)}` : ''
    const toggle = (
      <Button
        key="details"
        label={v.details ? 'Less' : 'More'}
        onPress={() => update($, view, x => ({ ...x, details: !x.details }))}
      />
    )
    const hide = (
      <Button
        key="hide"
        label="Hide"
        onPress={async () => {
          await $.store.set(HIDDEN, true)
          $.ui.invalidate('ui.render')
          $.ui.toast('RAPR usage ribbon hidden. /rapr-usage brings it back.')
        }}
      />
    )
    const plan = (p: { name: string; windows: Window[] }, withResets: boolean) => (
      <Box key={p.name} gap={1}>
        <Text bold>{p.name}</Text>
        {p.windows.map(w => (
          <Text key={w.key} color={colour(w.pct)}>
            {w.label} {Math.round(w.pct)}%{withResets && w.resets_at ? ` (resets in ${resetText(w, nowSeconds)})` : ''}
          </Text>
        ))}
      </Box>
    )

    if (!v.details) {
      return (
        <Box width={width} gap={2}>
          <Text color="claude" bold>RAPR</Text>
          {planned.map(p => plan(p, false))}
          {cost ? <Text dimColor>{cost}</Text> : null}
          {apis.map(t => <Text key={t} dimColor>{t}</Text>)}
          {rapr ? <Text dimColor wrap="truncate-end">{rapr}</Text> : null}
          {toggle}
          {hide}
        </Box>
      )
    }

    const rows = Object.entries(today.agents).sort((x, y) => y[1].seconds - x[1].seconds)
    return (
      <Box flexDirection="column" width={width}>
        <Box gap={1}>
          <Text color="claude" bold>RAPR</Text>
          <Text dimColor>plans as each AI reports them; API keys have no 5h or weekly limit</Text>
          {toggle}
          {hide}
        </Box>
        {planned.map(p => plan(p, true))}
        {cost ? <Text>{cost}</Text> : null}
        {apis.map(t => <Text key={t}>{t}</Text>)}
        {today.calls ? <Text>RAPR today {bucketText(today)}</Text> : null}
        {rows.map(([key, a]) => (
          <Box key={key} gap={1}>
            <Text>  {a.name || key}</Text>
            <Text dimColor>{bucketText(a)}</Text>
          </Box>
        ))}
        {v.usage && v.usage.total.calls ? <Text dimColor>RAPR all time {bucketText(v.usage.total)}</Text> : null}
      </Box>
    )
  })
  // The pane: drawn on every surface.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const v = await read($, view)
    const lines = paneLines(v, (await $.clock.now()) / 1000)
    return (
      <Box flexDirection="column" gap={e.surface === 'terminal' ? 0 : 1}>
        <Box gap={1}>
          <Text color="claude" bold>RAPR usage</Text>
          <Button
            key="refresh"
            label="Ask every AI now"
            onPress={async () => {
              await askRapr($)
              await refresh($)
            }}
          />
        </Box>
        {lines.map((line, i) => (
          <Text key={String(i)} dimColor={line.startsWith('  ')} bold={/^[A-Z]/.test(line) && line.endsWith(':')}>
            {line}
          </Text>
        ))}
      </Box>
    )
  })
}
