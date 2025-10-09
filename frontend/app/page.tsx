'use client'

import { FaMicrophone, FaPaperPlane, FaCog } from 'react-icons/fa'
import Icon from '@/components/atoms/Icon'
import { SpeakerHeader } from '@/components/molecules/SpeakerHeader'
import { MessageContent } from '@/components/molecules/MessageContent'

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
        <SpeakerHeader
          name="大澤敏"
          avatarSrc="/avatars/gakucho.png"
          color="#10B981"
          weight="bold"
          avatarSize="clamp(40px, 3.5vw, 59px)"
          width='200px'
        />

          <SpeakerHeader
            name="Rumina"
            avatarSrc="/avatars/rumina.png"
            color="rgb(56, 189, 248)"
            suffix={<span className="text-xs bg-gray-700 px-1 rounded">AI</span>}
            status="online"
            width='200px'
          />

          <SpeakerHeader
            name="あなた"
            color="#d4d4d8"
            weight="semibold"
            avatarSize={48}
            status="busy"
            fontSize="clamp(14px, 2vw, 20px)"
            width='200px'
          />

          <MessageContent
            role="assistant"
            variant="plain"
            text="こんにちは。こちらこそ、こうして直接話せるのは嬉しいですね。入学式、緊張しましたか？"
          />

          <MessageContent
            role="user"
            variant="plain"
            text="学長先生、こんにちは。今日はお話しできて光栄です！"
          />

      </section>
    </main>
  )
}
