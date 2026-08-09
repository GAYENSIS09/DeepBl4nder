interface BudgetData {
  llm: number;
  render: number;
  storage: number;
  external: number;
  total: number;
  budget: number;
  remaining: number;
  over_budget: boolean;
}

interface BudgetPanelProps {
  budget: BudgetData | undefined;
}

export function BudgetPanel({ budget }: BudgetPanelProps) {
  if (!budget) return <div className="animate-pulse">Chargement…</div>;

  const pct = Math.min(100, (budget.total / budget.budget) * 100);
  const isOver = budget.over_budget;

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Budget de production</h2>
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            isOver ? 'bg-red-900/30 text-red-400' : 'bg-green-900/30 text-green-400'
          }`}
        >
          {isOver ? 'DÉPASSÉ' : 'OK'}
        </span>
      </div>

      <div className="bg-gray-800 rounded-lg overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={`h-4 transition-all duration-300 ${
            isOver ? 'bg-red-500' : pct > 80 ? 'bg-yellow-500' : 'bg-green-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <BudgetCard label="Total" value={budget.total.toFixed(4)} unit="$" />
        <BudgetCard label="Budget" value={budget.budget.toFixed(4)} unit="$" />
        <BudgetCard label="Restant" value={budget.remaining.toFixed(4)} unit="$" />
        <BudgetCard label="Utilisé" value={`${pct.toFixed(1)}%`} />
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <BudgetCard label="LLM" value={budget.llm.toFixed(4)} unit="$" />
        <BudgetCard label="Render" value={budget.render.toFixed(4)} unit="$" />
        <BudgetCard label="Storage" value={budget.storage.toFixed(4)} unit="$" />
        <BudgetCard label="Externe" value={budget.external.toFixed(4)} unit="$" />
      </div>

      <details className="border border-gray-700 rounded-lg bg-gray-800/50">
        <summary className="p-3 cursor-pointer font-medium">Alertes & Politique</summary>
        <div className="px-3 pb-3 text-sm text-gray-400 space-y-1">
          <div>• Alerte émise <strong>une seule fois</strong> au franchissement du budget</div>
          <div>• Temps réel <strong>< 30s</strong> via SSE <code>/events</code> (type <code>budget_alert</code>)</div>
          <div>• Coûts trackés par étape : director, blender, qa, audio, compositing, localization</div>
          <div>• <code>cost_hook(step)</code> injecté dans <code>PipelineRunner</code></div>
        </div>
      </details>
    </section>
  );
}

function BudgetCard({ label, value, unit = '' }: { label: string; value: string; unit?: string }) {
  return (
    <div className="p-3 bg-gray-800 rounded-lg">
      <div className="text-xs text-gray-500 uppercase tracking-wider">{label}</div>
      <div className="text-xl font-mono font-bold text-white mt-1">
        {value}{unit && <span className="text-gray-400 text-base font-normal ml-1">{unit}</span>}
      </div>
    </div>
  );
}