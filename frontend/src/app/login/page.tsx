'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';

import { useAuth } from '@/lib/auth-context';
import { useNotifications } from '@/lib/notifications';
import { Button, Card, CardBody, Field, FormError, Input } from '@/components/ui';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { notify } = useNotifications();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      notify('success', 'Connexion réussie.');
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Échec de connexion.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-md animate-fade-up">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-acid font-display text-2xl font-bold text-black">
            D
          </span>
          <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">
            Deep<span className="text-acid">Blender</span>
          </h1>
          <p className="mt-2 text-sm text-muted">Production audiovisuelle assistée par agents IA.</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <Field label="Email" htmlFor="email">
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vous@exemple.com"
                />
              </Field>
              <Field label="Mot de passe" htmlFor="password">
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </Field>
              <FormError message={error} />
              <Button type="submit" disabled={busy || !email.trim() || !password} className="w-full">
                {busy ? 'Connexion…' : 'Se connecter'}
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-muted">
              Pas encore de compte ?{' '}
              <Link href="/register" className="text-acid hover:underline">
                Créer un compte
              </Link>
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
