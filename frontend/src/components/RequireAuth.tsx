'use client';

import { useEffect, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';

import { useAuth } from '@/lib/auth-context';

/**
 * Barrière d'authentification : redirige vers /login si aucune session
 * valide. Affiche un squelette pendant la restauration de session.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { token, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !token) router.replace('/login');
  }, [ready, token, router]);

  if (!ready || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <span
            className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-acid"
            role="status"
            aria-label="Chargement de la session"
          />
          <p className="text-sm text-muted">Chargement…</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
