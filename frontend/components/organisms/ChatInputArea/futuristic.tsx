'use client'

import React, { useState, useEffect, useRef } from 'react'
import Box from '@/components/styles/Box'
import InputWithMic from '@/components/molecules/InputWithMic'
import Button from '@/components/atoms/Button'
import { useSpeechRecognition } from '@/features/speech/hooks/useSpeechRecognition'

interface ChatInputAreaProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onSend: () => void
  isSending?: boolean
  disabled?: boolean
}

export default function ChatInputArea({
  value,
  onChange,
  onSend,
  isSending = false,
  disabled = false,
}: ChatInputAreaProps) {
  const [inputValue, setInputValue] = useState(value)
  const [isRecording, setIsRecording] = useState(false)
  const [energyActive, setEnergyActive] = useState(false)
  const lastRecognizedRef = useRef('')

  const { isListening, start, stop, reset, syncExternalText } =
    useSpeechRecognition({
      continuous: true,
      onResult: (text, isFinal) => {
        if (isFinal && text !== lastRecognizedRef.current) {
          lastRecognizedRef.current = text
          // 最新の state をもとに追記
          setInputValue((prev) => {
            const newText = (prev + ' ' + text).trim()
            return newText
          })
        }
      },
      onError: (err) => console.error('SpeechRecognition Error:', err),
    })

  /** 手入力で同期 */
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setInputValue(newValue)
    syncExternalText(newValue)
  }

  /** state → 親同期 (useEffectで確実に) */
  useEffect(() => {
    onChange({ target: { value: inputValue } } as any)
  }, [inputValue])

  /** マイククリック */
  const handleMicClick = () => {
    if (isListening) {
      stop()
      setIsRecording(false)
    } else {
      syncExternalText(inputValue) // 今の入力内容を保持してから開始
      lastRecognizedRef.current = ''
      start()
      setIsRecording(true)
    }
  }

  /** 送信 */
  const handleSendClick = async () => {
    if (disabled || isSending || !inputValue.trim()) return

    setEnergyActive(true)
    setTimeout(() => setEnergyActive(false), 1000)
    onSend()

    // 完全リセット
    stop()
    reset()
    setIsRecording(false)
    setInputValue('')
    lastRecognizedRef.current = ''
  }

  /** 音声認識終了時のUI更新 */
  useEffect(() => {
    if (!isListening) setIsRecording(false)
  }, [isListening])

  return (
    <div className={`chat-area ${isRecording ? 'recording' : ''}`}>
      <Box
        $display="flex"
        $width="100%"
        $backgroundColor="#1b1b1b"
        $borderRadius="20px"
        $padding="16px"
        $alignItems="center"
        $position="relative"
        style={{
          flexDirection: 'column',
          overflow: 'hidden',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(0,150,255,0.3)',
          boxShadow:
            'inset 0 1px 6px rgba(255,255,255,0.05), 0 0 20px rgba(0,150,255,0.3)',
        }}
      >
        {energyActive && <div className="energy-wave" />}

        <InputWithMic
          value={inputValue}
          onChange={handleInputChange}
          onMicClick={handleMicClick}
          disabled={disabled}
          placeholder="話しかけるか入力してください..."
        />

        <Button
          type="button"
          onClick={handleSendClick}
          disabled={disabled || isSending || !inputValue.trim()}
          $variants="Primary"
          $backColor="#007AFF"
          $hover_color="#339DFF"
          $color="#fff"
          $borderRadius="16px"
          $padding="0px"
          $fontSize="1rem"
          $width="90%"
          style={{
            fontWeight: 600,
            opacity: disabled || isSending ? 0.6 : 1,
            cursor: disabled || isSending ? 'not-allowed' : 'pointer',
            boxShadow:
              '0 0 10px rgba(0,122,255,0.6), 0 0 20px rgba(0,122,255,0.3)',
            transition: 'box-shadow 0.3s ease',
          }}
        >
          {isSending ? '送信中...' : '質問する'}
        </Button>
      </Box>

      {/* アニメーション */}
      <style jsx>{`
        .chat-area {
          position: relative;
          border-radius: 24px;
          padding: 3px;
          background: rgba(0, 0, 0, 0.7);
          transition: all 0.4s ease;
        }

        .chat-area.recording {
          background: linear-gradient(
            90deg,
            #00aaff,
            #b026ff,
            #00ffff,
            #00aaff
          );
          background-size: 300% 300%;
          animation: borderFlow 3s linear infinite;
          box-shadow: 0 0 20px rgba(0, 170, 255, 0.5);
        }

        @keyframes borderFlow {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }

        .energy-wave {
          position: absolute;
          bottom: 15%;
          left: 50%;
          transform: translateX(-50%);
          width: 20%;
          height: 20%;
          background: radial-gradient(
            circle,
            rgba(0, 170, 255, 0.5) 0%,
            rgba(0, 170, 255, 0.2) 30%,
            rgba(0, 170, 255, 0) 70%
          );
          border-radius: 50%;
          pointer-events: none;
          animation: energyPulse 1s ease-out forwards;
        }

        @keyframes energyPulse {
          0% {
            transform: translateX(-50%) scale(0.2);
            opacity: 0.9;
          }
          60% {
            transform: translateX(-50%) scale(1.4);
            opacity: 0.4;
          }
          100% {
            transform: translateX(-50%) scale(2.2);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  )
}
