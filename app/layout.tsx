import './globals.css'
import type { Metadata } from 'next'
import { Analytics } from "@vercel/analytics/next"

export const metadata: Metadata = {
  title: 'AI Agent TIDB',
  description: 'AI-powered course recommendation system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="th">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
