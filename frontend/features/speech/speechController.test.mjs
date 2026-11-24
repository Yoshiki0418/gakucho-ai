import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
const __dirname = path.dirname(fileURLToPath(import.meta.url))

function controllerFixture(overrides = {}) {
  const timers = new Map()
  let timerId = 0
  const mod = { exports: {} }
  const js = ts.transpileModule(fs.readFileSync(path.join(__dirname, 'speechController.ts'), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  vm.runInNewContext(js, {
    module: mod, exports: mod.exports, process, Blob, FormData, AbortController,
    setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id },
    clearTimeout: id => timers.delete(id),
  })
  const events = { phases: [], results: [], errors: [], uploads: [], tracksStopped: 0 }
  const recognition = {
    start() {}, stop() {}, abort() {}, onresult: null, onend: null, onerror: null,
  }
  const stream = { getTracks: () => [{ stop: () => { events.tracksStopped++ } }] }
  let recorder
  const deps = {
    createRecognition: () => recognition,
    getUserMedia: async () => stream,
    createRecorder: () => {
      recorder = {
        state: 'inactive', mimeType: 'audio/webm',
        start() { this.state = 'recording' },
        stop() {
          this.state = 'inactive'
          this.ondataavailable?.({ data: new Blob(['recorded audio']) })
          this.pendingStop = this.onstop?.()
        },
      }
      return recorder
    },
    fetch: async (_url, request) => {
      events.uploads.push(request)
      return { ok: true, json: async () => ({ text: 'recognized' }) }
    },
    ...overrides,
  }
  const controller = mod.exports.createSpeechController({
    onPhase: phase => events.phases.push(phase),
    onResult: (text, final) => events.results.push([text, final]),
    onError: message => events.errors.push(message),
  }, deps)
  return { controller, events, recognition, stream, timers, get recorder() { return recorder } }
}
const browserResult = (text, isFinal) => ({ results: [{ 0: { transcript: text }, isFinal }] })
const flush = async () => { for (let i = 0; i < 5; i++) await Promise.resolve() }

test('browser manual finish accepts the last result and submits only once', async () => {
  const f = controllerFixture()
  await f.controller.start('browser')
  f.recognition.onresult(browserResult('partial', false))
  f.controller.finish()
  f.recognition.onresult(browserResult('final sentence', true))
  const lateEnd = f.recognition.onend
  lateEnd()
  lateEnd()
  assert.deepEqual(f.events.results.filter(([, final]) => final), [['final sentence', true]])
  assert.equal(f.timers.size, 0)
})

test('browser automatic submission and cancellation reject stale events', async () => {
  const f = controllerFixture()
  await f.controller.start('browser', true)
  const lateResult = f.recognition.onresult
  lateResult(browserResult('one sentence', true))
  lateResult(browserResult('stale', true))
  assert.deepEqual(f.events.results.filter(([, final]) => final), [['one sentence', true]])
  await f.controller.start('browser')
  const cancelledEnd = f.recognition.onend
  f.controller.cancel()
  cancelledEnd()
  assert.equal(f.events.errors.length, 0)
})

test('selected Whisper identifier and recording reach the upload endpoint', async () => {
  const f = controllerFixture()
  await f.controller.start('whisper-large-v3-turbo')
  f.controller.finish()
  await f.recorder.pendingStop
  assert.equal(f.events.uploads[0].body.get('model'), 'whisper-large-v3-turbo')
  assert.ok(f.events.uploads[0].body.get('file').size > 0)
  assert.deepEqual(f.events.results, [['recognized', true]])
  assert.equal(f.events.tracksStopped, 1)
})

test('cancel while microphone permission is pending closes the late stream', async () => {
  let allow
  let stopped = 0
  const f = controllerFixture({ getUserMedia: () => new Promise(resolve => { allow = resolve }) })
  const pending = f.controller.start('whisper-base')
  f.controller.cancel()
  allow({ getTracks: () => [{ stop: () => { stopped++ } }] })
  await pending
  assert.equal(stopped, 1)
  assert.equal(f.events.uploads.length, 0)
  assert.equal(f.recorder, undefined)
})

test('cancel or model switch aborts transcription and ignores late server responses', async () => {
  let respond
  let signal
  const f = controllerFixture({ fetch: (_url, request) => {
    signal = request.signal
    return new Promise(resolve => { respond = resolve })
  } })
  await f.controller.start('whisper-base')
  f.controller.finish()
  const pending = f.recorder.pendingStop
  await f.controller.start('browser')
  assert.equal(signal.aborted, true)
  respond({ ok: true, json: async () => ({ text: 'old transcript' }) })
  await pending
  assert.equal(f.events.results.length, 0)
  assert.equal(f.events.errors.length, 0)
  assert.equal(f.events.phases.at(-1), 'listening')
  f.controller.cancel()
})

test('model switch between response headers and JSON does not deliver stale text', async () => {
  let jsonResolve
  const f = controllerFixture({ fetch: async () => ({ ok: true, json: () => new Promise(resolve => { jsonResolve = resolve }) }) })
  await f.controller.start('whisper-base')
  f.controller.finish()
  const pending = f.recorder.pendingStop
  await flush()
  f.controller.cancel()
  jsonResolve({ text: 'stale' })
  await pending
  assert.equal(f.events.results.length, 0)
})

test('recording stops before the server duration limit and releases its microphone', async () => {
  const f = controllerFixture()
  await f.controller.start('whisper-base')
  const timer = [...f.timers.values()][0]
  assert.equal(timer.delay, 59000)
  timer.fn()
  await f.recorder.pendingStop
  assert.equal(f.recorder.state, 'inactive')
  assert.equal(f.events.tracksStopped, 1)
  assert.equal(f.events.uploads.length, 1)
  assert.equal(f.timers.size, 0)
})

test('a proxy HTML 413 reports the upload limit without trying to parse JSON', async () => {
  const f = controllerFixture({ fetch: async () => ({
    ok: false, status: 413,
    json: async () => { assert.fail('HTML error response must not be parsed as JSON') },
  }) })
  await f.controller.start('whisper-base')
  f.controller.finish()
  await f.recorder.pendingStop
  assert.equal(f.events.results.length, 0)
  assert.equal(f.events.errors.length, 1)
  assert.match(f.events.errors[0], /8 MiB/)
  assert.equal(f.events.tracksStopped, 1)
  assert.equal(f.events.phases.at(-1), 'idle')
})

test('recorder failure and oversized chunks release the microphone without upload', async () => {
  let stopped = 0
  const broken = controllerFixture({
    getUserMedia: async () => ({ getTracks: () => [{ stop: () => { stopped++ } }] }),
    createRecorder: () => { throw new Error('unsupported') },
  })
  await broken.controller.start('whisper-base')
  assert.equal(stopped, 1)
  assert.equal(broken.events.errors.length, 1)
  const f = controllerFixture()
  await f.controller.start('whisper-base')
  f.recorder.ondataavailable({ data: { size: 8 * 1024 * 1024 + 1 } })
  assert.equal(f.events.tracksStopped, 1)
  assert.equal(f.events.uploads.length, 0)
  assert.equal(f.events.errors.length, 1)
})
