'use client'

import React, { useState } from 'react'
import ChatPanel from '@/components/organisms/ChatPanel'
import { useTextChat } from '@/features/text-chat/hooks/useTextChat'
import { AvatarPanel } from '@/components/organisms/AvatarPanel'
import { QRCodeDisplay } from '@/components/organisms/QRCodeDisplay'

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [closedUrls, setClosedUrls] = useState<Set<string>>(new Set())

  const { messages, startChat, speakingMessageId, resetChat, avatarFrameSrc, latestUrl, interruptChat } =
    useTextChat('/api/text-chat/char-stream-orchestrator')

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



  // ユーザーが閉じたURLでなければ表示する
  const displayUrl = latestUrl && !closedUrls.has(latestUrl) ? latestUrl : null

  const handleCloseQRCode = () => {
    if (latestUrl) {
      setClosedUrls((prev) => new Set(prev).add(latestUrl))
    }
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
          onInterrupt={interruptChat}
        />
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <AvatarPanel frameSrc={avatarFrameSrc} />
          <QRCodeDisplay url={displayUrl} onClose={handleCloseQRCode} />
        </div>
      </section>
    </main>
  )
}