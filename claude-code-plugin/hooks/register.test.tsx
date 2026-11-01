import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const NOW = Date.UTC(2026, 10, 1, 12, 0, 0)
const day = (ms: number) => {
  const d = new Date(ms)
  const two = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}
const IN_2H = NOW / 1000 + 2 * 3600

const usage = (dayText: string) => JSON.stringify({
  version: 1, day: dayText, updated: 1,
  today: { calls: 3, failed: 1, seconds: 250, tokens: 12_400, estimated: 0, cost_usd: 0.31, agents: {
    codex: { name: 'Codex', calls: 2, failed: 0, seconds: 200, tokens: 10_000 },
    claude: { name: 'Claude Code', calls: 1, failed: 1, seconds: 50, tokens: 2_400, cost_usd: 0.31 },
  } },
  total: { calls: 9, failed: 1, seconds: 900, tokens: 50_000, agents: {} },
  last: { agent: 'codex', name: 'Codex', seconds: 42, tokens: 100, ok: true, at: 1 },
  limits: { codex: { name: 'Codex', source: 'codex session file', at: 1, windows: [
    { key: 'primary', label: '5h', pct: 12, resets_at: IN_2H },
    { key: 'secondary', label: 'week', pct: 40.4, resets_at: 1 },     // long past: started over
  ] } },
})

const BAND = {
  plugin: 'rapr-usage',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 160, scroll: { offset: 0, bodyRows: 6 }, view: {} },
} as const

function engine(on: On, file: string | null, rateLimits: { kind: string; percentUsed: number; resetsAt?: string }[] = []) {
  mock.env(on, { HOME: '/home/me' })
  mock.clock(on, { now: NOW })
  mock.store(on)
  on('command.register', () => ({ value: { command: 'rapr-usage' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.usage', () => ({ value: {
    startedAt: NOW, rateLimits, cost: { usd: 1.234 },
    context: { used: 0, total: 1, percent: 0 },
  } as never }))
  on('fs.read', (_, e) => {
    if (file === null || e.path !== '/home/me/.config/rapr/mcp-usage.json') throw new Error('ENOENT')
    return { value: file }
  })
}

test("Claude's plan usage comes from Claude Code itself, the others' from RAPR's file", async ($, on) => {
  engine(on, usage(day(NOW)), [
    { kind: 'five_hour', percentUsed: 61, resetsAt: new Date(NOW + 3_600_000).toISOString() },
    { kind: 'seven_day', percentUsed: 88 },
  ])
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: /^5h 61%/ }))?.text).toBe('5h 61%')
    expect((await ui.find({ type: 'Text', text: /^week 88%/ }))?.text).toBe('week 88%')
    expect((await ui.find({ type: 'Text', text: /^5h 12%/ }))?.text).toBe('5h 12%')
    expect((await ui.find({ type: 'Text', text: /^week 0%/ }))?.text).toBe('week 0%')
    expect((await ui.find({ type: 'Text', text: /session/ }))?.text).toBe('session $1.23')
    expect((await ui.find({ type: 'Text', text: /RAPR today/ }))?.text).toBe('RAPR today 3 calls · 4m 10s')
    await ui.unmount()
  }
})

test('details show resets and each AI RAPR ran', async ($, on) => {
  engine(on, usage(day(NOW)), [{ kind: 'five_hour', percentUsed: 61, resetsAt: new Date(NOW + 3_600_000).toISOString() }])
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await ui.press({ key: 'details' })
  expect((await ui.find({ type: 'Text', text: /^5h 61%/ }))?.text).toBe('5h 61% (resets in 1h 0m)')
  expect((await ui.find({ type: 'Text', text: /^RAPR today/ }))?.text).toBe('RAPR today 3 calls · 4m 10s · 12.4k tok · $0.31, 1 failed')
  await ui.unmount()
})

test('nothing shows before any AI has reported usage', async ($, on) => {
  engine(on, null)
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('engine')
  await ui.unmount()
})
