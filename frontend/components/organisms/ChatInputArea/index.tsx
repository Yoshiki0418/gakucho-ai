'use client'

import React from 'react'
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
  return (
    <Box
      $display="flex"
      $width="100%"
      $backgroundColor="#1b1b1b"
      $borderRadius="20px"
      $padding="16px"
      $alignItems="center" 
      style={{ flexDirection: 'column'}}
    >
      {/* 入力 + マイク */}
      <InputWithMic
        value={value}
        onChange={onChange}
        onMicClick={onMicClick}
        disabled={disabled}
        placeholder="ここに入力..."
      />

      {/* 送信ボタン（横幅いっぱい・下配置） */}
      <Button
        type="button"
        onClick={onSend}
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
          whiteSpace: 'nowrap',
          opacity: disabled || isSending ? 0.6 : 1,
          transition: 'opacity 0.2s ease',
          cursor: disabled || isSending ? 'not-allowed' : 'pointer',
        }}
      >
        {isSending ? '送信中...' : '質問する'}
      </Button>
    </Box>
  )
}
