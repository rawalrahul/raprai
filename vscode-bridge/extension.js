// RAPR Bridge: lets RAPR AI, on this computer, ask GitHub Copilot questions through the
// person's VS Code sign-in, using VS Code's language model API (vscode.lm).
//
// - Serves 127.0.0.1 only, on a random port, and answers only requests that carry the
//   random key written to ~/.config/rapr/vscode-bridge.json (readable only by the person).
//   Requests a web page could make (an Origin header, a Host that isn't this machine) are
//   refused, so no site open in a browser can use it.
// - One VS Code window serves at a time; when it closes, another window takes over.
// - VS Code asks the person once whether RAPR Bridge may use Copilot's models: the
//   "RAPR: Connect Copilot" command asks that question.
// Plain JavaScript with no dependencies: what's in RAPR's repository is what runs.
'use strict'

const vscode = require('vscode')
const http = require('http')
const crypto = require('crypto')
const fs = require('fs')
const os = require('os')
const path = require('path')

const VERSION = require('./package.json').version
const MAX_BODY = 4 * 1024 * 1024          // a prompt with a large diff fits
const ANSWER_TIMEOUT_MS = 15 * 60 * 1000
const CHECK_EVERY_MS = 30 * 1000
const JUSTIFICATION = 'RAPR AI asks Copilot questions for you (reviews, answers, plans) from your coding agent.'
// Models that come with every paid Copilot plan without using premium requests, first.
const PREFERRED = ['gpt-4.1', 'gpt-5-mini', 'gpt-4o']

function configDir () {
  return process.env.RAPR_CONFIG_DIR || path.join(os.homedir(), '.config', 'rapr')
}
function bridgeFile () { return path.join(configDir(), 'vscode-bridge.json') }

let server = null
let key = null
let timer = null
let output = null

function log (line) {
  if (output) output.appendLine(`[${new Date().toISOString()}] ${line}`)
}

function readBridgeFile () {
  try { return JSON.parse(fs.readFileSync(bridgeFile(), 'utf8')) } catch { return null }
}

function writeBridgeFile (port) {
  fs.mkdirSync(configDir(), { recursive: true })
  const info = { port, key, pid: process.pid, version: VERSION, vscode: vscode.version, startedAt: Date.now() }
  const tmp = bridgeFile() + '.' + process.pid + '.tmp'
  fs.writeFileSync(tmp, JSON.stringify(info, null, 1), { mode: 0o600 })
  fs.renameSync(tmp, bridgeFile())
}

function removeBridgeFile () {
  const info = readBridgeFile()
  if (info && info.pid === process.pid && info.key === key) {
    try { fs.unlinkSync(bridgeFile()) } catch { /* gone already */ }
  }
}

// Whether another window's bridge answers (then this one stays quiet).
function otherBridgeAlive (info) {
  return new Promise(resolve => {
    if (!info || !info.port || !info.key || info.pid === process.pid) return resolve(false)
    const req = http.get({ host: '127.0.0.1', port: info.port, path: '/health', timeout: 2000,
      headers: { Authorization: 'Bearer ' + info.key } }, res => { res.resume(); resolve(res.statusCode === 200) })
    req.on('error', () => resolve(false))
    req.on('timeout', () => { req.destroy(); resolve(false) })
  })
}

function sameKey (given) {
  if (typeof given !== 'string' || !key) return false
  const a = Buffer.from(given)
  const b = Buffer.from(key)
  return a.length === b.length && crypto.timingSafeEqual(a, b)
}

function send (res, status, body) {
  const text = JSON.stringify(body)
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
  res.end(text)
}

async function copilotModels () {
  return vscode.lm.selectChatModels({ vendor: 'copilot' })
}

function describe (m) {
  return { id: m.id, name: m.name, family: m.family, version: m.version, maxInputTokens: m.maxInputTokens }
}

// The model asked for (by id or family), else one that uses no premium requests, else Copilot's first.
function pickModel (models, wanted) {
  if (wanted) {
    const w = String(wanted).toLowerCase()
    const hit = models.find(m => m.id.toLowerCase() === w) || models.find(m => (m.family || '').toLowerCase() === w)
    if (hit) return hit
  }
  for (const fam of PREFERRED) {
    const hit = models.find(m => (m.family || '').toLowerCase() === fam || m.id.toLowerCase() === fam)
    if (hit) return hit
  }
  return models[0]
}

// What went wrong, in words RAPR can pass on as they are.
function explain (err) {
  const code = err && err.code
  if (err instanceof vscode.LanguageModelError || code) {
    if (code === vscode.LanguageModelError.NoPermissions.name || code === 'NoPermissions') {
      return [403, 'no_permission', 'VS Code hasn\'t allowed RAPR Bridge to use Copilot yet. In VS Code, run "RAPR: Connect Copilot" (Ctrl+Shift+P) and press Allow.']
    }
    if (code === vscode.LanguageModelError.Blocked.name || code === 'Blocked') {
      return [429, 'blocked', 'Copilot is refusing requests for now (rate limit or quota). Try again later.']
    }
    if (code === vscode.LanguageModelError.NotFound.name || code === 'NotFound') {
      return [404, 'not_found', 'That Copilot model isn\'t available in VS Code.']
    }
  }
  return [502, 'copilot_error', 'Copilot didn\'t answer: ' + String((err && err.message) || err).slice(0, 300)]
}

async function ask (prompt, wanted) {
  const models = await copilotModels()
  if (!models.length) {
    const e = new Error('no_models')
    e.status = 503
    e.reason = 'Copilot isn\'t available in VS Code: install GitHub Copilot Chat and sign in to GitHub there.'
    throw e
  }
  const model = pickModel(models, wanted)
  const cts = new vscode.CancellationTokenSource()
  const stop = setTimeout(() => cts.cancel(), ANSWER_TIMEOUT_MS)
  try {
    const resp = await model.sendRequest([vscode.LanguageModelChatMessage.User(prompt)], { justification: JUSTIFICATION }, cts.token)
    let text = ''
    for await (const part of resp.text) text += part
    return { text, model: describe(model) }
  } finally {
    clearTimeout(stop)
    cts.dispose()
  }
}

function readBody (req) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', c => {
      size += c.length
      if (size > MAX_BODY) { reject(Object.assign(new Error('too_large'), { status: 413 })); req.destroy(); return }
      chunks.push(c)
    })
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    req.on('error', reject)
  })
}

async function handle (req, res) {
  const port = server && server.address() && server.address().port
  const host = String(req.headers.host || '')
  // Only programs on this machine, and never a web page (DNS rebinding, cross-site requests).
  if (req.headers.origin || (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`)) {
    return send(res, 403, { error: 'forbidden', message: 'RAPR Bridge answers only RAPR on this computer.' })
  }
  const auth = String(req.headers.authorization || '')
  if (!sameKey(auth.startsWith('Bearer ') ? auth.slice(7) : '')) {
    return send(res, 401, { error: 'unauthorized', message: 'Wrong or missing key (see ~/.config/rapr/vscode-bridge.json).' })
  }
  const url = new URL(req.url, 'http://127.0.0.1')
  try {
    if (req.method === 'GET' && url.pathname === '/health') {
      return send(res, 200, { ok: true, version: VERSION, vscode: vscode.version, pid: process.pid })
    }
    if (req.method === 'GET' && url.pathname === '/models') {
      return send(res, 200, { models: (await copilotModels()).map(describe) })
    }
    if (req.method === 'POST' && url.pathname === '/chat') {
      let body
      try { body = JSON.parse(await readBody(req)) } catch (e) {
        return send(res, e.status || 400, { error: 'bad_request', message: e.status === 413 ? 'The prompt is too large.' : 'Send JSON: {"prompt": "..."}.' })
      }
      if (!body || typeof body.prompt !== 'string' || !body.prompt.trim()) {
        return send(res, 400, { error: 'bad_request', message: 'Send JSON: {"prompt": "..."}.' })
      }
      log(`question (${body.prompt.length} characters)${body.model ? ' for ' + body.model : ''}`)
      const answer = await ask(body.prompt, body.model)
      log(`answered by ${answer.model.id} (${answer.text.length} characters)`)
      return send(res, 200, answer)
    }
    return send(res, 404, { error: 'not_found', message: 'RAPR Bridge has /health, /models and /chat.' })
  } catch (err) {
    if (err && err.status === 503) return send(res, 503, { error: 'no_models', message: err.reason })
    const [status, code, message] = explain(err)
    log(`failed: ${code}: ${(err && err.message) || err}`)
    return send(res, status, { error: code, message })
  }
}

function startServer () {
  return new Promise((resolve, reject) => {
    key = crypto.randomBytes(32).toString('hex')
    const s = http.createServer((req, res) => { handle(req, res).catch(() => send(res, 500, { error: 'internal' })) })
    s.on('error', reject)
    s.listen(0, '127.0.0.1', () => { server = s; resolve(s.address().port) })
  })
}

// Serve unless another window already does; check again now and then, to take over.
async function ensureServing () {
  if (server) {
    const info = readBridgeFile()
    if (info && info.pid === process.pid && info.key === key) return
    if (await otherBridgeAlive(info)) {
      // Two windows started at once: the other one's file stands, so this one steps down.
      server.close()
      server = null
      log('another VS Code window serves RAPR; this one stopped')
      return
    }
    writeBridgeFile(server.address().port)
    return
  }
  if (await otherBridgeAlive(readBridgeFile())) return
  const port = await startServer()
  writeBridgeFile(port)
  log(`serving RAPR on 127.0.0.1:${port}`)
}

async function connectCopilot () {
  await ensureServing().catch(e => log('could not serve: ' + e.message))
  const models = await copilotModels()
  if (!models.length) {
    vscode.window.showWarningMessage('RAPR Bridge: Copilot isn\'t available in this VS Code. Install GitHub Copilot Chat and sign in to GitHub, then run "RAPR: Connect Copilot" again.')
    return
  }
  try {
    // Asking once from a command is what shows VS Code's "allow RAPR Bridge to use Copilot" question.
    const answer = await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'RAPR Bridge: asking Copilot…' },
      () => ask('Reply with the single word: ready'))
    vscode.window.showInformationMessage(`RAPR Bridge: Copilot is connected (${answer.model.name}). RAPR can ask it questions now.`)
  } catch (err) {
    const [, , message] = explain(err)
    vscode.window.showErrorMessage('RAPR Bridge: ' + message)
  }
}

async function bridgeStatus () {
  const info = readBridgeFile()
  const mine = server && info && info.pid === process.pid
  const models = await copilotModels().catch(() => [])
  const where = mine ? `this window serves RAPR on 127.0.0.1:${info.port}`
    : info ? `another VS Code window serves RAPR (port ${info.port})` : 'not serving'
  vscode.window.showInformationMessage(`RAPR Bridge ${VERSION}: ${where}; Copilot models: ${models.length ? models.map(m => m.family || m.id).join(', ') : 'none (install GitHub Copilot Chat and sign in)'}.`)
}

function activate (context) {
  output = vscode.window.createOutputChannel('RAPR Bridge')
  context.subscriptions.push(output)
  context.subscriptions.push(vscode.commands.registerCommand('rapr.connectCopilot', connectCopilot))
  context.subscriptions.push(vscode.commands.registerCommand('rapr.bridgeStatus', bridgeStatus))
  ensureServing().catch(e => log('could not serve: ' + e.message))
  timer = setInterval(() => { ensureServing().catch(() => {}) }, CHECK_EVERY_MS)
}

function deactivate () {
  if (timer) clearInterval(timer)
  removeBridgeFile()
  if (server) { server.close(); server = null }
}

module.exports = { activate, deactivate, _test: { pickModel, explain, handle, bridgeFile } }
