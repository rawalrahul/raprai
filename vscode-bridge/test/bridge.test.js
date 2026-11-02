// Runs the real extension.js with a stand-in `vscode` module: node --test vscode-bridge/test
'use strict'
const test = require('node:test')
const assert = require('node:assert')
const fs = require('fs')
const os = require('os')
const path = require('path')
const http = require('http')
const Module = require('module')

// --- a stand-in for the parts of VS Code the bridge uses ---------------------------------------
class LanguageModelError extends Error {
  constructor (message, code) { super(message); this.code = code }
  static NoPermissions = { name: 'NoPermissions' }
  static Blocked = { name: 'Blocked' }
  static NotFound = { name: 'NotFound' }
}
const state = { models: [], sent: [], fail: null }
function model (id, family) {
  return {
    id, family, name: id.toUpperCase(), version: '1', maxInputTokens: 128000,
    async sendRequest (messages, options) {
      state.sent.push({ id, messages, options })
      if (state.fail) throw state.fail
      return { text: (async function * () { yield 'Hello '; yield 'from ' + id })() }
    }
  }
}
const fakeVscode = {
  version: '1.105.0',
  LanguageModelError,
  LanguageModelChatMessage: { User: content => ({ role: 'user', content }) },
  CancellationTokenSource: class { constructor () { this.token = {} } cancel () {} dispose () {} },
  ProgressLocation: { Notification: 15 },
  lm: { selectChatModels: async sel => (sel && sel.vendor === 'copilot' ? state.models : []) },
  window: {
    createOutputChannel: () => ({ appendLine () {}, dispose () {} }),
    showInformationMessage () {}, showWarningMessage () {}, showErrorMessage () {},
    withProgress: (_o, fn) => fn()
  },
  commands: { registerCommand: () => ({ dispose () {} }) }
}
const resolve = Module._resolveFilename
Module._resolveFilename = function (request, ...rest) {
  return request === 'vscode' ? 'vscode' : resolve.call(this, request, ...rest)
}
require.cache.vscode = { id: 'vscode', filename: 'vscode', loaded: true, exports: fakeVscode }

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rapr-bridge-'))
process.env.RAPR_CONFIG_DIR = dir
const ext = require('../extension.js')
const file = path.join(dir, 'vscode-bridge.json')

function call (info, method, p, { body, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port: info.port, path: p, method,
      headers: { Host: `127.0.0.1:${info.port}`, ...headers } }, res => {
      let data = ''
      res.on('data', c => { data += c })
      res.on('end', () => resolve({ status: res.statusCode, json: data ? JSON.parse(data) : null }))
    })
    req.on('error', reject)
    if (body !== undefined) req.write(typeof body === 'string' ? body : JSON.stringify(body))
    req.end()
  })
}
const auth = info => ({ Authorization: 'Bearer ' + info.key })

async function started () {
  for (let i = 0; i < 50 && !fs.existsSync(file); i++) await new Promise(r => setTimeout(r, 20))
  return JSON.parse(fs.readFileSync(file, 'utf8'))
}

test('serves RAPR on localhost behind a key, and only RAPR', async t => {
  const context = { subscriptions: [] }
  ext.activate(context)
  t.after(() => ext.deactivate())
  const info = await started()
  assert.strictEqual(info.pid, process.pid)
  assert.match(info.key, /^[0-9a-f]{64}$/)
  if (process.platform !== 'win32') assert.strictEqual(fs.statSync(file).mode & 0o777, 0o600)

  assert.strictEqual((await call(info, 'GET', '/health', { headers: auth(info) })).status, 200)
  assert.strictEqual((await call(info, 'GET', '/health')).status, 401)
  assert.strictEqual((await call(info, 'GET', '/health', { headers: { Authorization: 'Bearer ' + 'f'.repeat(64) } })).status, 401)
  // A web page can't use it: it sends an Origin, or (DNS rebinding) another Host.
  assert.strictEqual((await call(info, 'GET', '/health', { headers: { ...auth(info), Origin: 'https://evil.example' } })).status, 403)
  assert.strictEqual((await call(info, 'GET', '/health', { headers: { ...auth(info), Host: 'evil.example' } })).status, 403)

  // No Copilot in VS Code: says so.
  state.models = []
  let r = await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: 'hi' } })
  assert.strictEqual(r.status, 503)
  assert.match(r.json.message, /install GitHub Copilot Chat/)

  // Copilot answers, with a model that uses no premium requests unless one is asked for.
  state.models = [model('claude-sonnet-4.5', 'claude-sonnet-4.5'), model('gpt-4.1', 'gpt-4.1')]
  assert.deepStrictEqual((await call(info, 'GET', '/models', { headers: auth(info) })).json.models.map(m => m.id),
    ['claude-sonnet-4.5', 'gpt-4.1'])
  r = await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: 'Review this diff' } })
  assert.strictEqual(r.status, 200)
  assert.strictEqual(r.json.text, 'Hello from gpt-4.1')
  assert.strictEqual(state.sent.at(-1).messages[0].content, 'Review this diff')
  assert.ok(state.sent.at(-1).options.justification)
  r = await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: 'x', model: 'claude-sonnet-4.5' } })
  assert.strictEqual(r.json.model.id, 'claude-sonnet-4.5')

  // Not allowed yet: tells the person what to press.
  state.fail = new LanguageModelError('denied', 'NoPermissions')
  r = await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: 'x' } })
  assert.strictEqual(r.status, 403)
  assert.match(r.json.message, /RAPR: Connect Copilot/)
  state.fail = new LanguageModelError('slow down', 'Blocked')
  assert.strictEqual((await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: 'x' } })).status, 429)
  state.fail = null

  assert.strictEqual((await call(info, 'POST', '/chat', { headers: auth(info), body: 'not json' })).status, 400)
  assert.strictEqual((await call(info, 'POST', '/chat', { headers: auth(info), body: { prompt: '  ' } })).status, 400)
})

test('closing the window removes its file', async () => {
  assert.strictEqual(fs.existsSync(file), false)
})
