'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';

import { useAuth } from '@/lib/auth-context';
import { useNotifications } from '@/lib/notifications';
import { Button, Card, CardBody, Field, FormError, Input } from '@/components/ui';

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const { notify } = useNotifications();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(email.trim(), password, fullName.trim());
      notify('success', 'Compte créé. Bienvenue sur DeepBl4nder.');
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création de compte impossible.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-md animate-fade-up">
        <div className="mb-8 text-center">
          <img src="/favicon.svg" alt="DeepBl4nder" className="mx-auto mb-4 h-14 w-14" />
          <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">
            Créer un <span className="text-acid">compte</span>
          </h1>
          <p className="mt-2 text-sm text-muted">Un seul compte pour piloter toutes vos productions.</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <Field label="Nom complet" htmlFor="fullName">
                <Input
                  id="fullName"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ada Lovelace"
                />
              </Field>
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
              <Field label="Mot de passe" htmlFor="password" hint="8 caractères minimum.">
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </Field>
              <FormError message={error} />
              <Button type="submit" disabled={busy || !email.trim() || password.length < 8} className="w-full">
                {busy ? 'Création…' : 'Créer le compte'}
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-muted">
              Déjà inscrit ?{' '}
              <Link href="/login" className="text-acid hover:underline">
                Se connecter
              </Link>
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
