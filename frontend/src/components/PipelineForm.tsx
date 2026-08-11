'use client';

import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';

import { api } from '@/lib/api';
import { ensureProject } from '@/lib/productions';
import { useNotifications } from '@/lib/notifications';
import { Button, Card, CardBody, CardHeader, Field, FormError, TextArea, Input, Spinner } from '@/components/ui';

export function PipelineForm() {
  const router = useRouter();
  const { notify } = useNotifications();

  const [name, setName] = useState('');
  const [brief, setBrief] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const project = await ensureProject();
      const production = await api.createProduction(project.id, {
        name: name.trim() || `Production du ${new Date().toLocaleDateString('fr-FR')}`,
        brief: brief.trim(),
      });
      await api.runProduction(production.id);
      notify('success', `Production « ${production.name} » lancée.`);
      router.push(`/realtime?production=${encodeURIComponent(production.id)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de lancer la production.');
    } finally {
      setBusy(false);
    }
  };

  const canSubmit = brief.trim().length > 0 && !busy;

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Pipeline</h1>
        <p className="mt-1 text-muted">Décrivez un brief : les agents NOOA produisent la scène, de l'écriture au rendu.</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader title="Nouvelle production" subtitle="Organisation, workspace et projet sont créés automatiquement si besoin." />
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <Field label="Nom de la production" htmlFor="production-name">
                <Input
                  id="production-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ex. Ruelle sous la pluie"
                  maxLength={120}
                />
              </Field>

              <Field
                label="Brief créatif"
                htmlFor="production-brief"
                hint="Un paragraphe descriptif : lieu, ambiance, action, contraintes techniques."
                error={error}
              >
                <TextArea
                  id="production-brief"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder="Une ruelle étroite sous la pluie, néon vert, un personnage s'avance vers la caméra…"
                  rows={8}
                  required
                  invalid={Boolean(error)}
                  aria-describedby={error ? 'production-brief-error' : undefined}
                />
              </Field>

              <FormError id="production-brief-error" message={error} />

              <div className="flex items-center gap-3">
                <Button type="submit" disabled={!canSubmit}>
                  {busy ? (
                    <>
                      <Spinner className="border-t-black" /> Lancement…
                    </>
                  ) : (
                    'Créer et lancer'
                  )}
                </Button>
                {busy && <span className="text-sm text-muted">Envoi du brief au pipeline…</span>}
              </div>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
