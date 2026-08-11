'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';

import { api, type WorkerOut } from '@/lib/api';
import { Badge, Button, Card, CardHeader, EmptyState, ProgressBar, Skeleton, Stat } from '@/components/ui';
import { useProductionTree } from '@/hooks/useProductionTree';
import { useNotifications } from '@/lib/notifications';
import { productionStatusLabel } from '@/lib/productions';
import type { ProductionTreeItem } from '@/lib/productions';
import { fmtCost, fmtDateTime, fmtDuration, fmtPercent, fmtTime } from '@/lib/format';

const STATUS_TONE: Record<string, 'acid' | 'green' | 'amber' | 'red' | 'blue' | 'muted'> = {
  draft: 'muted',
  queued: 'blue',
  running: 'acid',
  waiting_approval: 'amber',
  revising: 'blue',
  completed: 'green',
  failed: 'red',
  cancelled: 'muted',
  blocked: 'amber',
};

function rotationLabel(rotation: string): string {
  const labels: Record<string, string> = {
    adaptive: 'Adaptatif (pondéré)',
    random: 'Aléatoire',
  };
  return labels[rotation] ?? rotation;
}

export default function DashboardPage() {
  const { productions, error, isLoading, mutate } = useProductionTree();
  const { worker, workerError } = useWorker();
  const { notify } = useNotifications();

  const active = productions.filter((p) => p.production.status === 'running' || p.production.status === 'queued');
  const totalCost = productions.reduce((sum, p) => sum + p.production.cost, 0);

  const handleDeleteProject = useCallback(
    async (item: ProductionTreeItem) => {
      const projectName = item.project.name;
      if (
        !confirm(
          `Supprimer le projet « ${projectName} » ?\n\nToutes les productions associées (${item.org.name} · ${item.workspace.name}) seront supprimées. Cette action est irréversible.`,
        )
      ) {
        return;
      }
      try {
        await api.deleteProject(item.project.id);
        notify('success', `Projet « ${projectName} » supprimé.`);
        mutate();
      } catch (err) {
        notify('error', err instanceof Error ? err.message : 'Suppression impossible.');
      }
    },
    [mutate, notify],
  );

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Tableau de bord</h1>
          <p className="mt-1 text-muted">Vos productions audio-visuelles, propulsées par les agents NOOA.</p>
        </div>
        <Link href="/pipeline">
          <Button>Nouvelle production</Button>
        </Link>
      </header>

      {error ? (
        <Card className="mb-8 border-red-500/40">
          <CardHeader
            title="Connexion à l'API impossible"
            subtitle={`${error instanceof Error ? error.message : String(error)} — Vérifiez que le serveur DeepBlender est démarré.`}
          />
        </Card>
      ) : null}

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Stat label="Productions" value={productions.length} />
        <Stat label="En cours" value={active.length} accent />
        <Stat label="Coût total" value={fmtCost(totalCost)} />
      </div>

      <div className="mb-8">
        <WorkerCard worker={worker} error={workerError} />
      </div>

      {isLoading && !productions.length ? (
        <div className="space-y-4">
          <Skeleton className="h-9 w-56" />
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : null}

      {!isLoading && !productions.length ? (
        <EmptyState
          title="Aucune production"
          description="Lancez votre première production : décrivez un brief et les agents NOOA s'occupent de la pipeline (scénario, Blender, QA, audio…)."
          actions={
            <Link href="/pipeline">
              <Button>Créer une production</Button>
            </Link>
          }
        />
      ) : null}

      {productions.length ? (
        <section className="space-y-3">
          <h2 className="font-display text-lg font-semibold text-off-white">Productions récentes</h2>
          {productions.map((item) => (
            <ProductionCard key={item.production.id} item={item} onDeleteProject={handleDeleteProject} />
          ))}
        </section>
      ) : null}
    </div>
  );
}

function ProductionCard({
  item,
  onDeleteProject,
}: {
  item: ProductionTreeItem;
  onDeleteProject: (item: ProductionTreeItem) => void;
}) {
  const { production } = item;
  const tone = STATUS_TONE[production.status] ?? 'muted';
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [stopBusy, setStopBusy] = useState(false);
  const { notify } = useNotifications();

  const isRunning = production.status === 'running' || production.status === 'queued';

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteBusy(true);
    try {
      await onDeleteProject(item);
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleStop = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Arrêter la production « ${production.name} » ?`)) return;
    setStopBusy(true);
    try {
      await api.cancelProduction(production.id);
      notify('success', `Production « ${production.name} » arrêtée.`);
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Arrêt impossible.');
    } finally {
      setStopBusy(false);
    }
  };

  return (
    <Link href="/realtime" className="block">
      <Card className="transition-colors hover:border-acid/50">
        <div className="flex flex-wrap items-center gap-4 px-5 py-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-display font-medium text-off-white">{production.name}</h3>
              <Badge tone={tone}>{productionStatusLabel(production.status)}</Badge>
              <Badge tone="muted">v{production.version}</Badge>
            </div>
            <p className="mt-1 truncate text-sm text-muted">
              {item.project.name} · {item.workspace.name} · {item.org.name}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
              <span>Mis à jour à {fmtTime(production.updated_at)}</span>
              {production.started_at && <span>Durée : {fmtDuration(production.started_at, production.finished_at)}</span>}
              {production.current_step && <span>Étape : {production.current_step}</span>}
            </div>
            <ProgressBar value={production.progress} className="mt-3 max-w-md" />
          </div>
          <div className="flex flex-col items-end gap-2">
            <div>
              <p className="font-mono text-sm text-acid">{fmtCost(production.cost)}</p>
              <p className="mt-0.5 text-xs text-muted">{fmtPercent(production.progress)}</p>
            </div>
            <div className="flex gap-2">
              {isRunning ? (
                <Button
                  variant="ghost"
                  className="px-2 py-1 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
                  disabled={stopBusy}
                  onClick={handleStop}
                  title={`Arrêter la production « ${production.name} »`}
                >
                  {stopBusy ? '…' : '⏹ Arrêter'}
                </Button>
              ) : null}
              <Button
                variant="danger"
                className="px-2 py-1 text-xs"
                disabled={deleteBusy}
                onClick={handleDelete}
                title={`Supprimer le projet « ${item.project.name} » et toutes ses productions`}
              >
                {deleteBusy ? '…' : '🗑 Supprimer'}
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </Link>
  );
}

function useWorker(): { worker: WorkerOut | null; workerError: string | null } {
  const [worker, setWorker] = useState<WorkerOut | null>(null);
  const [workerError, setWorkerError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await api.getWorker();
        if (active) {
          setWorker(data);
          setWorkerError(null);
        }
      } catch (err) {
        if (active) setWorkerError(err instanceof Error ? err.message : 'Statut worker indisponible.');
      }
    };
    void load();
    const id = window.setInterval(() => void load(), 5000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  return { worker, workerError };
}

function WorkerCard({ worker, error }: { worker: WorkerOut | null; error: string | null }) {
  const statusTone = worker?.status === 'online' ? 'acid' : worker?.status === 'idle' ? 'muted' : 'red';

  return (
    <Card>
      <CardHeader
        title="Worker intégré"
        subtitle="File d'exécution des runs sur le serveur DeepBlender."
        actions={
          worker ? (
            <Badge tone={statusTone}>
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-current animate-pulse" />
              {worker.status === 'online' ? 'En ligne' : worker.status === 'idle' ? 'En attente' : worker.status}
            </Badge>
          ) : (
            <Badge tone="muted">—</Badge>
          )
        }
      />
      <div className="grid gap-4 px-5 py-4 sm:grid-cols-4">
        <Stat label="File d'attente" value={worker?.queue_depth ?? '—'} />
        <Stat label="Runs en cours" value={worker?.running.length ?? '—'} />
        <Stat label="Runs traités" value={worker?.processed ?? '—'} accent />
        <Stat label="Échecs" value={worker?.failed ?? '—'} />
      </div>
      {worker && worker.running.length ? (
        <div className="px-5 pb-4">
          <ul className="space-y-1 text-xs text-muted">
            {worker.running.map((run) => (
              <li key={run.production_id} className="truncate font-mono">
                {run.production_id} · depuis {fmtDateTime(new Date(run.since * 1000).toISOString())}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {worker && worker.routing.length ? (
        <div className="border-t border-white/10 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-medium text-off-white">Fournisseurs LLM</h3>
            <Badge tone="muted">{rotationLabel(worker.rotation)}</Badge>
          </div>
          <ul className="mt-3 space-y-2">
            {worker.routing.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <span className="w-24 font-mono text-off-white">{p.id}</span>
                <span
                  className="min-w-0 flex-1 truncate text-muted"
                  title={`${p.model} · ${p.base_url}`}
                >
                  {p.model}
                </span>
                {p.cooldown_remaining_s > 0 ? (
                  <Badge tone="amber">Cooldown {Math.ceil(p.cooldown_remaining_s)} s</Badge>
                ) : (
                  <Badge tone="acid">Actif</Badge>
                )}
                <span className="text-muted">
                  {p.successes} ok · {p.failures} échec{p.failures > 1 ? 's' : ''}
                </span>
              </li>
            ))}
          </ul>
          {worker.routing.some((p) => p.last_error) ? (
            <p className="mt-2 text-xs text-red-400/80">
              Dernière erreur : {worker.routing.map((p) => p.last_error).filter(Boolean)[0]}
            </p>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="px-5 pb-4 text-sm text-red-400">
          {error}
        </p>
      ) : null}
    </Card>
  );
}
