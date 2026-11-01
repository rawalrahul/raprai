// RAPR's usage ribbon in Claude Code: a band above the prompt with what the AIs RAPR ran
// for you (through the `rapr` MCP server) did today: calls, AI time and estimated tokens,
// per AI, and the last run. The numbers come from ~/.config/rapr/mcp-usage.json, which
// helm/mcp_usage.py writes after every run; this band only reads it.
//
// /rapr-usage           show or hide the band
// /rapr-usage details   one line, or a row per AI
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Bucket, Usage, View } from '../types'

const view = atom({ plugin: 'rapr-usage', key: 'view' } as const, { usage: null, details: false } as View)
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

async function refresh($: EngineInterface): Promise<void> {
  let usage: Usage | null = null
  try {
    const parsed = JSON.parse(await $.fs.read(await usageFile($))) as Usage
    if (parsed && parsed.version === 1 && parsed.today && parsed.total) usage = parsed
  } catch {
    usage = null            // no file yet: RAPR hasn't run an AI on this computer
  }
  // The file's "today" is the day of its last write; past midnight it is yesterday's.
  if (usage && usage.day !== localDay(await $.clock.now())) usage = { ...usage, today: EMPTY }
  const before = await read($, view)
  if (before.usage?.updated === usage?.updated && before.usage?.day === usage?.day) return
  await update($, view, v => ({ ...v, usage }))
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
  return `${plural(b.calls, 'call')} · ${fmtSeconds(b.seconds)} · ~${fmtTokens(b.tokens)} tok${failed}`
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
    const { usage, details } = await read($, view)
    if (e.props.hasSurvey || !usage || usage.today.calls === 0 || (await $.store.get(HIDDEN))) return next(e)

    const { Box, Text, Button } = $.ui.resolve(e)
    const width = e.surface === 'terminal' ? e.props.bodyColumns : undefined
    const today = usage.today
    const last = usage.last
    const lastText = last
      ? `last: ${last.name} ${fmtSeconds(last.seconds)}${last.ok ? '' : ' (failed)'}`
      : ''
    const toggle = (
      <Button
        key="details"
        label={details ? 'Less' : 'Per AI'}
        onPress={() => update($, view, v => ({ ...v, details: !v.details }))}
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

    if (!details) {
      return (
        <Box width={width} gap={1}>
          <Text color="claude" bold>RAPR</Text>
          <Text>today {bucketText(today)}</Text>
          <Text dimColor wrap="truncate-end">
            {agentsText(today)}
            {lastText ? `   ${lastText}` : ''}
          </Text>
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
          <Text>today {bucketText(today)}</Text>
          {toggle}
          {hide}
        </Box>
        {rows.map(([key, a]) => (
          <Box key={key} gap={1}>
            <Text>  {a.name || key}</Text>
            <Text dimColor>{bucketText(a)}</Text>
          </Box>
        ))}
        <Text dimColor>
          {'  '}all time {bucketText(usage.total)}
          {lastText ? `   ${lastText}` : ''}   (~ tokens estimated from text length)
        </Text>
      </Box>
    )
  })
}
