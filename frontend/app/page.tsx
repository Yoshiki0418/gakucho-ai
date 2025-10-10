'use client'

import { FaMicrophone, FaPaperPlane, FaCog } from 'react-icons/fa'
import Icon from '@/components/atoms/Icon'
import { MessageItem } from '@/components/organisms/MessageItem'

export default function IconDemoPage() {
  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '48px',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#232222ff',
        fontFamily: 'sans-serif',
        padding: '24px',
      }}
    >
      <h1 style={{ fontSize: '1.8rem', marginBottom: '8px' }}>🎨 Icon Component Demo</h1>

      {/* ========== symbol variant（操作アイコン） ========== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          alignItems: 'center',
        }}
      >
        <h2 style={{ fontSize: '1.2rem' }}>Symbol Icons</h2>
        <div style={{ display: 'flex', gap: '24px' }}>
          <Icon $variant="symbol" $icon={<FaMicrophone />} $size={48} $color="#007AFF" />
          <Icon $variant="symbol" $icon={<FaPaperPlane />} $size={48} $color="#FF9500" />
          <Icon $variant="symbol" $icon={<FaCog />} $size={48} $color="#333" />
        </div>
      </section>

      {/* ========== avatar variant（人物・AI） ========== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          alignItems: 'center',
        }}
      >
          <MessageItem
            name="あなた"
            avatarSrc="/avatars/user.png"
            text="学長先生、こんにちは。今日はお話しできて光栄です！"
            role="user"
          />

          <MessageItem
            name="大澤敏"
            avatarSrc="/avatars/gakucho.png"
            nameColor="#10B981"
            text="こんにちは。こちらこそ、こうして直接話せるのは嬉しいですね。入学式、緊張しましたか？"
            role="assistant"
          />


      </section>
    </main>
  )
}
