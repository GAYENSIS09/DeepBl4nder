'use client';

import { useState } from 'react';

interface PipelineFormProps {}

export function PipelineForm({}: PipelineFormProps) {
  const [brief, setBrief] = useState(
    'Une ruelle sombre sous la pluie, un personnage marche lentement vers une porte pendant cinq secondes.'
  );
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // This would call the pipeline endpoint
      // For now, just validate the script
      const response = await fetch(`${API_URL}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: `import bpy\nprint("Brief: ${brief.replace(/"/g, '\\"')}")\n# TODO: DirectorAgent → SceneSpec → BlenderScript`
        }),
      });
      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="brief" className="block text-sm font-medium mb-2">
            Brief créatif
          </label>
          <textarea
            id="brief"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={4}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
            placeholder="Décrivez votre scène…"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
          >
            {loading ? 'Exécution…' : 'Valider & Lancer le pipeline'}
          </button>
          <button
            type="button"
            onClick={() => {
              setResult(null);
              setError(null);
            }}
            className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            Effacer
          </button>
        </div>
      </form>

      {error && (
        <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
          {error}
        </div>
      )}

      {result && (
        <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg overflow-x-auto">
          <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{result}</pre>
        </div>
      )}

      <details className="border border-gray-700 rounded-lg bg-gray-800/50">
        <summary className="p-3 cursor-pointer font-medium">Étapes du pipeline</summary>
        <div className="px-3 pb-3 text-sm text-gray-400 space-y-1">
          <div>1. <strong>DirectorAgent</strong> → Brief → SceneSpec (shots, caméra, éclairage, personnages)</div>
          <div>2. <strong>BlenderAgent</strong> → SceneSpec → BlenderScript (bpy validé AST)</div>
          <div>3. <strong>Validation</strong> → CodePolicy (imports autorisés, pas d'os.system, etc.)</div>
          <div>4. <strong>QAAgent</strong> → Script/Render → QAReport (technique, visuel, continuité, sémantique)</div>
          <div>5. <strong>Révision</strong> → RevisionSpec ciblée (director/blender/audio/compositing/localization)</div>
          <div>6. <strong>Post-production</strong> → AudioAgent, CompositingAgent, LocalizationAgent</div>
        </div>
      </details>
    </section>
  );
}