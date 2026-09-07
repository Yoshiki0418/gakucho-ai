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
  duration?: number
  visemes?: VisemeFrame[]
}
type VisemeFrame = {
  start: number
  end: number
  viseme: string
}
export type LipSyncMode = 'legacy' | 'phoneme'
type SSEFrame = {
  type: 'frame_chunk'
  image: string
  frame_index?: number
  fps?: number
}
type SSEDone = { type: 'done'; message?: string }
type SSEMetadata = {
  type: 'metadata_chunk'
  dataType: string
  content: string
}
// ★ any 付きの index signature は削除
type SSEAny = SSEText | SSEAudio | SSEFrame | SSEDone | SSEMetadata

export function useTextChat(endpoint: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null)
  const [avatarFrameSrc, setAvatarFrameSrc] = useState<string | null>(null) // ★ 最新フレーム
  const [latestUrl, setLatestUrl] = useState<string | null>(null)

  const eventSourceRef = useRef<EventSource | null>(null)
  const currentAssistantIdRef = useRef<string | null>(null)
  const lastAudioChunkTimeRef = useRef<number>(0)

  // ========= Web Audio 再生制御 =========
  const audioCtxRef = useRef<AudioContext | null>(null)
  const playbackTimeRef = useRef<number>(0)
  const audioGenerationRef = useRef<number>(0)
  const audioDecodeQueueRef = useRef<Promise<void>>(Promise.resolve())
  const lipSyncActiveRef = useRef<boolean>(false)
  const lipSyncRequestRef = useRef<number>(0)
  const lipSyncClientIdRef = useRef<string | null>(null)
  const lipSyncModeRef = useRef<LipSyncMode>('legacy')

  /**
   * UE の口パク用トラックを音声再生状態に合わせる。
   * stop は pagehide 中にも送れるよう keepalive を使う。
   */
  const setLipSyncActive = async (active: boolean, force = false) => {
    if (!force && lipSyncActiveRef.current === active) return

    lipSyncActiveRef.current = active
    const requestId = ++lipSyncRequestRef.current
    const action = active ? 'start' : 'stop'
    if (!lipSyncClientIdRef.current) {
      lipSyncClientIdRef.current = crypto.randomUUID()
    }
    const query = new URLSearchParams({
      client_id: lipSyncClientIdRef.current,
      mode: lipSyncModeRef.current,
    })

    try {
      const response = await fetch(`/lip-sync/${action}?${query}`, {
        method: 'GET',
        cache: 'no-store',
        keepalive: !active,
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      console.log(`[LipSync] ${action}`)
    } catch (error) {
      console.error(`[LipSync] failed to ${action}:`, error)
      // この要求より後の状態変更が無ければ、次回に再試行できるよう戻す。
      if (lipSyncRequestRef.current === requestId) {
        lipSyncActiveRef.current = !active
      }
    }
  }

  const sendVisemeTimeline = async (
    frames: VisemeFrame[],
    delayMs: number,
    generation: number,
  ) => {
    if (
      lipSyncModeRef.current !== 'phoneme' ||
      !frames.length ||
      generation !== audioGenerationRef.current
    ) return
    if (!lipSyncClientIdRef.current) {
      lipSyncClientIdRef.current = crypto.randomUUID()
    }
    const query = new URLSearchParams({
      client_id: lipSyncClientIdRef.current,
    })
    try {
      const response = await fetch(`/lip-sync/timeline?${query}`, {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          delay_ms: Math.max(0, delayMs),
          frames,
        }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
    } catch (error) {
      console.error('[LipSync] timeline送信失敗:', error)
    }
  }

  const resetChat = async () => {
    stopAllAudio()
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setMessages([])
    setSpeakingMessageId(null)
    setAvatarFrameSrc(null)
    setLatestUrl(null)
    currentAssistantIdRef.current = null

    // ★ バックエンドの履歴もリセットする
    try {
      // NEXT_PUBLIC_API_BASE_URL が空なら相対URLにする（nginx経由でバックエンドに届く）
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''
      const resetUrl = apiBase
        ? `${apiBase}/api/text-chat/reset`
        : '/api/text-chat/reset'
      console.log('[useTextChat] Resetting history on backend:', resetUrl)
      await fetch(resetUrl, { method: 'POST' })
    } catch (err) {
      console.error('[useTextChat] Failed to reset backend history:', err)
    }
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
      audioCtxRef.current.resume().catch(() => { })
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

  const enqueueAudioBuffer = (
    buf: AudioBuffer,
    generation: number,
    visemes: VisemeFrame[],
  ) => {
    const ctx = audioCtxRef.current!
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)

    if (generation !== audioGenerationRef.current) return

    const now = ctx.currentTime
    // 最初の音声にもUEへ口形列を届ける時間を確保する。
    if (playbackTimeRef.current < now) playbackTimeRef.current = now + 0.12

    if (currentAssistantIdRef.current) {
      setSpeakingMessageId(currentAssistantIdRef.current)
    }

    const scheduledStart = playbackTimeRef.current
    void sendVisemeTimeline(
      visemes,
      (scheduledStart - ctx.currentTime) * 1000,
      generation,
    )
    src.start(scheduledStart)
    playbackTimeRef.current += buf.duration

    src.onended = () => {
      const checkDelay = 600
      setTimeout(() => {
        if (generation !== audioGenerationRef.current) return
        const elapsed = Date.now() - lastAudioChunkTimeRef.current
        const remaining = playbackTimeRef.current - ctx.currentTime
        if (elapsed > checkDelay && remaining <= 0.5) {
          setSpeakingMessageId(null)
        }
      }, checkDelay)
    }
  }

  const handleAudioChunk = async (
    base64: string,
    visemes: VisemeFrame[] = [],
  ) => {
    ensureAudioReady()
    const ctx = audioCtxRef.current!
    const generation = audioGenerationRef.current
    lastAudioChunkTimeRef.current = Date.now()

    try {
      const arr = b64ToArrayBuffer(base64)
      const audioBuffer = await ctx.decodeAudioData(arr.slice(0))
      if (generation !== audioGenerationRef.current) return
      enqueueAudioBuffer(audioBuffer, generation, visemes)
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
        if (generation !== audioGenerationRef.current) return
        enqueueAudioBuffer(audioBuffer, generation, visemes)
      } catch (e2) {
        console.error('再試行でも失敗:', e2)
      }
    }
  }

  const stopAllAudio = () => {
    audioGenerationRef.current += 1
    const ctx = audioCtxRef.current
    if (ctx) ctx.close().catch(() => { })
    audioCtxRef.current = null
    playbackTimeRef.current = 0
    audioDecodeQueueRef.current = Promise.resolve()
    currentAssistantIdRef.current = null
    setSpeakingMessageId(null)
    void setLipSyncActive(false)
  }

  const interruptChat = () => {
    stopAllAudio()
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }

  // ==========================================
  const startChat = (
    userText: string,
    mode: string = 'general',
    fillerMode: string = 'dynamic',
    llmModel?: string,
    fillerModel?: string,
    lipSyncMode: LipSyncMode = 'legacy',
  ) => {
    // 新しい会話のたびにオーディオはリセット
    stopAllAudio()
    // 直前の stop と新しい start が前後しても、新しい発話を消さないようIDを分ける。
    lipSyncClientIdRef.current = crypto.randomUUID()
    lipSyncModeRef.current = lipSyncMode
    setLatestUrl(null)

    // ユーザーメッセージ追加
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), text: userText, role: 'user' },
    ])

    // 既存 SSE を閉じる
    eventSourceRef.current?.close()

    // NEXT_PUBLIC_API_BASE_URL が空なら相対URL（nginx経由）、設定があればそれを使う
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''
    // モデル選択が指定されていればクエリに付与（未指定ならバックエンド既定モデル）
    const modelParams =
      (llmModel ? `&llm_model=${encodeURIComponent(llmModel)}` : '') +
      (fillerModel ? `&filler_model=${encodeURIComponent(fillerModel)}` : '')
    const fullUrl = apiBase
      ? `${apiBase}${endpoint}?text=${encodeURIComponent(userText)}&mode=${mode}&filler_mode=${fillerMode}${modelParams}`
      : `${endpoint}?text=${encodeURIComponent(userText)}&mode=${mode}&filler_mode=${fillerMode}${modelParams}`

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
              // 音声再生時にセットするためここでは呼ばない
              return [...prev, { id, text: chunk, role: 'assistant' }]
            } else {
              // 直近の assistant メッセージに追記
              const id = currentAssistantIdRef.current ?? last.id
              currentAssistantIdRef.current = id
              // 音声再生時にセットするためここでは呼ばない

              let updated = last.text + chunk
              if (/[。！？!?]$/.test(updated)) updated += '\n\n'

              return [...prev.slice(0, -1), { ...last, text: updated, id }]
            }
          })
          return
        }

        // 🟦 音声チャンク
        if (data.type === 'audio_chunk') {
          if (data.audio) {
            const generation = audioGenerationRef.current
            // decodeAudioData の完了順が前後しても、発話と口形の順序はSSE順を保つ。
            audioDecodeQueueRef.current = audioDecodeQueueRef.current
              .then(async () => {
                if (generation !== audioGenerationRef.current) return
                await handleAudioChunk(data.audio, data.visemes ?? [])
              })
              .catch((error) => {
                console.error('音声キュー処理失敗:', error)
              })
          }
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

        // 🟦 メタデータチャンク
        if (data.type === 'metadata_chunk') {
          if (data.dataType === 'url') {
            let url = data.content
            if (url.startsWith('www.')) {
              url = `https://${url}`
            }
            setLatestUrl(url)
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
    // speakingMessageId は最初の音声バッファを再生するときに設定され、
    // 最後のバッファが終わると null になる。テキスト生成中ではなく、
    // 実際に端末から音声が出ている区間だけ口パクを有効にする。
    if (speakingMessageId === null) {
      void setLipSyncActive(false)
      return
    }

    // UE側のリースを更新する。タブが異常終了して更新が止まれば、UEが自動で
    // ニュートラルへ戻すため「口が動きっぱなし」にならない。
    void setLipSyncActive(true)
    const heartbeat = window.setInterval(() => {
      void setLipSyncActive(true, true)
    }, 2_000)

    return () => window.clearInterval(heartbeat)
  }, [speakingMessageId])

  useEffect(() => {
    // 前回、発話中にタブを閉じた場合でも必ずニュートラルから開始する。
    void setLipSyncActive(false, true)

    const onUserInteract = () => {
      ensureAudioReady()
      window.removeEventListener('click', onUserInteract)
      window.removeEventListener('keydown', onUserInteract)
      window.removeEventListener('touchstart', onUserInteract)
    }
    window.addEventListener('click', onUserInteract)
    window.addEventListener('keydown', onUserInteract)
    window.addEventListener('touchstart', onUserInteract)

    const onPageHide = () => {
      stopAllAudio()
      void setLipSyncActive(false, true)
    }
    window.addEventListener('pagehide', onPageHide)

    return () => {
      eventSourceRef.current?.close()
      stopAllAudio()
      void setLipSyncActive(false, true)
      window.removeEventListener('click', onUserInteract)
      window.removeEventListener('keydown', onUserInteract)
      window.removeEventListener('touchstart', onUserInteract)
      window.removeEventListener('pagehide', onPageHide)
    }
    // イベントリスナーはマウント中に一度だけ登録する。参照する状態は全て ref。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    messages,
    startChat,
    speakingMessageId,
    resetChat,
    avatarFrameSrc,
    latestUrl,
    interruptChat,
  }
}
