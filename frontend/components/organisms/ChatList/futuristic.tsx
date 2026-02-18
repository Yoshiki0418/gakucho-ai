'use client'

import React, { useEffect, useMemo, useRef } from 'react'
import Flex from '@/components/styles/Flex'
import { MessageBubble } from '@/components/organisms/MessageBubble'

type ChatMessage = {
  id: string
  name?: string
  text: string
  avatarSrc?: string
  role?: 'user' | 'assistant'
}

type ChatListFuturisticProps = {
  messages: readonly ChatMessage[]
  width?: string
  height?: string
  speakingMessageId?: string | null
}

export const ChatListFuturistic: React.FC<ChatListFuturisticProps> = ({
  messages,
  width = '100%',
  height = '100%',
  speakingMessageId = null,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const lastMessageKey = useMemo(() => {
    const last = messages[messages.length - 1]
    if (!last) return 'none'
    return `${last.id ?? 'no-id'}:${last.text?.length ?? 0}`
  }, [messages])

  useEffect(() => {
    if (!bottomRef.current) return
    bottomRef.current.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    })
  }, [lastMessageKey])

  return (
    <Flex
      $flex_direction="column"
      $width={width}
      $height={height}
      $gap="14px"
      $padding="20px"
      $overflow="visible"
      $backgroundColor="transparent"
      $borderRadius="0px"
      $boxShadow="none"
      style={{
        position: 'relative',
        backdropFilter: 'none',
        border: 'none',
      }}
    >
      {messages.map((msg, index) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          index={index}
          isSpeaking={msg.id === speakingMessageId}
        />
      ))}

      {/* 一番下のダミー – ここまでスクロールさせる */}
      <div ref={bottomRef} />
    </Flex>
  )
}