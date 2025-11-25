'use client'

import React, { useState } from 'react'
import { FaMicrophone } from 'react-icons/fa'
import InputText from '@/components/atoms/InputText'
import Icon from '@/components/atoms/Icon'
import Flex from '@/components/styles/Flex'

interface InputWithMicProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  onMicClick?: () => void
  placeholder?: string
  disabled?: boolean
}

export default function InputWithMic({
  value,
  onChange,
  onMicClick,
  placeholder = '話しかけるか入力してください...',
  disabled = false,
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
          background: 'rgba(15, 23, 42, 0.8)', // tailwind: bg-slate-900/80
          backdropFilter: 'blur(16px)',
          border: isFocused
            ? '2px solid rgba(59, 130, 246, 0.55)' // focus時の青枠
            : '1px solid rgba(148, 163, 184, 0.18)',
          boxShadow: isFocused
            ? '0 0 0 4px rgba(59, 130, 246, 0.14), 0 8px 24px rgba(0,0,0,0.6)'
            : '0 4px 18px rgba(0,0,0,0.45)',
          transition: 'border 0.22s ease, box-shadow 0.22s ease, background 0.22s ease',
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
            placeholder={placeholder}
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
              paddingRight: '5.2rem', // 右側のマイク＋余白ぶん
              outline: 'none',
            }}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
          />

          {/* マイクボタン（右端に丸く浮かせる） */}
          <button
            type="button"
            onClick={onMicClick}
            disabled={disabled}
            style={{
              position: 'absolute',
              right: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              width: 40,
              height: 40,
              borderRadius: '999px',
              border: '1px solid rgba(148,163,184,0.4)',
              background:
                'linear-gradient(135deg, rgba(51,65,85,0.9), rgba(15,23,42,0.95))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.45 : 1,
              boxShadow: disabled
                ? 'none'
                : '0 0 14px rgba(148,163,184,0.6)',
              transition: 'all 0.18s ease',
            }}
          >
            <Icon $icon={<FaMicrophone />} $size={18} $color="#e5e7eb" />
          </button>
        </Flex>
      </div>
    </div>
  )
}
