'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { browserSpeechDependencies, createSpeechController, SpeechPhase } from '../speechController'

interface UseSpeechRecognitionOptions {
  lang?: string
  model?: string
  autoSubmit?: boolean
  continuous?: boolean
  interimResults?: boolean
  onResult?: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
}

export function useSpeechRecognition({
  lang = 'ja-JP', model = 'browser', autoSubmit = false, continuous, interimResults, onResult, onError,
}: UseSpeechRecognitionOptions = {}) {
  const [phase, setPhase] = useState<SpeechPhase>('idle')
  const callbacks = useRef({ onResult, onError })
  callbacks.current = { onResult, onError }
  const controller = useRef<ReturnType<typeof createSpeechController> | null>(null)

  useEffect(() => {
    let mounted = true
    const current = createSpeechController({
      onPhase: (next) => { if (mounted) setPhase(next) },
      onResult: (text, final) => callbacks.current.onResult?.(text, final),
      onError: (message) => callbacks.current.onError?.(message),
    }, browserSpeechDependencies())
    controller.current = current
    setPhase('idle')
    return () => {
      mounted = false
      current.cancel()
      if (controller.current === current) controller.current = null
    }
  }, [model, lang, autoSubmit, continuous, interimResults])

  const start = useCallback(() => {
    void controller.current?.start(model, autoSubmit, lang, { continuous, interimResults })
  }, [model, autoSubmit, lang, continuous, interimResults])
  const stop = useCallback(() => controller.current?.finish(), [])
  const reset = useCallback(() => controller.current?.cancel(), [])
  const syncExternalText = useCallback((text: string) => { void text }, [])

  return {
    isListening: phase === 'listening', isTranscribing: phase === 'transcribing',
    isStarting: phase === 'starting', start, stop, reset, syncExternalText,
  }
}
