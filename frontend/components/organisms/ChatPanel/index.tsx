'use client'

import React, { useState, useRef, useEffect } from 'react'
import styled from 'styled-components'
import { RefreshCcw, Settings } from 'lucide-react'
import Flex from '@/components/styles/Flex'
import { ChatList } from '@/components/organisms/ChatList'
import { InitialChatView } from '@/components/organisms/InitialChatView'
import ChatInputArea from '@/components/organisms/ChatInputArea'
import { ModeToggle, InputMode } from '@/components/molecules/ModeToggle'
import { VoiceInputArea } from '@/components/organisms/VoiceInputArea'

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
  appMode?: 'general' | 'ceremony'
  onToggleMode?: () => void
  width?: number | string
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
  onToggleMode,
  width = '35%',
}: ChatPanelProps) {
  const hasMessages = messages.length > 0
  const [internalMode, setInternalMode] = useState<InputMode>('text')
  const inputMode = inputModeProp ?? internalMode
  const [voiceMode, setVoiceMode] = useState<'ptt' | 'vad'>('ptt')

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

        {/* 右側：ボタン群 */}
        <Flex $flex_direction="row" $gap="8px">
          {onToggleMode && (
            <button
              onClick={() => onToggleMode()}
              style={{
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                background: appMode === 'ceremony' ? 'rgba(59,130,246,0.20)' : 'rgba(255,255,255,0.05)',
                border: appMode === 'ceremony' ? '1px solid rgba(59,130,246,0.4)' : '1px solid rgba(148,163,184,0.15)',
                borderRadius: '16px',
                padding: '0 12px',
                height: 38,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: '0.25s ease',
                color: appMode === 'ceremony' ? '#60a5fa' : '#cbd5e1',
                fontSize: '0.85rem',
                fontWeight: 600,
                gap: '6px',
              }}
              title={appMode === 'ceremony' ? '現在のモード：式典モード（フィラー・QR非表示）' : '現在のモード：一般モード'}
              onMouseEnter={(e) => {
                if (appMode !== 'ceremony') {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.1)'
                  e.currentTarget.style.border = '1px solid rgba(148,163,184,0.25)'
                }
              }}
              onMouseLeave={(e) => {
                if (appMode !== 'ceremony') {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
                  e.currentTarget.style.border = '1px solid rgba(148,163,184,0.15)'
                }
              }}
            >
              <Settings size={14} />
              {appMode === 'ceremony' ? 'モード：式典' : 'モード：一般'}
            </button>
          )}

          <button
            onClick={() => onResetChat?.()}
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
          {inputMode === 'text' ? (
            <ChatInputArea
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
