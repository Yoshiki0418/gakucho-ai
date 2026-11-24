'use client'

import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Mic, Square, Volume2 } from 'lucide-react'
import { useSpeechRecognition } from '@/features/speech/hooks/useSpeechRecognition'

type VoiceInputAreaProps = {
  onTranscript: (text: string) => void
  disabled?: boolean
  isAISpeaking?: boolean
  onInterrupt?: () => void
  voiceMode?: 'ptt' | 'vad'
  sttModel?: string
}

export const VoiceInputArea: React.FC<VoiceInputAreaProps> = ({
  onTranscript, disabled = false, isAISpeaking = false, onInterrupt,
  voiceMode = 'ptt', sttModel = 'browser',
}) => {
  const [previewText, setPreviewText] = useState('')
  const [error, setError] = useState('')
  const automatic = voiceMode === 'vad' && sttModel === 'browser'
  const { isListening, isStarting, isTranscribing, start, stop, reset } = useSpeechRecognition({
    model: sttModel,
    autoSubmit: automatic,
    onResult: (text, final) => {
      setPreviewText(final ? '' : text)
      if (text && isAISpeaking) onInterrupt?.()
      if (final && text.trim()) onTranscript(text.trim())
    },
    onError: (message) => { setError(message); setPreviewText('') },
  })

  useEffect(() => {
    if (disabled) {
      reset()
      setPreviewText('')
    }
  }, [disabled, reset])
  useEffect(() => {
    setError('')
    setPreviewText('')
  }, [sttModel, voiceMode])

  const busy = isStarting || isTranscribing
  const active = isListening || busy
  const toggleListening = () => {
    setError('')
    if (active) {
      stop()
    } else {
      setPreviewText('')
      if (isAISpeaking) onInterrupt?.()
      start()
    }
  }
  const status = isStarting ? 'マイクの使用を確認しています…'
    : isTranscribing ? '文字起こし中…（ボタンでキャンセル）'
      : isListening ? automatic ? 'お話しください。発話が確定すると送信します' : '録音中… もう一度押すと送信します'
        : isAISpeaking ? 'AIが話しています…'
          : automatic ? 'マイクボタンを押して話し始めてください'
            : 'ボタンを押して話し、もう一度押して送信'

  return (
    <div style={{ width: '100%', padding: '4px 0' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, minHeight: 56,
        borderRadius: 14, background: 'rgba(15,23,42,0.8)',
        border: active ? '2px solid rgba(59,130,246,0.5)' : '1px solid rgba(148,163,184,0.15)',
        padding: '8px 10px 8px 14px',
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div role="status" aria-live="polite" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#fff' }}>
            {isAISpeaking && !active ? <Volume2 size={16} /> : <span aria-hidden="true" style={{
              width: 8, height: 8, borderRadius: '50%', background: active ? '#ef4444' : '#6b7280',
            }} />}
            {status}
          </div>
          <div aria-hidden="true" style={{ display: 'flex', gap: 2, height: 18, alignItems: 'center' }}>
            {Array.from({ length: 32 }, (_, index) => <motion.div key={index}
              style={{ width: 3, borderRadius: 999, background: isListening ? '#60a5fa' : '#374151' }}
              animate={{ opacity: isListening ? [0.4, 1, 0.4] : 1, height: 2 }}
              transition={{ repeat: isListening ? Infinity : 0, duration: 1.2, delay: index * 0.03 }} />)}
          </div>
          {previewText && <p style={{ margin: 0, color: '#e5e7eb', fontSize: 12, overflowWrap: 'anywhere' }}>「{previewText}」</p>}
          {sttModel !== 'browser' && <p style={{ margin: '2px 0 0', fontSize: 11, color: '#94a3b8' }}>
            Whisperは録音停止後に文字起こしして送信します（最大60秒）。
          </p>}
        </div>
        <motion.button type="button" onClick={toggleListening} disabled={disabled}
          aria-label={active ? busy ? '音声入力をキャンセル' : '録音を終了して送信' : '音声入力を開始'}
          whileHover={{ scale: disabled ? 1 : 1.05 }} whileTap={{ scale: disabled ? 1 : 0.95 }}
          style={{
            width: 48, height: 48, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '1px solid rgba(255,255,255,0.12)', cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.5 : 1, flexShrink: 0,
            background: active ? 'linear-gradient(135deg,#ef4444,#dc2626)' : 'linear-gradient(135deg,#3b82f6,#2563eb)',
          }}>
          {active ? <Square size={22} color="#fff" /> : <Mic size={26} color="#fff" />}
        </motion.button>
      </div>
      {error && <p role="alert" style={{ color: '#fca5a5', fontSize: 12, margin: '6px 0 0' }}>{error}</p>}
    </div>
  )
}
