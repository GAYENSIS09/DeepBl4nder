'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

import { useAuth } from '@/lib/auth-context';

const NAV = [
  { href: '/', label: 'Tableau de bord', icon: '◈' },
  { href: '/pipeline', label: 'Pipeline', icon: '▷' },
  { href: '/realtime', label: 'Temps réel', icon: '⇄' },
  { href: '/costs', label: 'Coûts', icon: '¤' },
  { href: '/members', label: 'Membres', icon: '⊕' },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-[200px] flex-col bg-off-black">
      <Link href="/" className="flex items-center gap-2 border-b border-border px-5 py-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-acid font-display text-sm font-bold text-black">
          D
        </span>
        <span className="font-display text-sm font-bold tracking-tight text-off-white">
          Deep<span className="text-acid">Blender</span>
        </span>
      </Link>

      <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Navigation principale">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                active ? 'bg-acid/10 text-acid' : 'text-muted hover:bg-border/40 hover:text-off-white'
              }`}
            >
              <span className="w-4 text-center">{item.icon}</span>
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
  );
}
