'use client'

import Button from '@/components/atoms/Button'
import Input from '@/components/atoms/InputText'
import UserIcon from '@/components/atoms/Icon'

export default function HomePage() {
  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#fafafa',
      }}
    >
      <h1>Atoms Components Demo</h1>

      {/* ========================== */}
      {/* Buttons */}
      {/* ========================== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <h2>Button Variants</h2>
        <Button $variants="Primary" onClick={() => alert('Primary clicked!')}>
          Primary
        </Button>

        <Button $variants="Toggle" $isactive>
          Active Toggle
        </Button>

        <Button $variants="Toggle" $isactive={false}>
          Inactive Toggle
        </Button>

        <Button $variants="Icon">
          <span role="img" aria-label="star">
            ⭐
          </span>
        </Button>
      </section>

      {/* ========================== */}
      {/* Inputs */}
      {/* ========================== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <h2>Input Variants</h2>
        <Input $variants="auth" placeholder="メールアドレスを入力" />
        <Input $variants="serch" placeholder="キーワード検索" />
        <Input $variants="chat" placeholder="メッセージを入力..." />
      </section>

      {/* ========================== */}
      {/* Icons */}
      {/* ========================== */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <h2>Icon Demo</h2>

        <UserIcon />
        <UserIcon $size={60} $color="#ffffff" $backgroundColor="#4A90E2" />
        <UserIcon $size={40} $color="#4A90E2" $backgroundColor="#E3F2FD" />
      </section>
    </main>
  )
}
