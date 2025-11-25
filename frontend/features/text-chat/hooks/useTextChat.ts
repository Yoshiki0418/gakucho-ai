'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  text: string
  role: 'user' | 'assistant'
}

type SSEText = { type: 'text_chunk'; content: string }
type SSEAudio = { type: 'audio_chunk'; audio: string; sentence?: string; mime?: string }
type SSEDone = { type: 'done' }
type SSEAny = SSEText | SSEAudio | SSEDone

export function useTextChat(endpoint: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null)

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
    currentAssistantIdRef.current = null
  }

  const ensureAudioReady = () => {
    if (!audioCtxRef.current) {
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext;

      if (!AudioContextClass) {
        console.error("AudioContext not supported");
        return;
      }

      audioCtxRef.current = new AudioContextClass();
    }

    if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }
  };

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
    stopAllAudio()

    // 🗣️ ユーザー入力
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), text: userText, role: 'user' },
    ])

    eventSourceRef.current?.close()

    const fullUrl = `http://localhost:8000${endpoint}?text=${encodeURIComponent(userText)}`
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
              // 🎯 新しいassistantメッセージを開始
              const id = crypto.randomUUID()
              currentAssistantIdRef.current = id
              setSpeakingMessageId(id)
              return [...prev, { id, text: chunk, role: 'assistant' }]
            } else {
              // 同じassistantメッセージにテキストを追加
              const id = currentAssistantIdRef.current ?? last.id
              currentAssistantIdRef.current = id
              setSpeakingMessageId(id)

              let updated = last.text + chunk
              if (/[。！？!?]$/.test(updated)) updated += '\n\n'

              return [...prev.slice(0, -1), { ...last, text: updated, id }]
            }
          })
        }

        // 音声チャンク
        else if (data.type === 'audio_chunk') {
          if (data.audio) handleAudioChunk(data.audio)
        }

        // 完了イベント
        else if (data.type === 'done') {
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
        }
      } catch (e) {
        console.error('Parse error:', e)
      }
    }

    es.onerror = (err) => {
      console.error('❌ SSE Error:', err)
      es.close()
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
  }
}
