'use client'

import React, { useState } from 'react'

/** Pixel Streaming サーバーの URL */
const PIXEL_STREAMING_URL = 'http://127.0.0.1:80'

type AvatarPanelProps = {
  frameSrc: string | null
  /** Pixel Streaming サーバーの URL（デフォルト: 127.0.0.1:80） */
  streamUrl?: string
}

export const AvatarPanel: React.FC<AvatarPanelProps> = ({
  frameSrc,
  streamUrl = PIXEL_STREAMING_URL,
}) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const isSpeaking = frameSrc !== null

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        backgroundColor: '#000',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* ローディング表示（iframe 読み込み中） */}
      {!isLoaded && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            color: '#94a3b8',
            fontSize: 14,
            gap: 12,
            zIndex: 1,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              border: '3px solid rgba(148,163,184,0.3)',
              borderTopColor: '#94a3b8',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
            }}
          />
          <span>ストリーミング接続中…</span>
          <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
      )}

      {/* UE5 Pixel Streaming iframe */}
      <iframe
        src={streamUrl}
        title="学長 3D アバター (Pixel Streaming)"
        allow="autoplay; fullscreen; microphone; camera"
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          display: 'block',
          opacity: isLoaded ? 1 : 0,
          transition: 'opacity 0.4s ease',
        }}
        onLoad={() => setIsLoaded(true)}
      />

      {/* 右上ステータスバッジ */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          right: 16,
          padding: '4px 10px',
          borderRadius: 999,
          background: 'rgba(15,23,42,0.75)',
          border: '1px solid rgba(148,163,184,0.6)',
          fontSize: 11,
          color: '#E5E7EB',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          zIndex: 2,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '999px',
            backgroundColor: isSpeaking ? '#22c55e' : '#6b7280',
          }}
        />
        <span>{isSpeaking ? 'Speaking' : 'Idle'}</span>
      </div>
    </div>
  )
}

