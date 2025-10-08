'use client'

import Button from '@/components/atoms/Button'

export default function HomePage() {
  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
      }}
    >
      <h1>Button Variants Demo</h1>

      {/* Primaryボタン */}
      <Button $variants="Primary" onClick={() => alert('Primary clicked!')}>
        Primary
      </Button>

      {/* Toggleボタン（アクティブ・非アクティブ両方） */}
      <Button $variants="Toggle" $isactive>
        Active Toggle
      </Button>
      <Button $variants="Toggle" $isactive={false}>
        Inactive Toggle
      </Button>

      {/* Iconボタン（仮の中身） */}
      <Button $variants="Icon">
        <span role="img" aria-label="star">
          ⭐
        </span>
      </Button>
    </main>
  )
}
