'use client'

import React from 'react'
import Image from 'next/image'

type AvatarPanelProps = {
  frameSrc: string | null
  /** 最初に表示しておく学長の静止画（口を閉じている画像）のパス */
  idleSrc?: string
}

export const AvatarPanel: React.FC<AvatarPanelProps> = ({
  frameSrc,
  idleSrc = '/avatars/test.jpg',
}) => {
  const currentSrc = frameSrc ?? idleSrc

  return (
    <div
      style={{
        flex: 1,
        height: '100%',
        backgroundColor: '#000',
        display: 'flex',
        flexDirection: 'column',   // ★ 縦方向レイアウト
        justifyContent: 'flex-end',// ★ 縦方向の「下」に寄せる
        alignItems: 'center',      // 横方向は中央
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* アバター画像ラッパー */}
      <div
        style={{
          width: '100%',
          maxWidth: 960,
          // 高さはコンテンツに任せる。大きさを制限したければ maxHeight などで調整
          maxHeight: '90vh',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-end',
        }}
      >
        <Image
          src={currentSrc}
          alt="学長アバター"
          fill
          priority
          style={{
            objectFit: 'contain',
          }}
        />
      </div>

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
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '999px',
            backgroundColor: frameSrc ? '#22c55e' : '#6b7280',
          }}
        />
        <span>{frameSrc ? 'Speaking' : 'Idle'}</span>
      </div>
    </div>
  )
}
