import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DeepBl4nder - AI-Powered 3D Production',
  description: 'Open-source AI agent orchestration for 3D animation and rendering.',
  icons: { icon: '/favicon.svg' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  )
}
