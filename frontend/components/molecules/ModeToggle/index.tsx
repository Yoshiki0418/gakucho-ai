'use client'

import React, { CSSProperties } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, Mic } from 'lucide-react'

export type InputMode = 'text' | 'voice'

interface ModeToggleProps {
  mode: InputMode
  onChange: (mode: InputMode) => void
}

export const ModeToggle: React.FC<ModeToggleProps> = ({ mode, onChange }) => {
  const isText = mode === 'text'
  const isVoice = mode === 'voice'

  const activeColor = '#FFFFFF'
  const inactiveTextColor = '#CBD5F5'
  const inactiveIconColor = '#9CA3AF'

  const containerStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    padding: 2,
    borderRadius: 999,
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(148, 163, 184, 0.25)',
    boxShadow: '0 6px 16px rgba(15,23,42,0.7)',
    backdropFilter: 'blur(16px)',
    position: 'relative',
    width: 'fit-content',
  }

  const buttonBase: CSSProperties = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    borderRadius: 999,
    border: 'none',
    padding: '6px 10px',
    fontSize: 13.5,
    fontWeight: 500,
    cursor: 'pointer',
    background: 'transparent',
    whiteSpace: 'nowrap',
    outline: 'none',
    color: '#FFF',
    zIndex: 2,
  }

  const indicatorWidth = isText
    ? 'calc(50% + 12px)' 
    : 'calc(50% - 14px)' 

  const activeIndicatorStyle: CSSProperties = {
    position: 'absolute',
    top: 2,
    bottom: 2,
    width: indicatorWidth,
    borderRadius: 999,
    background:
      'linear-gradient(135deg, rgba(59,130,246,0.45) 0%, rgba(37,99,235,0.35) 100%)',
    border: '1px solid rgba(59,130,246,0.7)',
    boxShadow: '0 0 16px rgba(59,130,246,0.6)',
    zIndex: 1,
  }

  return (
    <div style={containerStyle}>
      <motion.div
        layout
        layoutId="modeIndicator"
        style={{
          ...activeIndicatorStyle,
          left: mode === 'text' ? 2 : 'calc(50% + 12px)', 
        }}
        transition={{
          type: 'spring',
          stiffness: 350,
          damping: 30,
        }}
      />

      {/* TEXT */}
      <button
        type="button"
        onClick={() => onChange('text')}
        style={{
          ...buttonBase,
          color: isText ? activeColor : inactiveTextColor,
        }}
      >
        <MessageSquare
          style={{
            width: 14,
            height: 14,
            zIndex: 3,
            color: isText ? activeColor : inactiveIconColor,
          }}
        />
        <span style={{ position: 'relative', zIndex: 3, color: '#FFF' }}>
          テキスト
        </span>
      </button>

      {/* VOICE */}
      <button
        type="button"
        onClick={() => onChange('voice')}
        style={{
          ...buttonBase,
          color: isVoice ? activeColor : inactiveTextColor,
        }}
      >
        <Mic
          style={{
            width: 14,
            height: 14,
            zIndex: 3,
            color: isVoice ? activeColor : inactiveIconColor,
          }}
        />
        <span style={{ position: 'relative', zIndex: 3, color: '#FFF' }}>
          音声
        </span>
      </button>
    </div>
  )
}
