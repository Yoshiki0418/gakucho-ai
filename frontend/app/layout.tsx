'use client'

import { ThemeProvider } from 'styled-components'
import GlobalStyles from '@/styles/GlobalStyles'
import theme from '@/styles/theme'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="ja"
      style={{
        height: '100%',
        overflow: 'hidden', 
      }}
    >
      <body
        style={{
          margin: 0,
          height: '100%',
          overflow: 'hidden', 
          backgroundColor: '#020617',
        }}
      >
        <ThemeProvider theme={theme}>
          <GlobalStyles />
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
