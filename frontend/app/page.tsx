'use client'

import React, { useState } from 'react'
import { FaMicrophone, FaPaperPlane, FaCog } from 'react-icons/fa'
import Icon from '@/components/atoms/Icon'
import ChatPanel from '@/components/organisms/ChatPanel' // ✅ ChatPanelを使用

// 💬 デモ用メッセージデータ
const messages = [
  {
    id: '1',
    text: '学長先生、こんにちは。今日はお話しできて光栄です！私には可愛い彼女がいます',
    role: 'user',
  },
  {
    id: '2',
    text: 'こんにちは。こちらこそ、こうして直接話せるのは嬉しいですね。入学式、緊張しましたか？',
    role: 'assistant',
  },
  {
    id: '3',
    name: 'あなた',
    avatarSrc: '/avatars/user.png',
    text: 'ええ、とても緊張しました。でも先生方のお話が印象的で、モチベーションが高まりました。',
    role: 'user',
  },
  {
    id: '4',
    name: '大澤敏',
    avatarSrc: '/avatars/gakucho.png',
    text: 'それは何よりですね。大学生活の始まりを良い形で迎えられたようで、私も嬉しく思います。',
    role: 'assistant',
  },
  {
    id: '5',
    name: 'あなた',
    avatarSrc: '/avatars/user.png',
    text: 'これから研究室の活動も始まるので、いろいろ挑戦してみたいです！',
    role: 'user',
  },
  {
    id: '6',
    name: '大澤敏',
    avatarSrc: '/avatars/gakucho.png',
    text: '素晴らしい心構えですね。ぜひ多くを学び、良い経験を積んでください。',
    role: 'assistant',
  },
  {
    id: '7',
    name: 'あなた',
    avatarSrc: '/avatars/user.png',
    text: 'これから研究室の活動も始まるので、いろいろ挑戦してみたいです！',
    role: 'user',
  },
  {
    id: '8',
    name: 'あなた',
    avatarSrc: '/avatars/user.png',
    text: 'これから研究室の活動も始まるので、いろいろ挑戦してみたいです！',
    role: 'user',
  },
] as const;

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)

  const handleMicClick = () => {
    console.log('🎙️ Mic clicked')
  }

  const handleSend = async () => {
    if (!inputValue.trim()) return
    setIsSending(true)
    console.log('送信:', inputValue)
    await new Promise((r) => setTimeout(r, 1000))
    setIsSending(false)
    setInputValue('')
  }

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        height: '100vh',
        backgroundColor: '#000',
        fontFamily: 'sans-serif',
        padding: '0px',
      }}
    >
      {/* ✅ ChatPanel のみを中央に表示 */}
      <section
        style={{
          display: 'flex',
          justifyContent: 'flex-start', // ✅ 左寄せ
          alignItems: 'stretch',         // ✅ 高さ方向を埋める
          height: '100vh',               // ✅ 画面全体の高さに
          width: '100%',
          margin: 0,                     // ✅ 余白をなくす
          padding: 0,
        }}
      >
        <ChatPanel
          messages={messages}
          inputValue={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onMicClick={handleMicClick}
          onSend={handleSend}
          isSending={isSending}
        />
      </section>
    </main>
  )
}
