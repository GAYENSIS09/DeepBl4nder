export default function Architecture() {
  return (
    <div>
      <div className="mb-10">
        <span className="text-db-accent font-mono text-sm">02</span>
        <h1 className="text-4xl font-bold text-db-text mt-2">Architecture</h1>
        <p className="text-db-muted mt-3">System overview and design principles.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">High-Level Overview</h2>
        <div className="bg-db-surface border border-db-border rounded-xl p-6 space-y-4 text-sm">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">1.</span>
            <span><strong className="text-db-text">User (TUI)</strong> — Terminal interface</span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">2.</span>
            <span><strong className="text-db-text">14 NOOA Agents</strong> — In-process, coordinated via <code>agents.factory.build_agents()</code></span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">3.</span>
            <span><strong className="text-db-text">Local LLM Server</strong> — llama.cpp with Qwen3 cascade (1.5B &gt; 4B &gt; 8B)</span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-db-accent font-mono">4.</span>
            <span><strong className="text-db-text">Docker Workers</strong> — Blender headless, UE5, Godot, AI Video (optional)</span>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4">Project Structure</h2>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`DeepBl4nder/
  agents/          # 14 NOOA agents + factory.py
  production/      # PipelineRunner, BudgetTracker, EventLog
  llm/             # Local LLM (llama.cpp, cascade routing)
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
        <h2 className="text-xl font-semibold text-db-text mb-4">Design Principles</h2>
        <ul className="space-y-2 text-db-muted text-sm">
          <li><strong className="text-db-text">Local-First</strong> — Runs entirely on your machine</li>
          <li><strong className="text-db-text">Agent Isolation</strong> — Single responsibility per agent</li>
          <li><strong className="text-db-text">Cascade Routing</strong> — Lightest model first, escalate if needed</li>
          <li><strong className="text-db-text">No Cloud Dependencies</strong> — Works offline after model download</li>
          <li><strong className="text-db-text">Factory Centralisée</strong> — <code>agents.factory.build_agents()</code> source unique</li>
        </ul>
      </section>
    </div>
  )
}