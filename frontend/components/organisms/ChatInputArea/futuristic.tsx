'use client'

import React, { useState } from 'react'
import Box from '@/components/styles/Box'
import InputWithMic from '@/components/molecules/InputWithMic'
import Button from '@/components/atoms/Button'

interface ChatInputAreaProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  onSend: () => void
  isSending?: boolean
  disabled?: boolean
}

export default function ChatInputArea({
  value,
  onChange,
  onMicClick,
  onSend,
  isSending = false,
  disabled = false,
}: ChatInputAreaProps) {
  const [energyActive, setEnergyActive] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  /** 🎙️ マイククリック */
  const handleMicClick = () => {
    setIsRecording((prev) => !prev)
    onMicClick?.()
  }

  /** 🚀 送信時アニメーション */
  const handleSendClick = async () => {
    if (disabled || isSending) return
    setEnergyActive(true)
    setTimeout(() => setEnergyActive(false), 1000)
    onSend()
  }

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
        {/* ✨ エネルギー波紋 */}
        {energyActive && <div className="energy-wave" />}

        {/* 🎧 入力部分 */}
        <InputWithMic
          value={value}
          onChange={onChange}
          onMicClick={handleMicClick}
          disabled={disabled}
          placeholder="ここに入力..."
        />

        {/* 🚀 送信ボタン */}
        <Button
          type="button"
          onClick={handleSendClick}
          disabled={disabled || isSending}
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

      {/* 💫 外枠グラデーション定義 */}
      <style jsx>{`
        .chat-area {
          position: relative;
          border-radius: 24px;
          padding: 3px; /* 光の厚み */
          background: rgba(0, 0, 0, 0.7);
          transition: all 0.4s ease;
        }

        /* 🔥 録音中だけ外枠が流れる */
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
          padding: 3px;
          border-radius: 24px;
          box-shadow: 0 0 20px rgba(0, 170, 255, 0.5);
        }

        /* ChatInputArea全体のBox部分 */
        .chat-area > :global(div) {
          background: #1b1b1b;
          border-radius: 20px;
          height: 100%;
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
          z-index: 0;
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
