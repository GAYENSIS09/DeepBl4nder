'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

import { useAuth } from '@/lib/auth-context';

const NAV = [
  { href: '/', label: 'Tableau de bord', icon: '◈' },
  { href: '/pipeline', label: 'Pipeline', icon: '▷' },
  { href: '/realtime', label: 'Temps réel', icon: '⇄' },
  { href: '/library', label: 'Bibliothèque', icon: '☰' },
  { href: '/costs', label: 'Coûts', icon: '¤' },
  { href: '/members', label: 'Membres', icon: '⊕' },
  { href: '/settings', label: 'Paramètres', icon: '⚙' },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  return (
    <>
      {/* Mobile hamburger */}
      <button
        type="button"
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-3 left-3 z-50 flex h-10 w-10 items-center justify-center rounded-lg bg-off-black border border-border text-muted hover:text-off-white lg:hidden"
        aria-label="Toggle menu"
      >
        <span className="text-lg">{mobileOpen ? '✕' : '☰'}</span>
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[200px] flex-col bg-off-black border-r border-border transition-transform duration-200 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0`}
      >
        <Link href="/" className="flex items-center gap-2.5 border-b border-border px-5 py-4" onClick={() => setMobileOpen(false)}>
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          <span className="font-display text-sm font-bold tracking-tight text-off-white">
            Deep<span className="text-acid">Bl4nder</span>
          </span>
        </Link>

        <nav className="flex-1 space-y-0.5 px-3 py-4" aria-label="Navigation principale">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? 'page' : undefined}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active ? 'bg-acid/10 text-acid font-medium' : 'text-muted hover:bg-border/40 hover:text-off-white'
                }`}
              >
                <span className="w-4 text-center text-xs opacity-70">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-4">
          {user && (
            <p className="truncate text-xs text-muted" title={user.email}>
              {user.full_name || user.email}
            </p>
          )}
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 w-full rounded-lg px-3 py-1.5 text-left text-xs text-muted transition-colors hover:bg-border/40 hover:text-red-400"
          >
            Se déconnecter
          </button>
        </div>
      </aside>
    </>
  );
}
