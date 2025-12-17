'use client'

import React from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import type { Components } from 'react-markdown'
import Flex from '@/components/styles/Flex'
import Icon from '@/components/atoms/Icon'
import { NameLabel } from '@/components/atoms/NameLabel'

export type BubbleMessage = {
  id: string
  text: string
  role?: 'user' | 'assistant'
  name?: string
  avatarSrc?: string
}

type MessageBubbleProps = {
  message: BubbleMessage
  index: number
  isSpeaking?: boolean
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  index,
  isSpeaking = false,
}) => {
  const isUser = message.role === 'user'
  const displayName = message.name || (isUser ? 'あなた' : '大澤敏')
  const avatarSrc =
    message.avatarSrc || (isUser ? '/avatars/user.png' : '/avatars/gakucho.png')

  const baseBubbleStyle: React.CSSProperties = {
    borderRadius: 18,
    padding: '12px 20px',
  }

  const bubbleStyle: React.CSSProperties = isUser
    ? {
        ...baseBubbleStyle,
        background:
          'linear-gradient(135deg, rgba(59,130,246,0.9) 0%, rgba(37,99,235,0.9) 100%)',
        boxShadow: '0 4px 16px rgba(59,130,246,0.25)',
      }
    : {
        ...baseBubbleStyle,
        background: 'rgba(15,23,42,0.7)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(148,163,184,0.15)',
        boxShadow: isSpeaking
          ? '0 0 24px rgba(59,130,246,0.6)'
          : '0 4px 16px rgba(0,0,0,0.2)',
      }

  // ✅ inline を使わない：className が language-xxx ならブロック扱い
  const markdownComponents: Components = {
    p: ({ children }) => (
      <p
        style={{
          color: '#E5E7EB',
          fontSize: 15,
          lineHeight: 1.6,
          margin: '0 0 8px',
        }}
      >
        {children}
      </p>
    ),

    pre: ({ children, ...props }) => (
      <pre
        {...props}
        style={{
          background: 'rgba(0,0,0,0.45)',
          padding: '14px 16px',
          borderRadius: 12,
          margin: '8px 0',
          overflowX: 'auto',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        {children}
      </pre>
    ),

    code: ({ children, className, ...props }) => {
      const isBlock =
        typeof className === 'string' && /language-\w+/i.test(className)

      // ブロックコード（```）: <pre> 側で枠を作るので <code> は素の見た目にする
      if (isBlock) {
        return (
          <code
            className={className}
            {...props}
            style={{
              fontFamily: 'Menlo, Consolas, monospace',
              fontSize: 14,
              color: '#F3F4F6',
              whiteSpace: 'pre',
              display: 'block',
            }}
          >
            {children}
          </code>
        )
      }

      // インラインコード（`text`）
      return (
        <code
          className={className}
          {...props}
          style={{
            background: 'rgba(255,255,255,0.1)',
            padding: '2px 4px',
            borderRadius: 4,
            fontSize: 14,
            color: '#F9FAFB',
            fontFamily: 'Menlo, Consolas, monospace',
          }}
        >
          {children}
        </code>
      )
    },

    a: ({ children, ...props }) => (
      <a
        {...props}
        style={{
          color: '#60A5FA',
          textDecoration: 'underline',
        }}
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    ),
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      style={{
        display: 'flex',
        gap: 12,
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {/* アシスタント側のアイコン＋名前 */}
      {!isUser && (
        <Flex
          $flex_direction="column"
          $alignItems="center"
          $gap="4px"
          style={{ flexShrink: 0 }}
        >
          <Icon
            $variant="avatar"
            $src={avatarSrc}
            $alt={`${displayName}のアイコン`}
            $size={36}
            $shape="circle"
          />
          <NameLabel
            name={displayName}
            color="#10B981"
            fontSize="0.7rem"
            weight="semibold"
          />
        </Flex>
      )}

      {/* バブル本体 */}
      <div
        style={{
          maxWidth: '75%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
        }}
      >
        {message.text && (
          <div style={bubbleStyle}>
            {isUser ? (
              <p
                style={{
                  color: '#ffffff',
                  fontSize: 15,
                  lineHeight: 1.6,
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {message.text}
              </p>
            ) : (
              <div className="gakucho-markdown">
                <ReactMarkdown components={markdownComponents}>
                  {message.text}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
