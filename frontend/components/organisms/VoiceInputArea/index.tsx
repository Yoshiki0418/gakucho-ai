'use client'

import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Mic, Square, Volume2 } from 'lucide-react'

type VoiceInputAreaProps = {
  onTranscript: (text: string) => void
  disabled?: boolean
  isAISpeaking?: boolean
  onInterrupt?: () => void
}

/**
 * ✅ DOM の lib に SpeechRecognition 系の型が無い環境でもビルドできるように、
 *   必要最小限の型だけ自前定義する
 */
type SpeechRecognitionAlternative = {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
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
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

export const VoiceInputArea: React.FC<VoiceInputAreaProps> = ({
  onTranscript,
  disabled = false,
  isAISpeaking = false,
  onInterrupt,
}) => {
  const [isListening, setIsListening] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [previewText, setPreviewText] = useState('')

  const recognitionRef = useRef<SpeechRecognitionAlternative | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const skipAutoRestartRef = useRef(false)

  const propsRef = useRef({ onTranscript, isAISpeaking, onInterrupt })
  useEffect(() => {
    propsRef.current = { onTranscript, isAISpeaking, onInterrupt }
  }, [onTranscript, isAISpeaking, onInterrupt])

  // --- 音声認識の初期化 ---
  useEffect(() => {
    if (typeof window === 'undefined') return

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognitionCtor) {
      console.warn('SpeechRecognition API が利用できません')
      return
    }

    const recognition: SpeechRecognitionAlternative = new SpeechRecognitionCtor()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'ja-JP'

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let interim = ''
      let finalText = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const t = result[0]?.transcript ?? ''
        if (result.isFinal) {
          finalText += t
        } else {
          interim += t
        }
      }

      setPreviewText(interim || finalText)

      const { onTranscript, isAISpeaking, onInterrupt } = propsRef.current
      if ((interim || finalText) && isAISpeaking && onInterrupt) {
        onInterrupt()
      }

      if (finalText) {
        skipAutoRestartRef.current = true
        onTranscript(finalText)
        setPreviewText('')
      }
    }

    recognition.onerror = (e: any) => {
      console.error('SpeechRecognition error:', e?.error ?? e)
      setIsListening(false)
    }

    recognition.onend = () => {
      // stopListening() 直後の onend で再スタートしないためのガード
      if (isListening && !skipAutoRestartRef.current) {
        recognition.start()
      }
      skipAutoRestartRef.current = false
    }

    recognitionRef.current = recognition

    return () => {
      recognition.stop()
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
      if (audioContextRef.current) audioContextRef.current.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // --- 音声レベルの更新 ---
  const startAudioLevelMeter = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
      const AudioCtx =
        (window as any).AudioContext || (window as any).webkitAudioContext
      const audioCtx: AudioContext = new AudioCtx()
      const analyser = audioCtx.createAnalyser()
      const source = audioCtx.createMediaStreamSource(stream)
      source.connect(analyser)
      analyser.fftSize = 256

      audioContextRef.current = audioCtx
      analyserRef.current = analyser

      const update = () => {
        if (!analyserRef.current) return
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
        analyserRef.current.getByteFrequencyData(dataArray)
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        setAudioLevel(avg / 255)
        animationFrameRef.current = requestAnimationFrame(update)
      }
      update()
    } catch (e) {
      console.error('getUserMedia error:', e)
    }
  }

  const startListening = async () => {
    if (!recognitionRef.current || disabled) return
    await startAudioLevelMeter()
    recognitionRef.current.start()
    setIsListening(true)
  }

  const stopListening = () => {
    recognitionRef.current?.stop()
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    setIsListening(false)
    setAudioLevel(0)
    setPreviewText('')
  }

  const toggleListening = () => {
    if (isListening) {
      stopListening()
    } else {
      if (propsRef.current.isAISpeaking && propsRef.current.onInterrupt) {
        propsRef.current.onInterrupt()
      }
      startListening()
    }
  }

  // --- 波形バー（横に並ぶ小さいバー群） ---
  const renderWaveBars = () => {
    const barCount = 32
    const bars = []

    for (let i = 0; i < barCount; i++) {
      const baseHeight = 2
      const maxAddedHeight = 14
      const phase = (i / barCount) * Math.PI * 2
      const wave = Math.sin(phase + Date.now() / 200) * 0.3 + 0.7
      const h = baseHeight + audioLevel * maxAddedHeight * wave

      bars.push(
        <motion.div
          key={i}
          style={{
            width: 3,
            borderRadius: 999,
            background:
              'linear-gradient(to top, rgba(59,130,246,1), rgba(129,212,250,0.95))',
          }}
          animate={{ height: h }}
          transition={{ duration: 0.05 }}
        />,
      )
    }
    return bars
  }

  const disabledAll = disabled

  return (
    <div style={{ width: '100%', padding: '4px 0' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          width: '100%',
          minHeight: 56,
          borderRadius: 14,
          background: 'rgba(15,23,42,0.8)',
          backdropFilter: 'blur(16px)',
          border: isListening
            ? '2px solid rgba(59,130,246,0.5)'
            : '1px solid rgba(148,163,184,0.15)',
          boxShadow: isListening
            ? '0 0 0 4px rgba(59,130,246,0.12), 0 8px 24px rgba(0,0,0,0.45)'
            : '0 4px 18px rgba(0,0,0,0.5)',
          padding: '8px 10px 8px 14px',
          transition: 'border 0.18s ease, box-shadow 0.18s ease',
        }}
      >
        {/* 左側：状態テキスト + 波形 + プレビュー */}
        <div
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
          }}
        >
          {/* 状態行 */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 13,
              fontWeight: 500,
              color: isAISpeaking
                ? '#60A5FA'
                : isListening
                  ? '#FCA5A5'
                  : '#9CA3AF',
            }}
          >
            {isAISpeaking ? (
              <>
                <Volume2 size={16} />
                <span style={{ color: '#FFFFFF' }}>学長AIが話しています...</span>
              </>
            ) : isListening ? (
              <>
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '999px',
                    backgroundColor: '#EF4444',
                  }}
                />
                <span style={{ color: '#FFFFFF' }}>録音中...</span>
              </>
            ) : (
              <>
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '999px',
                    backgroundColor: '#6B7280',
                  }}
                />
                <span style={{ color: '#FFFFFF' }}>
                  マイクボタンを押して話しかけてください
                </span>
              </>
            )}
          </div>

          {/* 波形エリア（高さ小さめ） */}
          <div
            style={{
              height: 18,
              display: 'flex',
              alignItems: 'flex-end',
              gap: 2,
              opacity: isAISpeaking ? 0.6 : 1,
            }}
          >
            {isListening ? (
              renderWaveBars()
            ) : (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-end',
                  gap: 2,
                  width: '100%',
                }}
              >
                {Array.from({ length: 32 }).map((_, i) => (
                  <div
                    key={i}
                    style={{
                      width: 3,
                      height: 2,
                      borderRadius: 999,
                      backgroundColor: 'rgba(55,65,81,0.9)',
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* プレビュー（長い場合は省略） */}
          {previewText && isListening && (
            <p
              style={{
                fontSize: 12,
                color: '#E5E7EB',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              「{previewText}」
            </p>
          )}
        </div>

        {/* 右側：マイクボタン（丸） */}
        <motion.button
          type="button"
          onClick={toggleListening}
          disabled={disabledAll}
          whileHover={{ scale: disabledAll ? 1 : 1.05 }}
          whileTap={{ scale: disabledAll ? 1 : 0.95 }}
          style={{
            width: 48,
            height: 48,
            borderRadius: '999px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid rgba(255,255,255,0.12)',
            cursor: disabledAll ? 'not-allowed' : 'pointer',
            opacity: disabledAll ? 0.5 : 1,
            background: isListening
              ? 'linear-gradient(135deg, rgba(239,68,68,0.95), rgba(220,38,38,0.95))'
              : 'linear-gradient(135deg, rgba(59,130,246,0.95), rgba(37,99,235,0.95))',
            boxShadow: isListening
              ? '0 0 18px rgba(248,113,113,0.6)'
              : '0 0 16px rgba(59,130,246,0.6)',
            flexShrink: 0,
          }}
        >
          {isListening ? (
            <Square size={22} color="#ffffff" />
          ) : (
            <Mic size={26} color="#ffffff" />
          )}
        </motion.button>
      </div>
    </div>
  )
}
