'use client'

import { useEffect, useRef, useState } from 'react'

interface UseSpeechRecognitionOptions {
  lang?: string
  interimResults?: boolean
  continuous?: boolean
  onResult?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
}

/**
 * ✅ SpeechRecognition 系は TS の lib.dom に存在しない環境があるため、
 *   必要最小限の型だけローカルで定義する（Next build を確実に通す）
 */
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

  const lastResultIndexRef = useRef(-1)
  const finalTextRef = useRef('')
  const lastFinalSegmentRef = useRef('')

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
      let interim = ''
      let newFinal = ''

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal && i <= lastResultIndexRef.current) continue

        const transcript = result[0]?.transcript ?? ''

        if (result.isFinal) {
          newFinal += transcript
          lastResultIndexRef.current = i
        } else {
          interim += transcript
        }
      }

      if (newFinal) {
        // 差分のみ抽出
        const diff = newFinal.replace(lastFinalSegmentRef.current, '').trim()
        if (diff) {
          lastFinalSegmentRef.current = newFinal
          finalTextRef.current += diff + ' '
          onResult?.(diff, true)
        }
      } else if (interim) {
        onResult?.(finalTextRef.current + interim, false)
      }
    }

    recognition.onerror = (e: SpeechRecognitionErrorEventLike) => {
      onError?.(e?.error ?? 'SpeechRecognition error')
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition

    return () => {
      recognition.stop()
      recognitionRef.current = null
    }
    // onError / onResult は外から変わる可能性があるが、初期化を毎回やり直すのは避ける想定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, interimResults, continuous])

  const start = () => {
    if (!recognitionRef.current) return
    finalTextRef.current = ''
    lastResultIndexRef.current = -1
    lastFinalSegmentRef.current = ''
    recognitionRef.current.start()
    setIsListening(true)
  }

  const stop = () => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  const reset = () => {
    finalTextRef.current = ''
    lastResultIndexRef.current = -1
    lastFinalSegmentRef.current = ''
  }

  const syncExternalText = (text: string) => {
    finalTextRef.current = text
  }

  return { isListening, start, stop, reset, syncExternalText }
}
