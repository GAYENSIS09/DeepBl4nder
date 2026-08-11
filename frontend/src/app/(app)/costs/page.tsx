'use client';

import { useEffect, useState } from 'react';

import { api, type UsageOut } from '@/lib/api';
import { Badge, Card, CardHeader, EmptyState, Skeleton, Stat } from '@/components/ui';
import { useProductionTree } from '@/hooks/useProductionTree';
import { productionStatusLabel } from '@/lib/productions';
import { fmtCost, fmtDateTime } from '@/lib/format';

export default function CostsPage() {
  const { productions, error, isLoading } = useProductionTree(5000);
  const { usage } = useUsage();

  const total = productions.reduce((sum, item) => sum + item.production.cost, 0);
  const maxCost = Math.max(0.0001, ...productions.map((item) => item.production.cost));

  return (
    <div className="animate-fade-up p-6 md:p-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight text-off-white">Coûts</h1>
        <p className="mt-1 text-muted">Consommation par production, cumulée par les agents NOOA.</p>
      </header>

      {error ? (
        <Card className="mb-8 border-red-500/40">
          <CardHeader
            title="Connexion à l'API impossible"
            subtitle={`${error instanceof Error ? error.message : String(error)} — Vérifiez que le serveur DeepBlender est démarré.`}
          />
        </Card>
      ) : null}

      <UsagePanel usage={usage} />

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Stat label="Productions" value={productions.length} />
        <Stat label="Coût total" value={fmtCost(total)} accent />
        <Stat label="Coût moyen" value={productions.length ? fmtCost(total / productions.length) : '—'} />
      </div>

      {isLoading && !productions.length ? (
        <div className="space-y-4">
          <Skeleton className="h-9 w-40" />
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : null}

      {!isLoading && !productions.length ? (
        <EmptyState
          title="Aucun coût enregistré"
          description="Lancez une production pour que les coûts des agents apparaissent ici."
        />
      ) : null}

      {productions.length ? (
        <Card>
          <CardHeader title="Répartition des coûts" subtitle="Chaque barre est proportionnelle au coût cumulé de la production." />
          <div className="space-y-4 p-5">
            {productions.map((item) => {
              const { production } = item;
              const pct = Math.round((production.cost / maxCost) * 100);
              return (
                <div key={production.id} className="space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium text-off-white">{production.name}</span>
                    <span className="flex items-center gap-2">
                      <Badge tone={production.status === 'failed' ? 'red' : production.status === 'completed' ? 'green' : 'muted'}>
                        {productionStatusLabel(production.status)}
                      </Badge>
                      <span className="font-mono text-acid">{fmtCost(production.cost)}</span>
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-off-black">
                    <div className="h-full rounded-full bg-acid/70" style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-xs text-muted">
                    {production.current_step ? `Étape : ${production.current_step}` : 'En attente'} · mis à jour le{' '}
                    {fmtDateTime(production.updated_at)}
                  </p>
                </div>
              );
            })}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function useUsage(): { usage: UsageOut | null } {
  const [usage, setUsage] = useState<UsageOut | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const data = await api.getUsage();
        if (active) setUsage(data);
      } catch {
        // L'API est peut-être indisponible : on conserve l'affichage actuel.
      }
    };
    void load();
    const id = window.setInterval(() => void load(), 5000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  return { usage };
}

function QuotaBar({ label, value, quota, format }: { label: string; value: number; quota: number | null; format: (v: number) => string }) {
  if (quota === null) {
    return (
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="font-medium text-off-white">{label}</span>
          <span className="font-mono text-acid">{format(value)}</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-off-black">
          <div className="h-full rounded-full bg-acid/40" style={{ width: '100%' }} />
        </div>
        <p className="text-xs text-muted">Aucune limite configurée.</p>
      </div>
    );
  }
  const pct = Math.min(100, Math.round((value / quota) * 100));
  const over = value > quota;
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="font-medium text-off-white">{label}</span>
        <span className="flex items-center gap-2">
          {over ? <Badge tone="red">Limite dépassée</Badge> : null}
          <span className="font-mono text-acid">
            {format(value)} / {format(quota)}
          </span>
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-off-black">
        <div className={`h-full rounded-full ${over ? 'bg-red-500' : 'bg-acid/70'}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted">{pct} % du quota</p>
    </div>
  );
}

function UsagePanel({ usage }: { usage: UsageOut | null }) {
  if (!usage) return null;
  return (
    <Card className="mb-8">
      <CardHeader
        title="Usage et quotas"
        subtitle="Consommation comptabilisée sur vos organisations, à comparer aux limites configurées."
      />
      <div className="space-y-5 p-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <Stat label="Runs lancés" value={usage.runs} />
          <Stat label="Coût cumulé" value={fmtCost(usage.total_cost)} accent />
          <Stat label="Productions" value={usage.productions} />
        </div>
        <div className="space-y-5 border-t border-border pt-5">
          <QuotaBar
            label="Productions"
            value={usage.productions}
            quota={usage.quotas.productions}
            format={(v) => String(v)}
          />
          <QuotaBar label="Coût total" value={usage.total_cost} quota={usage.quotas.cost} format={fmtCost} />
        </div>
      </div>
    </Card>
  );
}
