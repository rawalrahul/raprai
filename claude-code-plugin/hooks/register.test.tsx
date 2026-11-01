import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const NOW = Date.UTC(2026, 10, 1, 12, 0, 0)
const day = (ms: number) => {
  const d = new Date(ms)
  const two = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`
}

const usage = (dayText: string) => JSON.stringify({
  version: 1, day: dayText, updated: 1,
  today: { calls: 3, failed: 1, seconds: 250, tokens: 12_400, agents: {
    codex: { name: 'Codex', calls: 2, failed: 0, seconds: 200, tokens: 10_000 },
    claude: { name: 'Claude Code', calls: 1, failed: 1, seconds: 50, tokens: 2_400 },
  } },
  total: { calls: 9, failed: 1, seconds: 900, tokens: 50_000, agents: {} },
  last: { agent: 'codex', name: 'Codex', seconds: 42, tokens: 100, ok: true, at: 1 },
})

const BAND = {
  plugin: 'rapr-usage',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 6, bodyColumns: 120, scroll: { offset: 0, bodyRows: 6 }, view: {} },
} as const

function engine(on: On, file: string | null) {
  mock.env(on, { HOME: '/home/me' })
  mock.clock(on, { now: NOW })
  mock.store(on)
  on('command.register', () => ({ value: { command: 'rapr-usage' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('fs.read', (_, e) => {
    if (file === null || e.path !== '/home/me/.config/rapr/mcp-usage.json') throw new Error('ENOENT')
    return { value: file }
  })
}

test("the band shows today's RAPR usage, on every surface", async ($, on) => {
  engine(on, usage(day(NOW)))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: /today/ }))?.text).toBe('today 3 calls · 4m 10s · ~12.4k tok, 1 failed')
    expect((await ui.find({ type: 'Text', text: /Codex/ }))?.text).toContain('Codex 2 · 3m 20s')
    await ui.unmount()
  }
})

test('nothing shows before RAPR has run an AI, or once the day has passed', async ($, on) => {
  engine(on, usage('2000-01-01'))
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('engine')
  await ui.unmount()
})
