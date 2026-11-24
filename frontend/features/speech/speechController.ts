/** One cancellable microphone/transcription session. No React or shared state. */
export type SpeechPhase = 'idle' | 'starting' | 'listening' | 'transcribing'

type Recognition = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: RecognitionEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
  abort?(): void
}
type RecognitionEvent = {
  results: { length: number; [index: number]: { isFinal: boolean; [index: number]: { transcript: string } } }
}
type SpeechCallbacks = {
  onPhase(phase: SpeechPhase): void
  onResult(text: string, isFinal: boolean): void
  onError(message: string): void
}
type SpeechDependencies = {
  createRecognition(): Recognition | null
  getUserMedia(): Promise<MediaStream>
  createRecorder(stream: MediaStream): MediaRecorder
  fetch: typeof fetch
}

const MAX_BYTES = 8 * 1024 * 1024
// Leave room for MediaRecorder/codec finalization before the server's 60 s cap.
const MAX_RECORDING_MS = 59000

export function browserSpeechDependencies(): SpeechDependencies {
  return {
    createRecognition: () => {
      const browser = window as unknown as {
        SpeechRecognition?: new () => Recognition
        webkitSpeechRecognition?: new () => Recognition
      }
      const Constructor = browser.SpeechRecognition || browser.webkitSpeechRecognition
      return Constructor ? new Constructor() : null
    },
    getUserMedia: () => navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    }),
    createRecorder: (stream) => {
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
        .find((type) => MediaRecorder.isTypeSupported(type))
      return new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    },
    fetch: (...args) => fetch(...args),
  }
}

export function createSpeechController(callbacks: SpeechCallbacks, deps: SpeechDependencies) {
  let generation = 0
  let phase: SpeechPhase = 'idle'
  let recognition: Recognition | null = null
  let recorder: MediaRecorder | null = null
  let stream: MediaStream | null = null
  let request: AbortController | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let browserText = ''

  const setPhase = (next: SpeechPhase) => {
    phase = next
    callbacks.onPhase(next)
  }
  const releaseTracks = () => {
    stream?.getTracks().forEach((track) => track.stop())
    stream = null
  }
  const clearTimer = () => {
    if (timer) clearTimeout(timer)
    timer = null
  }
  const cancel = () => {
    generation += 1
    clearTimer()
    if (recognition) {
      recognition.onresult = null
      recognition.onend = null
      recognition.onerror = null
      try {
        if (recognition.abort) recognition.abort()
        else recognition.stop()
      } catch { /* already ended */ }
      recognition = null
    }
    if (recorder) {
      recorder.ondataavailable = null
      recorder.onstop = null
      recorder.onerror = null
      if (recorder.state !== 'inactive') recorder.stop()
      recorder = null
    }
    request?.abort()
    request = null
    releaseTracks()
    browserText = ''
    setPhase('idle')
  }
  const report = (token: number, message: string) => {
    if (token !== generation) return
    cancel()
    callbacks.onError(message)
  }
  const publish = (token: number, text: string) => {
    if (token !== generation) return
    cancel()
    if (text.trim()) callbacks.onResult(text.trim(), true)
    else callbacks.onError('音声を認識できませんでした。もう一度お話しください。')
  }
  const finish = () => {
    clearTimer()
    if (phase === 'starting' || phase === 'transcribing') {
      cancel()
    } else if (recognition) {
      const token = generation
      try { recognition.stop() } catch { publish(token, browserText) }
    } else if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
  }

  const start = async (model = 'browser', autoSubmit = false, lang = 'ja-JP', options: { continuous?: boolean; interimResults?: boolean } = {}) => {
    cancel()
    const token = generation
    setPhase('starting')
    if (model === 'browser') {
      const engine = deps.createRecognition()
      if (!engine) {
        report(token, 'このブラウザは音声認識に対応していません。別の音声認識方式を選択してください。')
        return
      }
      recognition = engine
      engine.lang = lang
      engine.interimResults = options.interimResults ?? true
      engine.continuous = options.continuous ?? !autoSubmit
      engine.onresult = (event) => {
        if (token !== generation) return
        let text = ''
        let allFinal = event.results.length > 0
        for (let index = 0; index < event.results.length; index++) {
          text += event.results[index][0]?.transcript || ''
          allFinal = allFinal && event.results[index].isFinal
        }
        browserText = text
        callbacks.onResult(text, false)
        if (autoSubmit && allFinal && text.trim()) publish(token, text)
      }
      engine.onerror = (event) => {
        if (event.error !== 'aborted') report(token, event.error === 'no-speech'
          ? '音声を認識できませんでした。もう一度お話しください。'
          : 'マイクを使用できません。ブラウザの権限設定をご確認ください。')
      }
      engine.onend = () => publish(token, browserText)
      try {
        engine.start()
        setPhase('listening')
        timer = setTimeout(finish, MAX_RECORDING_MS)
      } catch {
        report(token, '音声認識を開始できませんでした。')
      }
      return
    }

    try {
      const recordingStream = await deps.getUserMedia()
      if (token !== generation) {
        recordingStream.getTracks().forEach((track) => track.stop())
        return
      }
      stream = recordingStream
      const engine = deps.createRecorder(recordingStream)
      recorder = engine
      const chunks: Blob[] = []
      let bytes = 0
      engine.ondataavailable = (event: BlobEvent) => {
        if (token !== generation) return
        bytes += event.data.size
        if (bytes > MAX_BYTES) {
          report(token, '録音が大きすぎます。短く区切ってお話しください。')
          return
        }
        if (event.data.size) chunks.push(event.data)
      }
      engine.onerror = () => report(token, '録音を続けられませんでした。')
      engine.onstop = async () => {
        if (token !== generation) return
        clearTimer()
        releaseTracks()
        recorder = null
        const blob = new Blob(chunks, { type: engine.mimeType || 'audio/webm' })
        if (!blob.size) { report(token, '録音データが空です。'); return }
        setPhase('transcribing')
        request = new AbortController()
        const form = new FormData()
        form.append('file', blob, 'recording')
        form.append('model', model)
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''
        try {
          const response = await deps.fetch(`${apiBase}/api/speech/transcribe`, {
            method: 'POST', body: form, signal: request.signal,
          })
          if (token !== generation) return
          const result = await response.json()
          if (token !== generation) return
          if (!response.ok) {
            report(token, typeof result.detail === 'string' ? result.detail : '音声認識に失敗しました。')
          } else if (typeof result.text === 'string') {
            publish(token, result.text)
          } else {
            report(token, '音声認識の応答を読み取れませんでした。')
          }
        } catch {
          report(token, '音声認識サーバーに接続できませんでした。')
        }
      }
      engine.start(250)
      setPhase('listening')
      timer = setTimeout(finish, MAX_RECORDING_MS)
    } catch {
      report(token, '録音を開始できません。マイクの権限とブラウザの対応状況をご確認ください。')
    }
  }

  return { start, finish, cancel }
}
