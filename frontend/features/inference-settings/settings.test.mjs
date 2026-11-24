import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const loaded = { exports: {} }
const source = readFileSync(new URL('./settings.ts', import.meta.url), 'utf8')
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText,
  { exports: loaded.exports, module: loaded, URLSearchParams })
const { buildChatQuery, defaultDraft, parseCatalog, validateDraft } = loaded.exports

const catalog = () => ({
  llm_models: [{ id: 'gpt-4o', label: 'GPT-4o', supports_temperature: true }, { id: 'gpt-5.2', label: 'GPT-5.2', supports_temperature: false }],
  filler_models: [{ id: 'gpt-4o-mini', label: 'GPT-4o mini', supports_temperature: true }],
  modes: [{ id: 'general', label: '学長', description: '学長と会話' }, { id: 'assistant', label: '一般AI', description: '一般のAI' }],
  tts_voices: [{ id: '0', label: '学長' }, { id: '3', label: '話者3' }],
  stt_models: [{ id: 'browser', label: 'ブラウザ', available: true }, { id: 'whisper-base', label: 'Whisper', available: false, reason: '未準備' }],
  defaults: { llm_model: 'gpt-4o', filler_model: 'gpt-4o-mini', mode: 'general', temperature: null, max_tokens: null,
    rag_top_k: 5, rag_threshold: 0.25, tts_voice: '0', stt_model: 'browser' },
  limits: { temperature: { min: 0, max: 2 }, max_tokens: { min: 16, max: 4096 }, rag_top_k: { min: 1, max: 20 }, rag_threshold: { min: 0, max: 1 } },
})

test('a configured request reaches the API without losing zero values or corrupting Japanese text', () => {
  const choices = parseCatalog(catalog())
  const draft = { ...defaultDraft(choices), temperature: '0', max_tokens: '512', rag_top_k: '8', rag_threshold: '0', tts_voice: '3' }
  const checked = validateDraft(draft, choices, 'gpt-4o')
  assert.equal(checked.valid, true)
  const query = buildChatQuery({ text: '学内の「A&B」は？', mode: 'assistant', fillerMode: 'dynamic', llmModel: 'gpt-4o', fillerModel: 'gpt-4o-mini', inference: checked.request })
  assert.deepEqual(Object.fromEntries(query), { text: '学内の「A&B」は？', mode: 'assistant', filler_mode: 'dynamic', llm_model: 'gpt-4o',
    filler_model: 'gpt-4o-mini', temperature: '0', max_tokens: '512', rag_top_k: '8', rag_threshold: '0', tts_voice: '3' })
})

test('blank optional parameters remain unspecified; inactive filler model is omitted', () => {
  const choices = catalog()
  const checked = validateDraft(defaultDraft(choices), choices, 'gpt-4o')
  const query = buildChatQuery({ text: 'hello', mode: 'general', fillerMode: 'none', fillerModel: 'gpt-4o-mini', inference: checked.request })
  assert.equal(query.has('temperature'), false)
  assert.equal(query.has('max_tokens'), false)
  assert.equal(query.has('filler_model'), false)
})

test('model changes cannot leak an unsupported temperature', () => {
  const choices = catalog()
  const checked = validateDraft({ ...defaultDraft(choices), temperature: '0.7' }, choices, 'gpt-5.2')
  assert.equal(checked.valid, true)
  assert.equal('temperature' in checked.request, false)
})

test('ordinary AI does not send unused campus search parameters or block on their drafts', () => {
  const choices = catalog()
  const checked = validateDraft({ ...defaultDraft(choices), rag_top_k: '', rag_threshold: 'NaN' }, choices, 'gpt-4o', 'assistant')
  assert.equal(checked.valid, true)
  assert.equal('rag_top_k' in checked.request, false)
  assert.equal('rag_threshold' in checked.request, false)
})

for (const [key, values] of Object.entries({ temperature: ['NaN', 'Infinity', '-0.1', '2.01'], max_tokens: ['0', '1', '15', '4097', '1.2', 'Infinity'],
  rag_top_k: ['', '0', '21', '1.2'], rag_threshold: ['', '-0.01', '1.01', 'NaN'] })) {
  test(`reject invalid ${key} values before submitting a conversation`, () => {
    for (const value of values) {
      const choices = catalog()
      const checked = validateDraft({ ...defaultDraft(choices), [key]: value }, choices, 'gpt-4o')
      assert.equal(checked.valid, false, `${key}=${value}`)
      assert.ok(checked.errors[key])
      assert.equal(key in checked.request, false)
    }
  })
}

test('the minimum generation budget accepted by Responses is sent unchanged', () => {
  const choices = catalog()
  const checked = validateDraft({ ...defaultDraft(choices), max_tokens: '16' }, choices, 'gpt-4o')
  assert.equal(checked.valid, true)
  assert.equal(checked.request.max_tokens, 16)
})

test('unavailable speech engines and unknown speakers cannot be sent', () => {
  const choices = catalog()
  const checked = validateDraft({ ...defaultDraft(choices), tts_voice: '99', stt_model: 'whisper-base' }, choices, 'gpt-4o')
  assert.ok(checked.errors.tts_voice)
  assert.ok(checked.errors.stt_model)
})

test('each tab owns an independent draft; validation does not mutate it', () => {
  const choices = catalog()
  const first = defaultDraft(choices)
  const second = defaultDraft(choices)
  first.rag_top_k = '12'
  assert.equal(second.rag_top_k, '5')
  const before = JSON.stringify(first)
  validateDraft(first, choices, 'gpt-4o')
  assert.equal(JSON.stringify(first), before)
})

test('catalog errors are surfaced rather than rendering invented model options', () => {
  assert.throws(() => parseCatalog({}))
  assert.throws(() => parseCatalog({ ...catalog(), llm_models: [{ id: 'fake' }] }))
  assert.throws(() => parseCatalog({ ...catalog(), limits: {} }))
  assert.throws(() => parseCatalog({ ...catalog(), defaults: { ...catalog().defaults, llm_model: 'unknown' } }))
})

test('network failure fallback leaves inference and model parameters unspecified', () => {
  const query = buildChatQuery({ text: 'こんにちは', mode: 'general', fillerMode: 'endogenous' })
  assert.deepEqual(Object.fromEntries(query), { text: 'こんにちは', mode: 'general', filler_mode: 'endogenous' })
  assert.throws(() => buildChatQuery({ text: 'hello', mode: 'general', fillerMode: 'none', inference: { max_tokens: Number.NaN } }))
})
