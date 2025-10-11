'use client'

import React from 'react'
import Flex from '@/components/styles/Flex'
import { ChatList } from '@/components/organisms/ChatList'
import ChatInputArea from '@/components/organisms/ChatInputArea'

interface ChatPanelProps {
  messages: ReadonlyArray<{
    id: string
    text: string
    role: 'user' | 'assistant'
    name?: string
    avatarSrc?: string
  }>
  inputValue: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  onSend: () => void
  isSending?: boolean
  disabled?: boolean
}

export default function ChatPanel({
  messages,
  inputValue,
  onChange,
  onMicClick,
  onSend,
  isSending = false,
  disabled = false,
}: ChatPanelProps) {
  return (
    <Flex
      $flex_direction="column"
      $justify_content="space-between"
      $backgroundColor="#000"
      $borderRadius="16px"
      $width="35%"
      $height="100%"
      $padding="16px"
      $paddingBottom='20px'
      $gap="12px" 
      style={{
}}
    >
      {/* チャット一覧 */}
      <Flex
        $flex_direction="column"
        $flex="1"
        $overflow="auto"
        $gap="8px"
        $backgroundColor="transparent"
        $borderRadius="12px"
        $padding="8px"
      >
        <ChatList messages={messages} width="100%" height="100%" variant='futuristic' animateGlow={true} />
      </Flex>

      {/* 入力エリア */}
      <ChatInputArea
        value={inputValue}
        onChange={onChange}
        onMicClick={onMicClick}
        onSend={onSend}
        isSending={isSending}
        disabled={disabled}
        mode='futuristic'
      />
    </Flex>
  )
}
