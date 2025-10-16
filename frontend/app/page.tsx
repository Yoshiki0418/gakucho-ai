'use client'

import React, { useState } from 'react'
import ChatPanel from '@/components/organisms/ChatPanel'
import { useTextChat } from '@/features/text-chat/hooks/useTextChat'

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)

  const { messages, startChat, speakingMessageId } =
    useTextChat('/api/text-chat/char-stream')

  const handleMicClick = () => {
    console.log('🎙️ Mic clicked')
  }

  const handleSend = () => {
    if (!inputValue.trim()) return
    setIsSending(true)
    startChat(inputValue)
    setIsSending(false)
    setInputValue('')
  }

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        height: '100vh',
        backgroundColor: '#000',
      }}
    >
      <section
        style={{
          display: 'flex',
          justifyContent: 'flex-start',
          alignItems: 'stretch',
          height: '100vh',
          width: '100%',
        }}
      >
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onMicClick={handleMicClick}
          onSend={handleSend}
          isSending={isSending}
          speakingMessageId={speakingMessageId}
        />
      </section>
    </main>
  )
}
