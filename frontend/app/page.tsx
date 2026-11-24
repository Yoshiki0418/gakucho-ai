'use client'

import React, { useState, useEffect } from 'react'
import ChatPanel from '@/components/organisms/ChatPanel'
import { useTextChat } from '@/features/text-chat/hooks/useTextChat'
import { AvatarPanel } from '@/components/organisms/AvatarPanel'
import { QRCodeDisplay } from '@/components/organisms/QRCodeDisplay'
import { ZOOM } from '@/features/avatar/zoom'
import type { LipSyncMode } from '@/features/text-chat/hooks/useTextChat'
import { useInferenceSettings } from '@/features/inference-settings/useInferenceSettings'
import { validateDraft, type ChatMode } from '@/features/inference-settings/settings'

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [closedUrls, setClosedUrls] = useState<Set<string>>(new Set())
  const [appMode, setAppMode] = useState<ChatMode>('general')
  const [fillerMode, setFillerMode] = useState<string>('endogenous')
  const settings = useInferenceSettings()
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null)
  // QRコード表示（モード切替とは独立して個別トグル）
  const [qrEnabled, setQrEnabled] = useState<boolean>(true)
  // UE アバターの口の動かし方（設定モーダルの「一般」タブ）
  const [lipSyncMode, setLipSyncMode] = useState<LipSyncMode>('legacy')
  // アバター映像の切り抜き倍率。UE のカメラは動かない
  const [zoom, setZoom] = useState<number>(ZOOM.default)

  const [chatWidth, setChatWidth] = useState<number | string>('35%')
  const [isResizing, setIsResizing] = useState(false)

  useEffect(() => {
    setChatWidth(window.innerWidth * 0.35)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      // Limit minimum to 320px and maximum to 80% inner width
      const newWidth = Math.max(320, Math.min(e.clientX, window.innerWidth * 0.8))
      setChatWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  const { messages, startChat, speakingMessageId, resetChat, avatarFrameSrc, latestUrl, interruptChat, error: chatError } =
    useTextChat('/api/text-chat/char-stream-orchestrator')

  const handleMicClick = () => {
    console.log('🎙️ Mic clicked')
  }

  const handleSend = async (value: string) => {
    const message = value.trim()
    if (!message) return

    const checked = settings.catalog ? validateDraft(settings.draft, settings.catalog, settings.mainModel, appMode) : null
    if (checked && !checked.valid) {
      setSettingsMessage('設定に入力エラーがあります。設定画面で赤字の項目を修正してください。')
      return
    }
    setSettingsMessage(null)
    setIsSending(true)
    try {
      await startChat(message, appMode, fillerMode, settings.mainModel, settings.fillerModel, lipSyncMode, checked?.request)
    } finally {
      setIsSending(false)
    }

    setInputValue('')
  }

  const handleTemplateClick = (text: string) => {
    setInputValue(text)
    handleSend(text)
  }



  // QR表示トグルがONで、ユーザーが閉じたURLでなければ表示する
  // （従来はモード依存だったが、設定で個別にON/OFF可能にした）
  const displayUrl = qrEnabled && latestUrl && !closedUrls.has(latestUrl) ? latestUrl : null

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
        cursor: isResizing ? 'col-resize' : 'auto',
        userSelect: isResizing ? 'none' : 'auto',
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
          appMode={appMode}
          onModeChange={setAppMode}
          width={chatWidth}
          fillerMode={fillerMode}
          onFillerModeChange={setFillerMode}
          mainModel={settings.mainModel}
          onMainModelChange={settings.changeMainModel}
          fillerModel={settings.fillerModel}
          onFillerModelChange={settings.setFillerModel}
          settingsCatalog={settings.catalog}
          inferenceDraft={settings.draft}
          onInferenceChange={settings.changeDraft}
          settingsLoading={settings.isLoading}
          settingsError={settings.error}
          onReloadSettings={settings.reload}
          errorMessage={settingsMessage || chatError}
          qrEnabled={qrEnabled}
          onQrEnabledChange={setQrEnabled}
          zoom={zoom}
          onZoomChange={setZoom}
          lipSyncMode={lipSyncMode}
          onLipSyncModeChange={setLipSyncMode}
        />

        {/* リサイズ用ハンドル */}
        <div
          onMouseDown={(e) => {
            e.preventDefault()
            setIsResizing(true)
          }}
          style={{
            width: '12px',
            cursor: 'col-resize',
            backgroundColor: isResizing ? 'rgba(59, 130, 246, 0.4)' : 'transparent',
            zIndex: 50,
            transition: 'background-color 0.2s',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
          onMouseEnter={(e) => {
            if (!isResizing) e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)'
          }}
          onMouseLeave={(e) => {
            if (!isResizing) e.currentTarget.style.backgroundColor = 'transparent'
          }}
        >
          <div style={{ width: '2px', height: '30px', backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: '1px' }} />
        </div>

        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <AvatarPanel frameSrc={avatarFrameSrc} zoom={zoom} />
          <QRCodeDisplay url={displayUrl} onClose={handleCloseQRCode} />
        </div>
      </section>
    </main>
  )
}