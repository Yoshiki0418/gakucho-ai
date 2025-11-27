'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  text: string
  role: 'user' | 'assistant'
}

// ===== SSE ペイロード型 =====
type SSEText = { type: 'text_chunk'; content: string }
type SSEAudio = {
  type: 'audio_chunk'
  audio: string
  sentence?: string
  mime?: string
}
type SSEFrame = {
  type: 'frame_chunk'
  image: string
  frame_index?: number
  fps?: number
}
type SSEDone = { type: 'done'; message?: string }
// ★ any 付きの index signature は削除
type SSEAny = SSEText | SSEAudio | SSEFrame | SSEDone

export function useTextChat(endpoint: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null)
  const [avatarFrameSrc, setAvatarFrameSrc] = useState<string | null>(null) // ★ 最新フレーム

  const eventSourceRef = useRef<EventSource | null>(null)
  const currentAssistantIdRef = useRef<string | null>(null)
  const lastAudioChunkTimeRef = useRef<number>(0)

  // ========= Web Audio 再生制御 =========
  const audioCtxRef = useRef<AudioContext | null>(null)
  const playbackTimeRef = useRef<number>(0)
  const queueClearedRef = useRef<boolean>(false)

  const resetChat = () => {
    stopAllAudio()
    setMessages([])
    setSpeakingMessageId(null)
    setAvatarFrameSrc(null)
    currentAssistantIdRef.current = null
  }

  const ensureAudioReady = () => {
    if (!audioCtxRef.current) {
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext

      if (!AudioContextClass) {
        console.error('AudioContext not supported')
        return
      }

      audioCtxRef.current = new AudioContextClass()
    }

    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume().catch(() => {})
    }
  }

  const b64ToArrayBuffer = (b64: string): ArrayBuffer => {
    b64 = b64.replace(/[\r\n\s]/g, '')
    while (b64.length % 4 !== 0) b64 += '='
    const binary = atob(b64)
    const buf = new ArrayBuffer(binary.length)
    const view = new Uint8Array(buf)
    for (let i = 0; i < binary.length; i++) view[i] = binary.charCodeAt(i)
    return buf
  }

  const enqueueAudioBuffer = (buf: AudioBuffer) => {
    const ctx = audioCtxRef.current!
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)

    if (queueClearedRef.current) return

    const now = ctx.currentTime
    if (playbackTimeRef.current < now) playbackTimeRef.current = now + 0.02

    if (currentAssistantIdRef.current) {
      setSpeakingMessageId(currentAssistantIdRef.current)
    }

    src.start(playbackTimeRef.current)
    playbackTimeRef.current += buf.duration

    src.onended = () => {
      const checkDelay = 600
      setTimeout(() => {
        const elapsed = Date.now() - lastAudioChunkTimeRef.current
        const remaining = playbackTimeRef.current - ctx.currentTime
        if (elapsed > checkDelay && remaining <= 0.5) {
          setSpeakingMessageId(null)
        }
      }, checkDelay)
    }
  }

  const handleAudioChunk = async (base64: string) => {
    ensureAudioReady()
    const ctx = audioCtxRef.current!
    lastAudioChunkTimeRef.current = Date.now()

    try {
      const arr = b64ToArrayBuffer(base64)
      const audioBuffer = await ctx.decodeAudioData(arr.slice(0))
      enqueueAudioBuffer(audioBuffer)
      if (currentAssistantIdRef.current) {
        setSpeakingMessageId(currentAssistantIdRef.current)
      }
    } catch (e) {
      console.error('decodeAudioData 失敗:', e)
      await new Promise((r) => setTimeout(r, 150))
      try {
        ensureAudioReady()
        const arr = b64ToArrayBuffer(base64)
        const audioBuffer = await ctx.decodeAudioData(arr.slice(0))
        enqueueAudioBuffer(audioBuffer)
      } catch (e2) {
        console.error('再試行でも失敗:', e2)
      }
    }
  }

  const stopAllAudio = () => {
    const ctx = audioCtxRef.current
    if (!ctx) return
    queueClearedRef.current = true
    ctx.close().catch(() => {})
    audioCtxRef.current = null
    playbackTimeRef.current = 0
    currentAssistantIdRef.current = null
    setTimeout(() => (queueClearedRef.current = false), 100)
  }

  // ==========================================
  const startChat = (userText: string) => {
    // 新しい会話のたびにオーディオはリセット
    stopAllAudio()

    // ユーザーメッセージ追加
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), text: userText, role: 'user' },
    ])

    // 既存 SSE を閉じる
    eventSourceRef.current?.close()

    // ★ FastAPI 直叩き用のベースURL
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      'http://localhost:8000' // dev デフォルト
    const fullUrl = `${apiBase}${endpoint}?text=${encodeURIComponent(userText)}`

    console.log('[useTextChat] SSE connect to:', fullUrl)

    const es = new EventSource(fullUrl)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data: SSEAny = JSON.parse(event.data)

        console.log('🔹 [SSE EVENT RECEIVED]', data)

        // 🟦 テキストチャンク
        if (data.type === 'text_chunk') {
          const chunk = data.content
          if (!chunk) return

          setMessages((prev) => {
            const last = prev.at(-1)
            if (!last || last.role !== 'assistant') {
              // 🎯 新しい assistant メッセージ開始
              const id = crypto.randomUUID()
              currentAssistantIdRef.current = id
              setSpeakingMessageId(id)
              return [...prev, { id, text: chunk, role: 'assistant' }]
            } else {
              // 直近の assistant メッセージに追記
              const id = currentAssistantIdRef.current ?? last.id
              currentAssistantIdRef.current = id
              setSpeakingMessageId(id)

              let updated = last.text + chunk
              if (/[。！？!?]$/.test(updated)) updated += '\n\n'

              return [...prev.slice(0, -1), { ...last, text: updated, id }]
            }
          })
          return
        }

        // 🟦 音声チャンク
        if (data.type === 'audio_chunk') {
          if (data.audio) handleAudioChunk(data.audio)
          return
        }

        // 🟦 フレームチャンク（Ditto）
        if (data.type === 'frame_chunk') {
          const imgBase64: string | undefined = data.image
          if (imgBase64) {
            setAvatarFrameSrc(`data:image/jpeg;base64,${imgBase64}`)
          }
          return
        }

        // 🟦 完了イベント
        if (data.type === 'done') {
          setMessages((prev) => {
            const last = prev.at(-1)
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, text: last.text.replace(/\n+$/g, '') },
              ]
            }
            return prev
          })
          es.close()
          eventSourceRef.current = null
          return
        }

        // その他の type（'start' など）は一旦無視でもOK
      } catch (e) {
        console.error('Parse error:', e)
      }
    }

    es.onerror = (err) => {
      console.error('❌ SSE Error:', err)
      es.close()
      eventSourceRef.current = null
      setSpeakingMessageId(null)
      currentAssistantIdRef.current = null
    }
  }

  // ==========================================

  useEffect(() => {
    const onUserInteract = () => {
      ensureAudioReady()
      window.removeEventListener('click', onUserInteract)
      window.removeEventListener('keydown', onUserInteract)
      window.removeEventListener('touchstart', onUserInteract)
    }
    window.addEventListener('click', onUserInteract)
    window.addEventListener('keydown', onUserInteract)
    window.addEventListener('touchstart', onUserInteract)

    return () => {
      eventSourceRef.current?.close()
      stopAllAudio()
      window.removeEventListener('click', onUserInteract)
      window.removeEventListener('keydown', onUserInteract)
      window.removeEventListener('touchstart', onUserInteract)
    }
  }, [])

  return {
    messages,
    startChat,
    speakingMessageId,
    resetChat,
    avatarFrameSrc, // AvatarPanel に渡す用
  }
}
