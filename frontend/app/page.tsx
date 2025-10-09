'use client'

import { FaMicrophone, FaPaperPlane, FaCog } from 'react-icons/fa'
import Icon from '@/components/atoms/Icon'

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
        backgroundColor: '#f8f8f8',
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
        <h2 style={{ fontSize: '1.2rem' }}>Avatar Icons</h2>
        <div style={{ display: 'flex', gap: '24px' }}>
          {/* ✅ 学長AI（画像・オンライン） */}
          <Icon
            $variant="avatar"
            $src="/avatars/gakucho.png"
            $status="online"
            $size={60}
            $backgroundColor="#ccc"
          />

          {/* ✅ ユーザー（名前・ビジー） */}
          <Icon
            $variant="avatar"
            $name="山本"
            $status="busy"
            $backgroundColor="#555"
            $size={60}
          />

          {/* ✅ 匿名ユーザー（オフライン） */}
          <Icon
            $variant="avatar"
            $name="?"
            $status="offline"
            $backgroundColor="#aaa"
            $size={60}
          />

          {/* ✅ ステータス非表示パターン（null指定） */}
          <Icon
            $variant="avatar"
            $name="Guest"
            $status={null}
            $backgroundColor="#888"
            $size={60}
          />

          {/* ✅ ステータス非表示パターン（false指定） */}
          <Icon
            $variant="avatar"
            $name="AI"
            $status={false}
            $backgroundColor="#444"
            $size={60}
          />
        </div>
      </section>
    </main>
  )
}
