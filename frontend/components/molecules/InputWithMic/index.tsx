'use client'

import React, { useState } from 'react'
import { FaMicrophone, FaStop } from 'react-icons/fa' // 停止アイコンを追加
import InputText from '@/components/atoms/InputText'
import Icon from '@/components/atoms/Icon'
import Flex from '@/components/styles/Flex'

interface InputWithMicProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  placeholder?: string
  disabled?: boolean
  // ↓↓↓ 追加: 録音中かどうかを受け取る
  isListening?: boolean
}

export default function InputWithMic({
  value,
  onChange,
  onMicClick,
  placeholder = '話しかけるか入力してください...',
  disabled = false,
  // ↓↓↓ デフォルトfalse
  isListening = false,
}: InputWithMicProps) {
  const [isFocused, setIsFocused] = useState(false)

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
      }}
    >
      {/* ガラスカードコンテナ */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          borderRadius: 14,
          padding: '6px 12px',
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(16px)',
          border: isFocused
            ? '2px solid rgba(59, 130, 246, 0.55)'
            : isListening // ★録音中は赤枠にして「聞いています」アピール
              ? '1px solid rgba(239, 68, 68, 0.6)'
              : '1px solid rgba(148, 163, 184, 0.18)',
          boxShadow: isFocused
            ? '0 0 0 4px rgba(59, 130, 246, 0.14), 0 8px 24px rgba(0,0,0,0.6)'
            : isListening // ★録音中は赤く発光させる
              ? '0 0 0 2px rgba(239, 68, 68, 0.3), 0 8px 24px rgba(0,0,0,0.6)'
              : '0 4px 18px rgba(0,0,0,0.45)',
          transition: 'border 0.2s ease, box-shadow 0.2s ease, background 0.2s ease',
        }}
      >
        <Flex
          $align_items="center"
          $justify_content="space-between"
          $width="100%"
          style={{ position: 'relative', gap: 8 }}
        >
          {/* 入力欄 */}
          <InputText
            value={value}
            onChange={onChange}
            // ★録音中はプレースホルダーを変える（これが一番重要）
            placeholder={isListening ? '聞いています...（もう一度押して送信）' : placeholder}
            disabled={disabled}
            $background="transparent"
            $backgroundColor="transparent"
            $border="none"
            $borderRadius="10px"
            $width="100%"
            $height="48px"
            $color="#ffffff"
            $variants="chat"
            style={{
              flex: 1,
              fontSize: '0.95rem',
              paddingLeft: '0.9rem',
              paddingRight: '5.2rem',
              outline: 'none',
            }}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
          />

          {/* マイクボタン */}
          <button
            type="button"
            onClick={onMicClick}
            disabled={disabled}
            style={{
              position: 'absolute',
              right: 12,
              top: '50%',
              // ★録音中は少し大きくして「押している感」を出す
              transform: isListening 
                ? 'translateY(-50%) scale(1.1)' 
                : 'translateY(-50%) scale(1)',
              width: 40,
              height: 40,
              borderRadius: '999px',
              // ★録音中は赤くする
              border: isListening
                ? '1px solid rgba(239, 68, 68, 0.6)'
                : '1px solid rgba(148,163,184,0.4)',
              background: isListening
                ? 'linear-gradient(135deg, #ef4444, #b91c1c)' // 赤グラデーション
                : 'linear-gradient(135deg, rgba(51,65,85,0.9), rgba(15,23,42,0.95))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.45 : 1,
              // ★録音中は強い影をつけて「起動中」に見せる
              boxShadow: disabled
                ? 'none'
                : isListening
                  ? '0 0 12px rgba(239, 68, 68, 0.7)' 
                  : '0 0 14px rgba(148,163,184,0.6)',
              transition: 'all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)', // 弾むようなアニメーション
            }}
          >
            <Icon 
              // ★アイコンを切り替える（停止ボタンにする）
              $icon={isListening ? <FaStop /> : <FaMicrophone />} 
              $size={18} 
              $color="#e5e7eb" 
            />
          </button>
        </Flex>
      </div>
    </div>
  )
}