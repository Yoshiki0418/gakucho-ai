'use client'

import { useEffect, useRef, useState } from 'react'

interface UseSpeechRecognitionOptions {
  lang?: string
  interimResults?: boolean
  continuous?: boolean
  onResult?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
}

export function useSpeechRecognition({
  lang = 'ja-JP',
  interimResults = true,
  continuous = true,
  onResult,
  onError,
}: UseSpeechRecognitionOptions = {}) {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const lastResultIndexRef = useRef(-1)
  const finalTextRef = useRef('')
  const lastFinalSegmentRef = useRef('') 

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      onError?.('このブラウザでは音声認識がサポートされていません。')
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = lang
    recognition.interimResults = interimResults
    recognition.continuous = continuous

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = ''
      let newFinal = ''

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal && i <= lastResultIndexRef.current) continue

        if (result.isFinal) {
          newFinal += result[0].transcript
          lastResultIndexRef.current = i
        } else {
          interim += result[0].transcript
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

    recognition.onerror = (e) => onError?.(e.error)
    recognition.onend = () => setIsListening(false)
    recognitionRef.current = recognition
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
