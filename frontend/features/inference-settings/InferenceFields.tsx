'use client'

import type { CSSProperties } from 'react'
import { validateDraft, type ChatMode, type InferenceDraft, type SettingsCatalog } from './settings'

const fieldStyle: CSSProperties = { display: 'grid', gap: 6, marginBottom: 18, color: '#e2e8f0', fontSize: '0.85rem' }
const inputStyle: CSSProperties = { width: '100%', padding: '9px 10px', border: '1px solid #64748b', borderRadius: 7,
  color: '#f8fafc', background: '#0f172a', fontSize: '0.9rem', boxSizing: 'border-box' }
const hintStyle: CSSProperties = { color: '#94a3b8', fontSize: '0.75rem', lineHeight: 1.5 }

export function InferenceFields({ catalog, draft, modelId, mode, section, onChange }: {
  catalog: SettingsCatalog
  draft: InferenceDraft
  modelId: string
  mode: ChatMode
  section: 'inference' | 'audio'
  onChange: (key: keyof InferenceDraft, value: string) => void
}) {
  const { errors } = validateDraft(draft, catalog, modelId, mode)
  const temperatureSupported = catalog.llm_models.find((model) => model.id === modelId)?.supports_temperature === true
  if (section === 'audio') return (
    <>
      <label style={fieldStyle}>
        音声入力エンジン
        <select aria-label="音声入力エンジン" style={inputStyle} value={draft.stt_model} onChange={(event) => onChange('stt_model', event.target.value)}>
          {catalog.stt_models.map((model) => <option key={model.id} value={model.id} disabled={!model.available}>
            {model.label}{model.available ? '' : '（利用できません）'}
          </option>)}
        </select>
        <span style={hintStyle}>次にマイクを開始するときに適用します。</span>
        {catalog.stt_models.filter((model) => !model.available && model.reason).map((model) =>
          <span key={model.id} style={hintStyle}>{model.label}：{model.reason}</span>)}
        {errors.stt_model && <span role="alert" style={{ color: '#fda4af' }}>{errors.stt_model}</span>}
      </label>
      <label style={fieldStyle}>
        読み上げ話者
        <select aria-label="読み上げ話者" style={inputStyle} value={draft.tts_voice} disabled={!catalog.tts_voices.length}
          onChange={(event) => onChange('tts_voice', event.target.value)}>
          {!catalog.tts_voices.length && <option value="">既定の話者</option>}
          {catalog.tts_voices.map((voice) => <option key={voice.id} value={voice.id}>{voice.label}</option>)}
        </select>
        <span style={hintStyle}>{catalog.tts_voices.length === 1 ? 'この音声モデルで利用できる話者は1名です。' : '現在の音声モデルで利用できる話者を選びます。'}</span>
        {errors.tts_voice && <span role="alert" style={{ color: '#fda4af' }}>{errors.tts_voice}</span>}
      </label>
    </>
  )
  const fields = [
    { key: 'temperature' as const, label: '応答の変化の大きさ（temperature）', optional: true, step: '0.1', hint: temperatureSupported ? '空欄はモデルの既定値。大きいほど表現が多様になります。' : 'このモデルはtemperatureの指定に対応していません。モデルの既定値を使います。' },
    { key: 'max_tokens' as const, label: '生成トークン数の上限', optional: true, step: '1', hint: '空欄は既定値。文字数ではなく、応答生成に使うトークン数の上限です。' },
    { key: 'rag_top_k' as const, label: '学内検索の取得件数（Top-k）', optional: false, step: '1', hint: '学内情報を検索する回答で使用します。' },
    { key: 'rag_threshold' as const, label: '学内検索のスコア閾値', optional: false, step: '0.05', hint: '高いほど一致度の高い情報に絞ります。該当する情報が減ることがあります。' },
  ]
  return (
    <>
      <p style={{ ...hintStyle, marginTop: 0, marginBottom: 18 }}>{mode === 'assistant'
        ? '温度とトークン数は一般AIの回答に適用します。このモードでは学内検索を使いません。'
        : '温度とトークン数は親の会話AIと学内検索の回答に適用します。専門担当AIとフィラーは既定設定を使います。'}</p>
      {fields.map(({ key, label, optional, step, hint }) => {
        const disabled = (key === 'temperature' && !temperatureSupported) || (mode === 'assistant' && key.startsWith('rag_'))
        return <label key={key} style={fieldStyle}>
          {label}
          <input type="number" inputMode={step === '1' ? 'numeric' : 'decimal'} aria-label={label}
            aria-invalid={!!errors[key]} aria-describedby={`hint-${key}`} min={catalog.limits[key].min} max={catalog.limits[key].max}
            step={step} value={disabled ? '' : draft[key]} disabled={disabled} placeholder={optional ? '既定値を使用' : undefined}
            style={{ ...inputStyle, opacity: disabled ? 0.55 : 1 }} onChange={(event) => onChange(key, event.target.value)} />
          <span id={`hint-${key}`} style={hintStyle}>{hint}</span>
          {errors[key] && <span role="alert" style={{ color: '#fda4af' }}>{errors[key]}</span>}
        </label>
      })}
    </>
  )
}
