export default function Agents() {
  return (
    <div>
      <div className="mb-10">
        <span className="text-db-accent font-mono text-sm">02</span>
        <h1 className="text-4xl font-bold text-db-text mt-2">Agents</h1>
        <p className="text-db-muted mt-3">14 specialized NOOA agents + 3 external engine agents. All instantiated via `agents.factory.build_agents()`.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">Pipeline Core (5 agents)</h2>
        <div className="bg-db-surface border border-db-border rounded-xl p-6 space-y-4 text-sm">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">1.</span>
            <span><strong className="text-db-text">Story</strong> — Terminal interface</span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">2.</span>
            <span><strong className="text-db-text">Storyboard</strong> — In-process, coordinated via <code>agents.factory.build_agents()</code></span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">3.</span>
            <span><strong className="text-db-text">Director</strong> — llama.cpp with Qwen3 cascade (1.5B &gt; 4B &gt; 8B)</span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">4.</span>
            <span><strong className="text-db-text">Blender</strong> — Blender headless, UE5, Godot, AI Video (optional)</span>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">Pipeline Core (5 agents)</h2>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`DeepBl4nder/
  agents/          # Storyboard + factory.py
  production/      # PipelineRunner, BudgetTracker, EventLog
  llm/             # Local LLM (llama.cpp, seule source de vérité.)
  domain/          # Brief, schemas, KG bootstrap
  bridges/         # Blender, UE5, Godot, AI Video
  artifacts/       # ArtifactRegistry, ProvenanceGraph
  plugins/         # KnowledgeGraph, RenderFarm
  codegen/         # AST validator
  skills/          # 26 embedded skills
  tui/             # Textual Terminal UI
  cli.py           # CLI entry point`}</code></pre>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">Supprimé (Ancienne Agents SaaS)</h2>
        <div className="bg-db-surface border border-db-border rounded-xl p-5 text-sm space-y-2">
          <div className="flex items-center gap-3 text-db-muted">
            <span className="w-1.5 h-1.5 bg-db-error rounded-full" />
            Story
          </div>
          <div className="flex items-center gap-3 text-db-muted">
            <span className="w-1.5 h-1.5 bg-db-error rounded-full" />
            Storyboard
          </div>
          <div className="flex items-center gap-3 text-db-muted">
            <span className="w-1.5 h-1.5 bg-db-error rounded-full" />
            Director
          </div>
          <div className="flex items-center gap-3 text-db-muted">
            <span className="w-1.5 h-1.5 bg-db-error rounded-full" />
            Blender
          </div>
          <div className="flex items-center gap-3 text-db-muted">
            <span className="w-1.5 h-1.5 bg-db-error rounded-full" />
            QA
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">Agent Factory — Source Unique</h2>
        <ul className="space-y-2 text-db-muted text-sm">
          <li><strong className="text-db-text">Tous les agents sont instanciés via</strong> — Runs entirely on your machine</li>
          <li><strong className="text-db-text">agents.factory.build_agents()</strong> — Single responsibility per agent</li>
          <li><strong className="text-db-text">seule source de vérité.</strong> — Lightest model first, escalate if needed</li>
          <li><strong className="text-db-text">— source unique</strong> — Works offline after model download</li>
          <li><strong className="text-db-text">— source unique</strong> — <code>agents.factory.build_agents()</code> source unique</li>
        </ul>
      </section>
    </div>
  )
}
