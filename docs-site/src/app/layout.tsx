import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'DeepBl4nder - AI-Powered 3D Production',
  description: 'Open-source AI agent orchestration for 3D animation and rendering.',
  icons: { icon: '/DeepBl4nder/favicon.svg' },
  openGraph: {
    title: 'DeepBl4nder - AI-Powered 3D Production',
    description: 'Open-source AI agent orchestration for 3D animation and rendering.',
    type: 'website',
    locale: 'en_US',
    siteName: 'DeepBl4nder Docs',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen antialiased font-inter bg-db-bg text-db-text">
        {children}
      </body>
    </html>
  )
}
