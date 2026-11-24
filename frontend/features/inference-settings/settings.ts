export type ChatMode = 'general' | 'ceremony' | 'assistant'

export type ModelOption = {
  id: string
  label: string
  supports_temperature: boolean
}

export type SettingsCatalog = {
  llm_models: ModelOption[]
  filler_models: ModelOption[]
  tts_voices: { id: string; label: string }[]
  stt_models: { id: string; label: string; available: boolean; reason?: string }[]
  modes: { id: ChatMode; label: string; description: string }[]
  defaults: {
    llm_model: string
    filler_model: string
    mode: ChatMode
    temperature: number | null
    max_tokens: number | null
    rag_top_k: number
    rag_threshold: number
    tts_voice: string
    stt_model: string
  }
  limits: Record<'temperature' | 'max_tokens' | 'rag_top_k' | 'rag_threshold', { min: number; max: number }>
}

export type InferenceDraft = {
  temperature: string
  max_tokens: string
  rag_top_k: string
  rag_threshold: string
  tts_voice: string
  stt_model: string
}

export type InferenceRequest = {
  temperature?: number
  max_tokens?: number
  rag_top_k?: number
  rag_threshold?: number
  tts_voice?: string
}

export type DraftErrors = Partial<Record<keyof InferenceDraft, string>>

export const EMPTY_DRAFT: InferenceDraft = {
  temperature: '', max_tokens: '', rag_top_k: '5', rag_threshold: '0.25',
  tts_voice: '', stt_model: 'browser',
}

export function defaultDraft(catalog: SettingsCatalog): InferenceDraft {
  const defaults = catalog.defaults
  return {
    temperature: defaults.temperature == null ? '' : String(defaults.temperature),
    max_tokens: defaults.max_tokens == null ? '' : String(defaults.max_tokens),
    rag_top_k: String(defaults.rag_top_k),
    rag_threshold: String(defaults.rag_threshold),
    tts_voice: defaults.tts_voice,
    stt_model: defaults.stt_model,
  }
}

/** Validate the network contract before rendering options from it. */
export function parseCatalog(value: unknown): SettingsCatalog {
  if (!value || typeof value !== 'object') throw new Error('設定一覧の形式が正しくありません。')
  const item = value as SettingsCatalog
  const isChoice = (choice: unknown): choice is { id: string; label: string } =>
    !!choice && typeof choice === 'object' && typeof (choice as { id?: unknown }).id === 'string' &&
    typeof (choice as { label?: unknown }).label === 'string'
  for (const choices of [item.llm_models, item.filler_models, item.tts_voices, item.stt_models, item.modes]) {
    if (!Array.isArray(choices) || !choices.every(isChoice)) throw new Error('設定一覧の形式が正しくありません。')
  }
  if (!item.llm_models.every((model) => typeof model.supports_temperature === 'boolean') ||
      !item.filler_models.every((model) => typeof model.supports_temperature === 'boolean') ||
      !item.stt_models.every((model) => typeof model.available === 'boolean') ||
      !item.modes.every((mode) => ['general', 'ceremony', 'assistant'].includes(mode.id))) {
    throw new Error('設定一覧の形式が正しくありません。')
  }
  for (const name of ['temperature', 'max_tokens', 'rag_top_k', 'rag_threshold'] as const) {
    const limit = item.limits?.[name]
    if (!limit || !Number.isFinite(limit.min) || !Number.isFinite(limit.max) || limit.min > limit.max) {
      throw new Error('設定範囲を取得できませんでした。')
    }
  }
  const defaults = item.defaults
  if (!defaults || typeof defaults.tts_voice !== 'string' || typeof defaults.stt_model !== 'string' ||
      !item.llm_models.some((model) => model.id === defaults.llm_model) ||
      !item.filler_models.some((model) => model.id === defaults.filler_model) ||
      !item.modes.some((mode) => mode.id === defaults.mode) ||
      !Number.isFinite(defaults.rag_top_k) || !Number.isFinite(defaults.rag_threshold)) {
    throw new Error('既定の設定を取得できませんでした。')
  }
  return item
}

export function validateDraft(draft: InferenceDraft, catalog: SettingsCatalog, modelId: string, mode: ChatMode = 'general') {
  const request: InferenceRequest = {}
  const errors: DraftErrors = {}
  const model = catalog.llm_models.find((candidate) => candidate.id === modelId)
  for (const key of ['temperature', 'max_tokens', 'rag_top_k', 'rag_threshold'] as const) {
    if (mode === 'assistant' && (key === 'rag_top_k' || key === 'rag_threshold')) continue
    // Unsupported temperature must not be forwarded after changing models.
    if (key === 'temperature' && !model?.supports_temperature) continue
    const raw = draft[key].trim()
    if (!raw && (key === 'temperature' || key === 'max_tokens')) continue
    const value = Number(raw)
    const { min, max } = catalog.limits[key]
    const integer = key === 'max_tokens' || key === 'rag_top_k'
    if (!raw || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) {
      errors[key] = `${min}〜${max}の${integer ? '整数' : '数値'}を入力してください。`
    } else {
      request[key] = value
    }
  }
  if (draft.tts_voice) {
    if (catalog.tts_voices.some((voice) => voice.id === draft.tts_voice)) request.tts_voice = draft.tts_voice
    else errors.tts_voice = '利用できる話者を選んでください。'
  }
  if (!catalog.stt_models.some((candidate) => candidate.id === draft.stt_model && candidate.available)) {
    errors.stt_model = '利用できる音声入力を選んでください。'
  }
  return { request, errors, valid: Object.keys(errors).length === 0 }
}

export function buildChatQuery(options: {
  text: string
  mode: string
  fillerMode: string
  llmModel?: string
  fillerModel?: string
  inference?: InferenceRequest
}) {
  const query = new URLSearchParams({ text: options.text, mode: options.mode, filler_mode: options.fillerMode })
  if (options.llmModel) query.set('llm_model', options.llmModel)
  if (options.fillerModel && options.fillerMode === 'dynamic') query.set('filler_model', options.fillerModel)
  for (const [key, value] of Object.entries(options.inference ?? {})) {
    if (value !== undefined && value !== null && value !== '') {
      if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('推論設定に無効な数値があります。')
      query.set(key, String(value))
    }
  }
  return query
}
