interface StatusData {
  skills: string[];
  plugins: Array<{ name: string; available: boolean }>;
  tools: string[];
  blender: boolean;
  worker_count?: number;
  gpu_count?: number;
}

interface StatusPanelProps {
  status: StatusData | undefined;
}

export function StatusPanel({ status }: StatusPanelProps) {
  if (!status) return <div className="animate-pulse">Chargement…</div>;

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-lg font-semibold mb-3">Compétences (Skills) — {status.skills.length}</h2>
        <div className="flex flex-wrap gap-2">
          {status.skills.map((skill) => (
            <span key={skill} className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gray-300">
              {skill}
            </span>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Plugins — {status.plugins.length}</h2>
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {status.plugins.map((plugin) => (
            <div
              key={plugin.name}
              className="p-3 bg-gray-800 rounded-lg flex items-center justify-between"
            >
              <span className="font-mono text-sm">{plugin.name}</span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  plugin.available ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
                }`}
              >
                {plugin.available ? 'Disponible' : 'Absent'}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Outils (Tools) — {status.tools.length}</h2>
        <div className="flex flex-wrap gap-2">
          {status.tools.map((tool) => (
            <span key={tool} className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gray-300 font-mono">
              {tool}
            </span>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Blender</h2>
        <div className="p-3 bg-gray-800 rounded-lg flex items-center gap-4">
          <span className="font-mono">
            {status.blender ? '✅ Disponible' : '❌ Absent (définir BLENDER_EXE)'}
          </span>
          {status.worker_count !== undefined && (
            <>
              <span className="px-2 py-1 bg-gray-700 rounded text-sm">Workers: {status.worker_count}</span>
              <span className="px-2 py-1 bg-gray-700 rounded text-sm">GPU: {status.gpu_count}</span>
            </>
          )}
        </div>
      </section>
    </div>
  );
}