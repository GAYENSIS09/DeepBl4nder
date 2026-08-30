export default function GettingStarted() {
  return (
    <div>
      <div className="mb-10">
        <span className="text-db-accent font-mono text-sm">01</span>
        <h1 className="text-4xl font-bold text-db-text mt-2">Getting Started</h1>
        <p className="text-db-muted mt-3">Get up and running in minutes.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-db-accent/10 rounded-md flex items-center justify-center text-db-accent text-xs font-mono">1</span>
          Prerequisites
        </h2>
        <div className="bg-db-surface border border-db-border rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-3 text-db-muted text-sm">
            <span className="w-1.5 h-1.5 bg-db-accent rounded-full" />
            Python 3.12+
          </div>
          <div className="flex items-center gap-3 text-db-muted text-sm">
            <span className="w-1.5 h-1.5 bg-db-accent rounded-full" />
            NVIDIA GPU with 8GB+ VRAM (for local LLM)
          </div>
          <div className="flex items-center gap-3 text-db-muted text-sm">
            <span className="w-1.5 h-1.5 bg-db-accent rounded-full" />
            Docker + NVIDIA Container Toolkit
          </div>
          <div className="flex items-center gap-3 text-db-muted text-sm">
            <span className="w-1.5 h-1.5 bg-db-accent rounded-full" />
            Blender 4.1+ (optional, for local runs)
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-db-accent/10 rounded-md flex items-center justify-center text-db-accent text-xs font-mono">2</span>
          Installation
        </h2>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`# Clone the repository
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Install with TUI support
pip install -e ".[tui]"`}</code></pre>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-db-accent/10 rounded-md flex items-center justify-center text-db-accent text-xs font-mono">3</span>
          Download Models
        </h2>
        <p className="text-db-muted text-sm mb-4">
          Download the Qwen3 GGUF models for local inference:
        </p>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`# Download all models (1.5B, 4B, 8B)
python -m DeepBl4nder.llm.download --all

# Or download specific models
python -m DeepBl4nder.llm.download --model qwen3-8b`}</code></pre>
        <p className="text-db-dim text-xs mt-3">Models are stored in ./models/ (gitignored)</p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-db-accent/10 rounded-md flex items-center justify-center text-db-accent text-xs font-mono">4</span>
          Launch with Docker
        </h2>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`# Start LLM server + Blender worker
docker compose up -d`}</code></pre>
        <p className="text-db-muted text-sm mt-3">
          This starts the LLM server (port 8080) and Blender worker.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold text-db-text mb-4 flex items-center gap-2">
          <span className="w-6 h-6 bg-db-accent/10 rounded-md flex items-center justify-center text-db-accent text-xs font-mono">5</span>
          Run TUI
        </h2>
        <pre className="bg-db-surface border border-db-border rounded-xl p-5 text-sm"><code>{`DeepBl4nder tui`}</code></pre>
        <p className="text-db-muted text-sm mt-3">
          The TUI connects to the local LLM server and lets you run productions interactively.
        </p>
      </section>
    </div>
  )
}