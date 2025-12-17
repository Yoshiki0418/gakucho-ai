'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface UseSpeechRecognitionOptions {
  lang?: string
  interimResults?: boolean
  continuous?: boolean
  onResult?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
}

type SpeechRecognitionResultItemLike = {
  transcript: string
}

type SpeechRecognitionResultLike = {
  isFinal: boolean
  length: number
  [index: number]: SpeechRecognitionResultItemLike
}

type SpeechRecognitionEventLike = {
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

type SpeechRecognitionErrorEventLike = {
  error: string
}

type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort?: () => void
}

export function useSpeechRecognition({
  lang = 'ja-JP',
  interimResults = true,
  continuous = true,
  onResult,
  onError,
}: UseSpeechRecognitionOptions = {}) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognitionCtor) {
      onError?.('このブラウザでは音声認識がサポートされていません。')
      return
    }

    const recognition: SpeechRecognitionLike = new SpeechRecognitionCtor()
    recognition.lang = lang
    recognition.interimResults = interimResults
    recognition.continuous = continuous

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let finalTranscript = ''
      let interimTranscript = ''

      // 毎回すべての結果を走査して文字列を再構築する
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        const transcript = result[0]?.transcript ?? ''

        if (result.isFinal) {
          finalTranscript += transcript
        } else {
          interimTranscript += transcript
        }
      }

      // 結果を通知
      if (finalTranscript || interimTranscript) {
        onResult?.(finalTranscript + interimTranscript, false)
      }
    }
    // ---------------------------------------------------

    recognition.onerror = (e: SpeechRecognitionErrorEventLike) => {
      const errorMsg = e?.error ?? 'SpeechRecognition error'
      if (errorMsg !== 'no-speech') {
        onError?.(errorMsg)
      }
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition

    // クリーンアップ関数
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch (e) {
        }
      }
      recognitionRef.current = null
    }
  }, [lang, interimResults, continuous, onResult, onError])

  // --- 操作メソッドの安定化 (useCallback) ---

  const start = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (e) {
        console.error('Failed to start recognition:', e)
      }
    }
  }, [isListening])

  const stop = useCallback(() => {
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop()
        setIsListening(false)
      } catch (e) {
        console.error('Failed to stop recognition:', e)
      }
    }
  }, [isListening])

  const reset = useCallback(() => {
    if (recognitionRef.current) {
      try {
        // abortがあればabort、なければstopでリセットを試みる
        if (recognitionRef.current.abort) {
          recognitionRef.current.abort()
        } else {
          recognitionRef.current.stop()
        }
      } catch (e) {
        console.error('Failed to reset recognition:', e)
      }
      setIsListening(false)
    }
  }, [])

  const syncExternalText = useCallback((text: string) => {
    // Do nothing
  }, [])

  return { isListening, start, stop, reset, syncExternalText }
}