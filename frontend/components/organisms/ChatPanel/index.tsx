'use client'

import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import styled from 'styled-components'
import { RefreshCcw, Settings, X } from 'lucide-react'
import Flex from '@/components/styles/Flex'
import { ChatList } from '@/components/organisms/ChatList'
import { InitialChatView } from '@/components/organisms/InitialChatView'
import ChatInputArea from '@/components/organisms/ChatInputArea'
import { ModeToggle, InputMode } from '@/components/molecules/ModeToggle'
import { VoiceInputArea } from '@/components/organisms/VoiceInputArea'
import { ZOOM, clampZoom } from '@/features/avatar/zoom'
import type { LipSyncMode } from '@/features/text-chat/hooks/useTextChat'
import { InferenceFields } from '@/features/inference-settings/InferenceFields'
import { EMPTY_DRAFT, type ChatMode, type InferenceDraft, type SettingsCatalog } from '@/features/inference-settings/settings'

const ScrollableBody = styled(Flex)`
  /* スクロールバーの幅 */
  &::-webkit-scrollbar {
    width: 6px;
  }

  /* トラック（背景）: 透明にしてUIに溶け込ませる */
  &::-webkit-scrollbar-track {
    background: transparent;
  }

  /* つまみ（動く部分）: 半透明の青みがかったグレー */
  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.2); /* Slate-400 相当の薄い色 */
    border-radius: 3px;
  }

  /* ホバー時: 少し明るくして操作可能であることを示す */
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.4);
  }

  /* Firefox対応 */
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.2) transparent;
`

interface ChatMessage {
  id: string
  text: string
  role: 'user' | 'assistant'
  name?: string
  avatarSrc?: string
}

type FillerMode = 'dynamic' | 'static' | 'none' | 'endogenous'

const FILLER_MODE_OPTIONS: { value: FillerMode; label: string; description: string }[] = [
  { value: 'dynamic', label: '外部動的フィラー', description: '別LLMがタイムアウト検知で生成（提案手法）' },
  { value: 'static', label: '静的フィラー', description: '固定フレーズからランダム選択（比較条件）' },
  { value: 'none', label: 'フィラーなし', description: 'フィラーを一切出力しない（ベースライン）' },
  { value: 'endogenous', label: '内因的フィラー', description: '親エージェント自身がツール呼び出し前に自己判断で出力（新実験条件）' },
]

// UE の口パクの駆動方式。phoneme は TTS の alignment から得た音素長で
// Face Control Rig を動かす（発話と口形が一致する）。legacy は従来の
// 口パクアニメーションを再生中だけ有効にする。
const LIP_SYNC_OPTIONS: { value: LipSyncMode; label: string; description: string }[] = [
  { value: 'legacy', label: '従来アニメーション', description: '発話中だけ口パクアニメを再生する' },
  { value: 'phoneme', label: '音素同期（推奨）', description: 'TTSの音素長に合わせて口形を動かす' },
]

type SettingsSection = 'general' | 'model' | 'inference' | 'audio' | 'filler' | 'mode'

const SETTINGS_SECTIONS: { id: SettingsSection; label: string }[] = [
  { id: 'general', label: '一般' },
  { id: 'model', label: 'モデル' },
  { id: 'inference', label: '推論・検索' },
  { id: 'audio', label: '音声' },
  { id: 'filler', label: 'フィラー' },
  { id: 'mode', label: 'モード' },
]

interface ChatPanelProps {
  messages: ReadonlyArray<ChatMessage>
  inputValue: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  onSend: (value: string) => void
  isSending?: boolean
  disabled?: boolean
  speakingMessageId?: string | null
  onTemplateClick?: (text: string) => void
  inputModeProp?: InputMode
  onInputModeChange?: (mode: InputMode) => void
  onResetChat?: () => void
  onInterrupt?: () => void
  appMode?: ChatMode
  onModeChange?: (mode: ChatMode) => void
  width?: number | string
  fillerMode?: string
  onFillerModeChange?: (mode: string) => void
  mainModel?: string
  onMainModelChange?: (model: string) => void
  fillerModel?: string
  onFillerModelChange?: (model: string) => void
  settingsCatalog?: SettingsCatalog | null
  inferenceDraft?: InferenceDraft
  onInferenceChange?: (key: keyof InferenceDraft, value: string) => void
  settingsLoading?: boolean
  settingsError?: string | null
  onReloadSettings?: () => void
  errorMessage?: string | null
  qrEnabled?: boolean
  onQrEnabledChange?: (enabled: boolean) => void
  /** アバター映像の切り抜き倍率 */
  zoom?: number
  onZoomChange?: (zoom: number) => void
  lipSyncMode?: LipSyncMode
  onLipSyncModeChange?: (mode: LipSyncMode) => void
}

export default function ChatPanel({
  messages,
  inputValue,
  onChange,
  onMicClick,
  onSend,
  isSending = false,
  disabled = false,
  speakingMessageId = null,
  inputModeProp,
  onInputModeChange,
  onResetChat,
  onInterrupt,
  appMode = 'general',
  onModeChange,
  width = '35%',
  fillerMode = 'endogenous',
  onFillerModeChange,
  mainModel = '',
  onMainModelChange,
  fillerModel = '',
  onFillerModelChange,
  settingsCatalog = null,
  inferenceDraft = EMPTY_DRAFT,
  onInferenceChange,
  settingsLoading = false,
  settingsError = null,
  onReloadSettings,
  errorMessage = null,
  qrEnabled = true,
  onQrEnabledChange,
  zoom = ZOOM.default,
  onZoomChange,
  lipSyncMode = 'legacy',
  onLipSyncModeChange,
}: ChatPanelProps) {
  const hasMessages = messages.length > 0
  const [internalMode, setInternalMode] = useState<InputMode>('text')
  const inputMode = inputModeProp ?? internalMode
  const [voiceMode, setVoiceMode] = useState<'ptt' | 'vad'>('ptt')
  const [speechSession, setSpeechSession] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [settingsSection, setSettingsSection] = useState<SettingsSection>('general')
  const settingsDialogRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!showSettings) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = settingsDialogRef.current
    const focusable = () => Array.from(dialog?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]') ?? [])
    focusable()[0]?.focus()
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowSettings(false)
      if (event.key !== 'Tab') return
      const elements = focusable()
      const first = elements[0]
      const last = elements[elements.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      previousFocus?.focus()
    }
  }, [showSettings])

  const handleModeChange = (mode: InputMode) => {
    if (!inputModeProp) {
      setInternalMode(mode)
    }
    onInputModeChange?.(mode)
  }

  const scrollContainerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!scrollContainerRef.current) return
    const el = scrollContainerRef.current
    el.scrollTop = el.scrollHeight
  }, [messages.length])

  // 設定画面のラジオ選択リスト（フィラー/モデル/モードで共通利用）
  const renderRadioList = (
    options: { value: string; label: string; description: string }[],
    selected: string,
    onSelect: (value: string) => void,
  ) => (
    <div role="radiogroup" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {options.map((opt) => {
        const isSelected = selected === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onSelect(opt.value)}
            style={{
              background: isSelected ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.03)',
              border: isSelected ? '1px solid rgba(139,92,246,0.5)' : '1px solid rgba(148,163,184,0.1)',
              borderRadius: 10,
              padding: '12px 14px',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
            onMouseEnter={(e) => {
              if (!isSelected) {
                e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
                e.currentTarget.style.border = '1px solid rgba(148,163,184,0.2)'
              }
            }}
            onMouseLeave={(e) => {
              if (!isSelected) {
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                e.currentTarget.style.border = '1px solid rgba(148,163,184,0.1)'
              }
            }}
          >
            <div style={{
              width: 16,
              height: 16,
              borderRadius: '50%',
              border: isSelected ? '2px solid #a78bfa' : '2px solid rgba(148,163,184,0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              {isSelected && (
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#a78bfa' }} />
              )}
            </div>
            <div>
              <p style={{ margin: 0, color: isSelected ? '#e2e8f0' : '#94a3b8', fontSize: '0.88rem', fontWeight: 600 }}>
                {opt.label}
              </p>
              <p style={{ margin: '2px 0 0', color: '#475569', fontSize: '0.73rem', lineHeight: 1.4 }}>
                {opt.description}
              </p>
            </div>
          </button>
        )
      })}
    </div>
  )

  // 設定画面の各セクション見出し
  const sectionHeading = (title: string, subtitle: string) => (
    <div style={{ marginBottom: 16 }}>
      <p style={{ margin: 0, color: '#F9FAFB', fontSize: '1.0rem', fontWeight: 700, letterSpacing: '0.02em' }}>
        {title}
      </p>
      <p style={{ margin: '2px 0 0', color: '#64748b', fontSize: '0.75rem' }}>
        {subtitle}
      </p>
    </div>
  )

  return (
    <Flex
      $flex_direction="column"
      $backgroundColor="#020617"
      $borderRadius="16px"
      $width={typeof width === 'number' ? `${width}px` : width}
      $height="100%"
      $padding="0"
      style={{
        overflow: 'hidden',
        boxShadow: '0 18px 40px rgba(0,0,0,0.8)',
        border: '1px solid rgba(15,23,42,0.85)',
        backgroundImage:
          'linear-gradient(180deg, rgba(0,0,0,0.98) 0%, rgba(15,23,42,0.98) 100%)',
      }}
    >
      {/* Header ... */}
      <Flex
        $flex_direction="row"
        $justifyContent="space-between"
        $alignItems="center"
        $width="100%"
        $padding="18px 20px 14px"
        $backgroundColor="rgba(15,23,42,0.9)"
        style={{
          borderBottom: '1px solid rgba(148,163,184,0.18)',
          backdropFilter: 'blur(18px)',
          zIndex: 10,
        }}
      >
        {/* 左側：タイトル */}
        <Flex $flex_direction="column" $gap="2px">
          <span
            style={{
              color: '#F9FAFB',
              fontSize: '1.3rem',
              fontWeight: 600,
              letterSpacing: '0.02em',
              marginBottom: '6px',
            }}
          >
            学長AI
          </span>
          <span style={{ color: '#9CA3AF', fontSize: '0.8rem' }}>
            金沢工業大学
          </span>
        </Flex>

        {/* 右側：ボタン群（モード切替は設定画面に統合したためヘッダーからは削除） */}
        <Flex $flex_direction="row" $gap="8px">

          {/* 設定ボタン */}
          <button
            onClick={() => setShowSettings(true)}
            style={{
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(148,163,184,0.15)',
              borderRadius: '50%',
              width: 38,
              height: 38,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: '0.25s ease',
              color: '#cbd5e1',
              position: 'relative',
            }}
            title="会話の設定"
            aria-label="会話の設定"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(139,92,246,0.20)'
              e.currentTarget.style.border = '1px solid rgba(139,92,246,0.4)'
              e.currentTarget.style.color = '#a78bfa'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
              e.currentTarget.style.border = '1px solid rgba(148,163,184,0.15)'
              e.currentTarget.style.color = '#cbd5e1'
            }}
          >
            <Settings size={18} strokeWidth={2} />
            {/* アクティブなフィラーモードをドットで示す */}
            {fillerMode === 'endogenous' && (
              <span style={{
                position: 'absolute',
                top: 6,
                right: 6,
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#a78bfa',
              }} />
            )}
          </button>

          <button
            onClick={() => {
              setSpeechSession((session) => session + 1)
              onResetChat?.()
            }}
            style={{
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(148,163,184,0.15)',
              borderRadius: '50%',
              width: 38,
              height: 38,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: '0.25s ease',
              color: '#cbd5e1',
            }}
            title="会話をリセット"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(59,130,246,0.20)'
              e.currentTarget.style.border = '1px solid rgba(59,130,246,0.4)'
              e.currentTarget.style.color = '#60a5fa'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
              e.currentTarget.style.border = '1px solid rgba(148,163,184,0.15)'
              e.currentTarget.style.color = '#cbd5e1'
            }}
          >
            <RefreshCcw size={18} strokeWidth={2} />
          </button>
        </Flex>

        {/* ===== 設定モーダル ===== */}
        {/* backdrop-filter を持つヘッダー内に置くと position:fixed の基準が
            ビューポートではなくヘッダーになり画面外へはみ出すため、
            createPortal で body 直下に描画してビューポート基準にする */}
        {showSettings && typeof document !== 'undefined' && createPortal(
          <div
            onClick={() => setShowSettings(false)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(4px)',
              zIndex: 1000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              ref={settingsDialogRef}
              role="dialog"
              aria-modal="true"
              aria-label="会話の設定"
              style={{
                background: 'linear-gradient(160deg, rgba(15,23,42,0.98) 0%, rgba(30,41,59,0.98) 100%)',
                border: '1px solid rgba(148,163,184,0.2)',
                borderRadius: 16,
                width: 660,
                maxWidth: '92vw',
                height: 560,
                maxHeight: '85vh',
                boxShadow: '0 24px 60px rgba(0,0,0,0.8)',
                display: 'flex',
                overflow: 'hidden',
              }}
            >
              {/* ===== 左サイドナビ ===== */}
              <div style={{
                width: 124,
                flexShrink: 0,
                borderRight: '1px solid rgba(148,163,184,0.15)',
                background: 'rgba(2,6,23,0.5)',
                padding: '20px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}>
                <p style={{ margin: '0 0 12px 8px', color: '#F9FAFB', fontSize: '0.95rem', fontWeight: 700 }}>
                  設定
                </p>
                {SETTINGS_SECTIONS.map((sec) => {
                  const active = settingsSection === sec.id
                  return (
                    <button
                      key={sec.id}
                      onClick={() => setSettingsSection(sec.id)}
                      style={{
                        background: active ? 'rgba(139,92,246,0.18)' : 'transparent',
                        border: active ? '1px solid rgba(139,92,246,0.4)' : '1px solid transparent',
                        borderRadius: 8,
                        padding: '9px 12px',
                        textAlign: 'left',
                        cursor: 'pointer',
                        color: active ? '#c4b5fd' : '#94a3b8',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
                      }}
                      onMouseLeave={(e) => {
                        if (!active) e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      {sec.label}
                    </button>
                  )
                })}
              </div>

              {/* ===== 右コンテンツ ===== */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                {/* 閉じるボタン */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '14px 16px 0' }}>
                  <button
                    onClick={() => setShowSettings(false)}
                    aria-label="設定を閉じる"
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(148,163,184,0.15)',
                      borderRadius: '50%',
                      width: 32,
                      height: 32,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      color: '#94a3b8',
                      flexShrink: 0,
                    }}
                  >
                    <X size={15} />
                  </button>
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: '4px 20px 24px' }}>
                  {settingsLoading && <p role="status" style={{ color: '#cbd5e1', fontSize: '0.8rem' }}>利用できる設定を読み込んでいます…</p>}
                  {settingsError && <div role="alert" style={{ color: '#fda4af', fontSize: '0.8rem', marginBottom: 16 }}>
                    <p>{settingsError} 既定の設定で会話できます。</p>
                    <button type="button" onClick={onReloadSettings} style={{ padding: '6px 12px', borderRadius: 6, cursor: 'pointer' }}>設定を再読み込み</button>
                  </div>}
                  {/* --- 一般 --- */}
                  {settingsSection === 'general' && (
                    <div>
                      {sectionHeading('一般', '表示・全般の設定')}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 12,
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(148,163,184,0.1)',
                        borderRadius: 10,
                        padding: '12px 14px',
                      }}>
                        <div>
                          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '0.88rem', fontWeight: 600 }}>
                            QRコード表示
                          </p>
                          <p style={{ margin: '2px 0 0', color: '#475569', fontSize: '0.73rem', lineHeight: 1.4 }}>
                            回答内のURLをQRコードで表示する
                          </p>
                        </div>
                        <button
                          onClick={() => onQrEnabledChange?.(!qrEnabled)}
                          aria-label="QRコード表示切替"
                          style={{
                            position: 'relative',
                            width: 46,
                            height: 26,
                            borderRadius: 13,
                            border: 'none',
                            cursor: 'pointer',
                            flexShrink: 0,
                            background: qrEnabled ? 'rgba(139,92,246,0.9)' : 'rgba(148,163,184,0.3)',
                            transition: 'background 0.2s ease',
                          }}
                        >
                          <span style={{
                            position: 'absolute',
                            top: 3,
                            left: qrEnabled ? 23 : 3,
                            width: 20,
                            height: 20,
                            borderRadius: '50%',
                            background: '#fff',
                            transition: 'left 0.2s ease',
                          }} />
                        </button>
                      </div>

                      {/* アバター映像の切り抜き倍率。UE のカメラは動かないので、
                          構図そのものを変えたいときは UE 側の /set-camera を使う。 */}
                      <div style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(148,163,184,0.1)',
                        borderRadius: 10,
                        padding: '12px 14px',
                        marginTop: 10,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '0.88rem', fontWeight: 600 }}>
                            アバター表示倍率
                          </p>
                          <span style={{ color: '#a78bfa', fontSize: '0.8rem', fontWeight: 600 }}>
                            {zoom.toFixed(1)}x
                          </span>
                        </div>
                        <p style={{ margin: '2px 0 10px', color: '#475569', fontSize: '0.73rem', lineHeight: 1.4 }}>
                          配信映像の切り抜き範囲を変える（UEのカメラは動かない）
                        </p>
                        <input
                          type="range"
                          min={ZOOM.min}
                          max={ZOOM.max}
                          step={ZOOM.step}
                          value={zoom}
                          onChange={(e) => onZoomChange?.(clampZoom(Number(e.target.value)))}
                          aria-label="アバター表示倍率"
                          style={{ width: '100%', accentColor: '#8b5cf6', cursor: 'pointer' }}
                        />
                      </div>

                      <div style={{ marginTop: 20 }}>
                        {sectionHeading('リップシンク', 'アバターの口の動かし方')}
                        {renderRadioList(LIP_SYNC_OPTIONS, lipSyncMode, (v) => onLipSyncModeChange?.(v as LipSyncMode))}
                      </div>
                    </div>
                  )}

                  {/* --- モデル --- */}
                  {settingsSection === 'model' && (
                    <div>
                      {sectionHeading('モデル', 'この会話で最初に応答するAIのモデル')}
                      {settingsCatalog && renderRadioList(settingsCatalog.llm_models.map((model) => ({ value: model.id, label: model.label, description: model.supports_temperature ? '応答の温度を変更できます' : 'このモデルでは応答の温度を変更できません' })), mainModel, (v) => onMainModelChange?.(v))}
                      <p style={{ color: '#94a3b8', fontSize: '0.75rem', lineHeight: 1.6 }}>専門担当AIと学内検索の回答モデルは、この選択では変わりません。</p>
                    </div>
                  )}

                  {(settingsSection === 'inference' || settingsSection === 'audio') && (
                    <div>
                      {sectionHeading(settingsSection === 'audio' ? '音声' : '推論・検索', 'この画面から送る会話に適用する設定')}
                      {settingsCatalog && <InferenceFields catalog={settingsCatalog} draft={inferenceDraft} modelId={mainModel} mode={appMode}
                        section={settingsSection} onChange={(key, value) => onInferenceChange?.(key, value)} />}
                    </div>
                  )}

                  {/* --- フィラー --- */}
                  {settingsSection === 'filler' && (
                    <div>
                      {sectionHeading('フィラー', '応答を待つ間のつなぎ発話')}
                      {appMode === 'assistant' && <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>一般AIモードではフィラーを使いません。</p>}
                      {appMode === 'ceremony' && <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>式典モードでは外部フィラーを使いません。</p>}
                      <fieldset disabled={appMode === 'assistant'} style={{ border: 0, padding: 0, margin: 0, opacity: appMode === 'assistant' ? 0.5 : 1 }}>
                      {renderRadioList(FILLER_MODE_OPTIONS, fillerMode, (v) => onFillerModeChange?.(v))}

                      {/* 外部動的フィラー選択時のみ、生成モデルを選べる */}
                      {fillerMode === 'dynamic' && (
                        <div style={{ marginTop: 20 }}>
                          <p style={{ margin: '0 0 8px', color: '#cbd5e1', fontSize: '0.82rem', fontWeight: 700 }}>
                            動的フィラー生成モデル
                          </p>
                          {settingsCatalog && renderRadioList(settingsCatalog.filler_models.map((model) => ({ value: model.id, label: model.label, description: '応答を待つ間のつなぎ発話に使用します' })), fillerModel, (v) => onFillerModelChange?.(v))}
                        </div>
                      )}
                      </fieldset>
                    </div>
                  )}

                  {/* --- モード --- */}
                  {settingsSection === 'mode' && (
                    <div>
                      {sectionHeading('モード', '会話するAIの役割と応答スタイル')}
                      {renderRadioList(
                        [
                          { value: 'general', label: '学長モード', description: '学長AIとして会話し、必要に応じて学内情報や専門担当AIを使います' },
                          { value: 'assistant', label: '一般AIモード', description: '学長の役割を持たないAIと会話します。学内検索とフィラーは使いません' },
                          { value: 'ceremony', label: '式典モード', description: '学長AIが式典向けに簡潔に応答します。外部フィラーは使いません' },
                        ],
                        appMode,
                        (v) => {
                          if (v === 'general' || v === 'assistant' || v === 'ceremony') onModeChange?.(v)
                        },
                      )}
                    </div>
                  )}

                  <p style={{ margin: '20px 0 0', color: '#94a3b8', fontSize: '0.75rem', textAlign: 'center', lineHeight: 1.5 }}>
                    次の送信から、この画面の会話に適用します。他の利用者の設定は変わりません。
                  </p>
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
      </Flex>

      {/* Body: ここを ScrollableBody に変更 */}
      <ScrollableBody
        ref={scrollContainerRef}
        $flex_direction="column"
        $flex="1"
        $overflow="auto"
        $padding="10px"
        $gap="0px"
        $backgroundColor="transparent"
      >
        {hasMessages ? (
          <ChatList
            messages={messages}
            width="100%"
            height="auto"
            variant="futuristic"
            speakingMessageId={speakingMessageId}
          />
        ) : (
          <InitialChatView
            onTemplateClick={(text) => {
              onSend(text)
            }}
          />
        )}
      </ScrollableBody>

      {/* Footer ... */}
      <Flex
        $width="100%"
        $padding="10px 16px 18px"
        $backgroundColor="rgba(15,23,42,0.92)"
        style={{
          borderTop: '1px solid rgba(148,163,184,0.18)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Footerの中身... */}
        <Flex $flex_direction="column" $width="100%" $gap="10px">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <ModeToggle mode={inputMode} onChange={handleModeChange} />
            {inputMode === 'voice' && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'rgba(15,23,42,0.6)',
                  borderRadius: 8,
                  padding: 4,
                  gap: 4,
                  border: '1px solid rgba(148,163,184,0.1)',
                }}
              >
                <button
                  onClick={() => setVoiceMode('ptt')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    background: voiceMode === 'ptt' ? 'rgba(59,130,246,0.2)' : 'transparent',
                    color: voiceMode === 'ptt' ? '#60A5FA' : '#9CA3AF',
                    border: voiceMode === 'ptt' ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent',
                    transition: 'all 0.2s ease',
                  }}
                >
                  Push-to-Talk
                </button>
                <button
                  onClick={() => setVoiceMode('vad')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    background: voiceMode === 'vad' ? 'rgba(59,130,246,0.2)' : 'transparent',
                    color: voiceMode === 'vad' ? '#60A5FA' : '#9CA3AF',
                    border: voiceMode === 'vad' ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent',
                    transition: 'all 0.2s ease',
                  }}
                >
                  自動 (VAD)
                </button>
              </div>
            )}
          </div>
          {errorMessage && <p role="alert" style={{ color: '#fda4af', fontSize: '0.8rem', margin: 0 }}>{errorMessage}</p>}
          {inputMode === 'text' ? (
            <ChatInputArea
              key={speechSession}
              sttModel={inferenceDraft.stt_model}
              value={inputValue}
              onChange={onChange}
              onMicClick={onMicClick}
              onSend={onSend}
              isSending={isSending}
              disabled={disabled}
              mode="futuristic"
            />
          ) : (
            <VoiceInputArea
              key={speechSession}
              sttModel={inferenceDraft.stt_model}
              disabled={disabled}
              isAISpeaking={Boolean(speakingMessageId)}
              onInterrupt={onInterrupt}
              voiceMode={voiceMode}
              onTranscript={(text) => {
                onSend(text)
              }}
            />
          )}
          {/* 免責テキスト */}
          <p
            style={{
              margin: 0,
              textAlign: 'center',
              fontSize: '0.72rem',
              color: 'rgba(148,163,184,0.55)',
              lineHeight: 1.4,
            }}
          >
            学長AIはAIによる回答です。不正確な情報が含まれる場合があります。
          </p>
        </Flex>
      </Flex>
    </Flex>
  )
}
