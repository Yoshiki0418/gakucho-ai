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
    <html lang="ja">
      <body>
        <ThemeProvider theme={theme}>
          <GlobalStyles />
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
