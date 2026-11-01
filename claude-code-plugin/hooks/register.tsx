// RAPR's usage ribbon in Claude Code: a band above the prompt with
//   - your Claude plan's 5-hour and weekly usage and this session's cost, exactly as Claude
//     Code counts them ($.session.usage(): the numbers of claude.ai's usage page and /cost),
//   - the other AIs' plan usage as they report it (Codex's 5-hour and weekly windows), and
//   - what the AIs RAPR ran for you (the `rapr` MCP server) did today.
// The last two come from ~/.config/rapr/mcp-usage.json, which helm/mcp_usage.py writes.
//
// /rapr-usage           show or hide the band
// /rapr-usage details   one line, or a row per AI
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Bucket, Live, Usage, View, Window } from '../types'

const NO_LIVE: Live = { claude: [], cost: null }
const view = atom({ plugin: 'rapr-usage', key: 'view' } as const, { usage: null, live: NO_LIVE, details: false } as View, { shape: 'view-2' })
const HIDDEN = 'hidden'           // $.store key, kept across sessions
const REFRESH_MS = 20_000         // relays and bake-offs finish while you're idle

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
  return { claude, cost: u.cost?.usd ?? null }
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
  if (claude.length) out.push({ agent: 'claude', name: 'Claude', windows: claude })
  for (const [agent, lim] of Object.entries(v.usage?.limits ?? {})) {
    if (agent !== 'claude' && lim.windows.length) out.push({ agent, name: lim.name || agent, windows: lim.windows })
  }
  return out.map(p => ({ ...p, windows: p.windows.map(w => current(w, nowSeconds)) }))
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

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'rapr-usage',
      description: "Show or hide RAPR's usage ribbon; '/rapr-usage details' shows a row per AI",
    })
    await refresh($)
    $.clock.every(REFRESH_MS, () => {
      void refresh($).catch(() => undefined)
    })
    return next(e)
  })

  on('command.run', { command: 'rapr-usage' }, async ($, e) => {
    const arg = (e.args ?? '').trim().toLowerCase()
    if (arg === 'details') {
      const v = await update($, view, x => ({ ...x, details: !x.details }))
      await $.store.set(HIDDEN, false)
      return { text: v.details ? 'RAPR usage: a row per AI.' : 'RAPR usage: one line.' }
    }
    const hidden = arg === 'on' ? false : arg === 'off' ? true : !(await $.store.get(HIDDEN))
    await $.store.set(HIDDEN, hidden)
    await refresh($)
    $.ui.invalidate('ui.render')
    return { text: hidden ? 'RAPR usage ribbon hidden. /rapr-usage brings it back.' : 'RAPR usage ribbon shown.' }
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
    if (!planned.length && today.calls === 0) return next(e)

    const { Box, Text, Button } = $.ui.resolve(e)
    const width = e.surface === 'terminal' ? e.props.bodyColumns : undefined
    const colour = (pct: number) => (pct >= 90 ? 'error' : pct >= 70 ? 'warning' : undefined)
    const cost = v.live.cost !== null ? `session $${v.live.cost.toFixed(2)}` : ''
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
          <Text dimColor>plan usage, as each AI reports it{cost ? `; this ${cost}` : ''}</Text>
          {toggle}
          {hide}
        </Box>
        {planned.map(p => plan(p, true))}
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
}
