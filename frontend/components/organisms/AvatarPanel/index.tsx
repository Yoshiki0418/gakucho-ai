'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'

import { ZOOM } from '@/features/avatar/zoom'

/**
 * Pixel Streaming のプレイヤーページ。
 *
 * `player.html` ではなく `uiless.html` を使う。前者はフルスクリーンボタンや設定アイコンを
 * 映像の上に重ねてくるが、この画面ではどれも不要なため。
 * `AutoConnect` を付けないと「CLICK TO START」が出たまま接続しない。
 */
const PIXEL_STREAMING_URL =
  '/ue-stream/uiless.html?AutoConnect=true&AutoPlayVideo=true&StartVideoMuted=true'

// HTML の load 完了と WebRTC 映像の受信開始は別物。映像時刻を監視して、
// 接続失敗・フリーズ時は古い PeerConnection を iframe ごと破棄して張り直す。
const FIRST_FRAME_TIMEOUT_MS = 25_000
const FROZEN_FRAME_TIMEOUT_MS = 12_000
const RECONNECT_DELAY_MS = 3_000

/**
 * 配信されてくる映像は「Unreal Editor のウィンドウ全体」なので、
 * その中の 3D ビューポート部分だけを切り出して表示する。
 *
 * 3D ビューだけを配信する `LevelEditorViewport` ソースは Linux では
 * フレームを 1 枚も生成しないため、`Editor` ソース (ウィンドウ全体) しか選べない。
 *
 * 下の数値は 1920x1080 で起動したエディタ (start-gakucho.sh の
 * -EditorPixelStreamingRes) を実測したもの。右側にアウトライナー、下に
 * シーケンサー (学長の再生に必要) が居るぶん、ビューポートはこの範囲になる。
 * エディタのパネル配置を変えるとずれるので、そのときはここを測り直す。
 */
const STREAM = { width: 1920, height: 1080 }
const VIEWPORT = { x: 0, y: 130, width: 1156, height: 592 }

const cropStyle = (zoom: number): React.CSSProperties => {
  // ビューポート(横長)をパネル(縦長)に「はみ出させて」収める。
  // 高さを基準に拡大し、左右の溢れた分を切り落とす。幅を基準にすると、
  // パネルの方が縦長なぶん下のシーケンサーまで見えてしまう。
  //
  // zoom=1 のとき、パネルの高さ = ビューポートの高さ。zoom を上げるとその分だけ
  // 見える範囲が狭まる (= 寄る)。ビューポートの中心を常にパネルの中心に置く。
  const scaleH = (STREAM.height / VIEWPORT.height) * zoom * 100
  const centerX = ((VIEWPORT.x + VIEWPORT.width / 2) / STREAM.width) * 100
  const centerY = ((VIEWPORT.y + VIEWPORT.height / 2) / STREAM.height) * 100

  return {
    position: 'absolute',
    top: '50%',
    left: '50%',
    height: `${scaleH}%`,
    // 映像の縦横比を保つ。崩すと Pixel Streaming 側がレターボックスを入れてしまう。
    aspectRatio: `${STREAM.width} / ${STREAM.height}`,
    transform: `translate(-${centerX}%, -${centerY}%)`,
    border: 'none',
    display: 'block',
  }
}

type AvatarPanelProps = {
  frameSrc: string | null
  streamUrl?: string
  /** 映像の切り抜き倍率。UI は設定モーダル側にある */
  zoom?: number
}

export const AvatarPanel: React.FC<AvatarPanelProps> = ({
  frameSrc,
  streamUrl = PIXEL_STREAMING_URL,
  zoom = ZOOM.default,
}) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [streamAttempt, setStreamAttempt] = useState(0)
  const [mountStream, setMountStream] = useState(true)
  const isSpeaking = frameSrc !== null
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const attemptedStreamUrl = useMemo(() => {
    const separator = streamUrl.includes('?') ? '&' : '?'
    return `${streamUrl}${separator}gakuchoAttempt=${streamAttempt}`
  }, [streamAttempt, streamUrl])

  useEffect(() => {
    if (!mountStream) return

    const startedAt = Date.now()
    let lastFrameAt = startedAt
    let lastVideoTime = -1
    let receivedFrame = false
    let reconnecting = false

    const reconnect = () => {
      if (reconnecting) return
      reconnecting = true
      setIsLoaded(false)
      setIsReconnecting(true)

      // 先に iframe を外して旧 PeerConnection/NVENC セッションを解放し、
      // 少し待ってから新しい接続を作る。即時リロードはセッションを一時的に
      // 二重化し、複数端末利用時の NVENC 枯渇を起こしやすい。
      setMountStream(false)
      window.setTimeout(() => {
        setStreamAttempt((attempt) => attempt + 1)
        setMountStream(true)
      }, RECONNECT_DELAY_MS)
    }

    const timer = window.setInterval(() => {
      try {
        const video = iframeRef.current?.contentDocument?.querySelector('video')
        if (video && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
          const videoTime = video.currentTime
          if (video.videoWidth > 0 && videoTime > lastVideoTime + 0.001) {
            lastVideoTime = videoTime
            lastFrameAt = Date.now()
            receivedFrame = true
            setIsLoaded(true)
            setIsReconnecting(false)
          }
        }
      } catch {
        // 現在は同一オリジンだが、将来 streamUrl が外部 URL になった場合は
        // DOM を参照できない。その場合もタイムアウトで再接続する。
      }

      const timeout = receivedFrame ? FROZEN_FRAME_TIMEOUT_MS : FIRST_FRAME_TIMEOUT_MS
      if (Date.now() - lastFrameAt >= timeout) reconnect()
    }, 1_000)

    return () => window.clearInterval(timer)
  }, [mountStream, streamAttempt, streamUrl])

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
          <span>{isReconnecting ? '映像を再接続中…' : 'ストリーミング接続中…'}</span>
          <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
      )}

      {/* UE5 Pixel Streaming iframe（エディタ画面のうちビューポートだけを切り出す） */}
      {mountStream && (
        <iframe
          key={streamAttempt}
          ref={iframeRef}
          src={attemptedStreamUrl}
          title="学長 3D アバター (Pixel Streaming)"
          allow="autoplay; fullscreen"
          style={{
            ...cropStyle(zoom),
            opacity: isLoaded ? 1 : 0,
            transition: 'opacity 0.4s ease, height 0.2s ease',
            // 視点移動やクリックを拾わせない
            pointerEvents: 'none',
          }}
        />
      )}

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
