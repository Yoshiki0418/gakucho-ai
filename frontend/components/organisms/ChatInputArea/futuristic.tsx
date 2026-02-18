'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Mic, Send } from 'lucide-react'
import Box from '@/components/styles/Box'
import InputText from '@/components/atoms/InputText'
import { useSpeechRecognition } from '@/features/speech/hooks/useSpeechRecognition'

interface ChatInputAreaProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onSend: (value: string) => void
  isSending?: boolean
  disabled?: boolean
}

/**
 * フューチャー UI モードの ChatInputArea
 * - UI生成AI の ChatInput デザインをベースに
 * - 右側に Mic ＋ Send 丸ボタン
 * - フォーカス時のガラスカード＆青いフォーカスリング
 * - 既存の音声認識ロジック(useSpeechRecognition)は継承
 */
export default function FuturisticChatInputArea({
  value,
  onChange,
  onSend,
  isSending = false,
  disabled = false,
}: ChatInputAreaProps) {
  const [inputValue, setInputValue] = useState(value)
  const [isFocused, setIsFocused] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const lastRecognizedRef = useRef('')

  const { isListening, start, stop, reset, syncExternalText } =
    useSpeechRecognition({
      continuous: true,
      onResult: (text, isFinal) => {
        if (isFinal && text !== lastRecognizedRef.current) {
          lastRecognizedRef.current = text
          setInputValue((prev) => (prev + ' ' + text).trim())
        }
      },
      onError: (err) => console.error('SpeechRecognition Error:', err),
    })

  useEffect(() => {
    setInputValue(value)
    syncExternalText(value)
  }, [value])

  useEffect(() => {
    onChange({ target: { value: inputValue } } as any)
  }, [inputValue])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setInputValue(newValue)
    syncExternalText(newValue)
  }

  // Mic ボタンクリック
  const handleMicClick = () => {
    if (disabled) return

    if (isListening) {
      // 停止
      stop()
      setIsRecording(false)
    } else {
      // 開始
      syncExternalText(inputValue)
      lastRecognizedRef.current = ''
      start()
      setIsRecording(true)
    }
  }

  // 送信（ボタン or Enter）
  const handleSend = async () => {
    const text = inputValue.trim()
    if (disabled || isSending || !text) return

    onSend(text)

    // 完全リセット
    stop()
    reset()
    setIsRecording(false)
    setInputValue('')
    lastRecognizedRef.current = ''
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleSend()
  }

  // 音声認識終了時
  useEffect(() => {
    if (!isListening) setIsRecording(false)
  }, [isListening])

  const canSend = !!inputValue.trim() && !disabled && !isSending

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%' }}>
      <Box
        $width="100%"
        $borderRadius="14px"
        $padding="4px 4px"
        $backgroundColor="transparent"
        style={{
          position: 'relative',
        }}
      >
        {/* 外側のガラスカードコンテナ */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            padding: '4px 0',
            borderRadius: 14,
            background: 'rgba(15, 23, 42, 0.8)',
            backdropFilter: 'blur(16px)',
            border: isFocused
              ? '2px solid rgba(59, 130, 246, 0.5)'
              : '1px solid rgba(148, 163, 184, 0.15)',
            boxShadow: isFocused
              ? '0 0 0 4px rgba(59,130,246,0.12), 0 8px 24px rgba(0,0,0,0.45)'
              : '0 4px 18px rgba(0,0,0,0.5)',
            transition:
              'border 0.2s ease, box-shadow 0.2s ease, background 0.2s ease',
          }}
        >
          {/* テキスト入力 */}
          <InputText
            value={inputValue}
            onChange={handleInputChange}
            placeholder="話しかけるか入力してください..."
            disabled={disabled}
            $background="transparent"
            $backgroundColor="transparent"
            $border="none"
            $borderRadius="14px"
            $width="100%"
            $height="56px"
            $color="#ffffff"
            $variants="chat"
            style={{
              fontSize: '0.95rem',
              paddingLeft: '1.2rem',
              paddingRight: '5.4rem',
              outline: 'none',
            }}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
          />

          {/* 右側の Mic + Send ボタン */}
          <div
            style={{
              position: 'absolute',
              right: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            {/* Mic ボタン */}
            <button
              type="button"
              onClick={handleMicClick}
              disabled={disabled}
              style={{
                width: 40,
                height: 40,
                borderRadius: '999px',
                border: isRecording
                  ? '1px solid rgba(59,130,246,0.6)'
                  : '1px solid rgba(148,163,184,0.3)',
                background: isRecording
                  ? 'radial-gradient(circle, rgba(59,130,246,0.45) 0%, rgba(15,23,42,0.95) 65%)'
                  : 'linear-gradient(135deg, rgba(51,65,85,0.9), rgba(15,23,42,0.95))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.4 : 1,
                boxShadow: isRecording
                  ? '0 0 18px rgba(59,130,246,0.7)'
                  : '0 0 10px rgba(15,23,42,0.8)',
                transition: 'all 0.18s ease',
              }}
            >
              <Mic
                size={18}
                color={isRecording ? '#bfdbfe' : '#e5e7eb'}
                style={{
                  transform: isRecording ? 'scale(1.05)' : 'scale(1.0)',
                }}
              />
            </button>

            {/* Send ボタン */}
            <button
              type="submit"
              disabled={!canSend}
              style={{
                width: 40,
                height: 40,
                borderRadius: '999px',
                border: 'none',
                background: canSend
                  ? 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 45%, #4F46E5 100%)'
                  : 'linear-gradient(135deg, rgba(37,99,235,0.4), rgba(37,99,235,0.3))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: canSend ? 'pointer' : 'not-allowed',
                opacity: canSend ? 1 : 0.45,
                boxShadow: canSend
                  ? '0 0 16px rgba(59,130,246,0.5)'
                  : '0 4px 10px rgba(15,23,42,0.8)',
                transition: 'background 0.18s ease, box-shadow 0.18s ease, transform 0.1s ease',
              }}
            >
              <Send size={16} color="#ffffff" />
            </button>
          </div>
        </div>
      </Box>
    </form>
  )
}
