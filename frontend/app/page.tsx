'use client'

import React, { useState } from 'react'
import ChatPanel from '@/components/organisms/ChatPanel'
import { useTextChat } from '@/features/text-chat/hooks/useTextChat'
import { AvatarPanel } from '@/components/organisms/AvatarPanel'

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)

  const { messages, startChat, speakingMessageId, resetChat, avatarFrameSrc} =
  useTextChat('/api/text-chat/char-stream-agent')

  const handleMicClick = () => {
    console.log('🎙️ Mic clicked')
  }

  const handleSend = async (value: string) => {
    const message = value.trim()
    if (!message) return

    setIsSending(true)
    try {
      await startChat(message)
    } finally {
      setIsSending(false)
    }

    setInputValue('')
  }

  const handleTemplateClick = (text: string) => {
    setInputValue(text)
    handleSend(text)
  }

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        height: '100vh',
        backgroundColor: '#000',
        overflow: 'hidden',
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
          onTemplateClick={handleTemplateClick}
          onSend={handleSend}      
          isSending={isSending}
          onResetChat={resetChat} 
          speakingMessageId={speakingMessageId}
        />
        <AvatarPanel frameSrc={avatarFrameSrc} />
      </section>
    </main>
  )
}