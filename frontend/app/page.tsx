'use client'

import Text from '@/components/atoms/Text'

export default function LiveChatDemo() {
  return (
    <main
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        alignItems: 'flex-start',
        justifyContent: 'flex-start',
        height: '100vh',
        padding: '2rem',
        background: '#0d1117',
        color: 'white',
        fontFamily: 'sans-serif',
      }}
    >
      <h1 style={{ marginBottom: '1rem' }}>LiveChat Text Demo</h1>

      <Text $variants="livechat" $isUser={false}>
        <strong style={{ color: '#5FBB64' }}>大澤敏</strong>：こんにちは。AI学長システムへようこそ。
      </Text>

      <Text $variants="livechat" $isUser={true}>
        <strong>あなた</strong>：こんにちは！お会いできて光栄です。
      </Text>

      <Text $variants="livechat" $isUser={false}>
        <strong style={{ color: '#5FBB64' }}>大澤敏</strong>：ありがとうございます。今日はどんなお話をしましょうか？
      </Text>

      <Text $variants="livechat" $isUser={true}>
        <strong>あなた</strong>：学長AIプロジェクトについて教えてください！
      </Text>
    </main>
  )
}
