import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'TiDB AI Assistant',
  description: 'AI-powered course recommendation system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="th">
      <body>{children}</body>
    </html>
  )
}
