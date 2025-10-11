'use client'

import React from 'react'
import StandardChatInputArea from './standard'
import FuturisticChatInputArea from './futuristic'

interface ChatInputAreaProps {
  mode?: 'standard' | 'futuristic' // どちらを使うか指定
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  onSend: () => void
  isSending?: boolean
  disabled?: boolean
}

/**
 * ChatInputArea コンポーネント（UIモード切り替え可能）
 * 
 * mode="standard" → 通常デザイン
 * mode="futuristic" → 光るフューチャーデザイン
 */
export default function ChatInputArea({
  mode = 'standard',
  ...props
}: ChatInputAreaProps) {
  if (mode === 'futuristic') {
    return <FuturisticChatInputArea {...props} />
  }
  return <StandardChatInputArea {...props} />
}
