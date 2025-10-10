'use client'

import React from 'react'
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
  placeholder = 'ここに入力...',
  disabled = false,
}: InputWithMicProps) {
  return (
    <Flex
      $align_items="center"
      $justify_content="space-between"
      $backgroundColor="transparent"
      $borderRadius="16px"
      $padding="12px 16px"
      $width="100%"
      style={{
        position: 'relative',
      }}
    >
      {/* 入力欄 */}
      <InputText
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        $background='#000408'
        $borderRadius="10px"
        $width="100%"
        $height='60px'
        $color="#fff"
        $variants="chat"
        style={{
          flex: 1,
          fontSize: '1.1rem',
        }}
      />

      {/* マイクボタン */}
      <button
        onClick={onMicClick}
        disabled={disabled}
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '4px 8px',
        }}
      >
        <Icon $icon={<FaMicrophone />} $size={30} $color="#fff" />
      </button>
    </Flex>
  )
}
