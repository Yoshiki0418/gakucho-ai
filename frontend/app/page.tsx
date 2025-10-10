'use client';

import React, { useState } from 'react';
import { FaMicrophone, FaPaperPlane, FaCog } from 'react-icons/fa';
import Icon from '@/components/atoms/Icon';
import { ChatList } from '@/components/organisms/ChatList';
import InputWithMic from '@/components/molecules/InputWithMic'

// 💬 デモ用メッセージデータ
const messages = [
  {
    id: '1',
    text: '学長先生、こんにちは。今日はお話しできて光栄です！',
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
] as const;

export default function ChatDemoPage() {
  const [inputValue, setInputValue] = useState('');

  const handleMicClick = () => {
    console.log('🎙️ Mic clicked');
  };

  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        height: '100vh',
        backgroundColor: '#232222',
        fontFamily: 'sans-serif',
        padding: '24px',
        overflowY: 'auto',
      }}
    >
      {/* ページタイトル */}
      <h1
        style={{
          fontSize: '1.8rem',
          marginBottom: '24px',
          color: '#f5f5f5',
        }}
      >
        💬 ChatList Component Demo
      </h1>

      {/* ========== Symbol Icons（操作アイコン） ========== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '48px',
        }}
      >
        <h2 style={{ fontSize: '1.2rem', color: '#ddd' }}>Symbol Icons</h2>

        <div style={{ display: 'flex', gap: '24px' }}>
          <Icon $variant="symbol" $icon={<FaMicrophone />} $size={48} $color="#007AFF" />
          <Icon $variant="symbol" $icon={<FaPaperPlane />} $size={48} $color="#FF9500" />
          <Icon $variant="symbol" $icon={<FaCog />} $size={48} $color="#ddd" />
        </div>
      </section>

      {/* ========== ChatList（チャットメッセージ一覧） ========== */}
      <section
        style={{
          width: '100%',
          maxWidth: '700px',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <ChatList messages={messages} width="100%" height="480px" />

        <InputWithMic
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)} // 🔹 入力値を更新
          onMicClick={handleMicClick}
        />
      </section>
    </main>
  );
}
