import type { Metadata } from 'next';
import localFont from 'next/font/local';

import './globals.css';
import { AuthProvider } from '@/lib/auth-context';
import { NotificationsProvider } from '@/lib/notifications';

const display = localFont({
  src: '../../public/fonts/SpaceGrotesk-Variable.woff2',
  variable: '--font-display',
  display: 'swap',
});

const mono = localFont({
  src: '../../public/fonts/JetBrainsMono-Variable.woff2',
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'DeepBl4nder — AI Audiovisual Production',
  description: 'Plateforme SaaS de production audiovisuelle assistée par agents IA. Pipeline complet : scénario, storyboard, Blender, UE5, Godot, AI Video, audio, compositing.',
  icons: { icon: '/favicon.svg' },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className={`${display.variable} ${mono.variable}`}>
      <body className="bg-black text-off-white font-body antialiased">
        <AuthProvider>
          <NotificationsProvider>{children}</NotificationsProvider>
        </AuthProvider>
      </body>
    </html>
  );
}