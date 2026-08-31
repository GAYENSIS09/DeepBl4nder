import Link from 'next/link'
import { ArrowRight, Bot, Cpu, Box, Github, Zap, Shield, Terminal, Database, Workflow, Brain, Network, Puzzle } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-db-bg">
      {/* Header */}
      <header className="border-b border-db-border/50 backdrop-blur-sm sticky top-0 z-50 bg-db-bg/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img src="/DeepBl4nder/logo.svg" alt="DeepBl4nder" width={140} height={35} />
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/docs" className="text-db-muted hover:text-db-text transition text-sm font-medium">
              Docs
            </Link>
            <a href="https://github.com/GAYENSIS09/DeepBl4nder" target="_blank" rel="noopener noreferrer" className="text-db-muted hover:text-db-text transition">
              <Github className="w-5 h-5" />
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-db-accent/5 via-transparent to-transparent" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-db-accent/10 blur-[120px] rounded-full hero-glow" />

        <div className="relative max-w-4xl mx-auto px-6 py-32 text-center">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
            <span className="gradient-text">AI-Powered</span>
            <br />
            <span className="text-db-text">3D Production</span>
          </h1>

          <p className="text-lg md:text-xl text-db-muted max-w-2xl mx-auto mb-10 leading-relaxed">
            14 specialized AI agents collaborate to transform text into 3D scenes.
            Local LLM, multi-engine support, zero API keys.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link href="/docs/getting-started" className="inline-flex items-center justify-center gap-2 bg-db-accent text-db-bg font-semibold px-8 py-4 rounded-xl hover:bg-db-accent2 transition-all hover:scale-105 glow-sm">
              Get Started <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="https://github.com/GAYENSIS09/DeepBl4nder" target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 border border-db-border text-db-text font-semibold px-8 py-4 rounded-xl hover:border-db-accent/50 hover:bg-db-surface transition-all">
              <Github className="w-5 h-5" /> View Source
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-db-text mb-3">Why DeepBl4nder?</h2>
          <p className="text-db-muted">Production-ready AI pipeline for 3D content creation</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Bot className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">14 AI Agents</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Story, storyboard, director, character design, environment, animation,
              audio, music, QA, compositing, localization, review.
            </p>
          </div>

          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Brain className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Local LLM Cascade</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Qwen3-1.5B/4B/8B via llama-cpp-python. Heuristic classification routes
              tasks to the optimal model. Auto-escalation on failure.
            </p>
          </div>

          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Workflow className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Smart Pipeline</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Checkpoint/resume, budget tracking, revision loops, parallel post-production.
              Crash recovery via event journal replay.
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-6">
          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Network className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Knowledge Graph</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              JSON-backed knowledge graph tracks production entities.
              TF-IDF vector store for semantic domain schema search.
            </p>
          </div>

          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Database className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Context Optimization</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Multi-layer context management: pruning, deduplication, KV cache
              optimization. Progressive skill disclosure saves 70% tokens.
            </p>
          </div>

          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Puzzle className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">36+ Skills</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Embedded skills for 3D, narrative, audio, QA, and more.
              Progressive disclosure loads only what's needed.
            </p>
          </div>
        </div>
      </section>

      {/* Quick Start */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <div className="bg-db-surface border border-db-border rounded-2xl p-8 glow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Terminal className="w-5 h-5 text-db-accent" />
            <h2 className="text-xl font-bold text-db-text">Quick Start</h2>
          </div>
          <pre className="bg-db-bg border border-db-border rounded-xl p-6 text-sm overflow-x-auto"><code><span className="text-db-dim"># Clone and install</span>{'\n'}
<span className="text-db-accent">git clone</span> https://github.com/GAYENSIS09/DeepBl4nder.git{'\n'}
<span className="text-db-accent">cd</span> DeepBl4nder{'\n'}
<span className="text-db-accent">pip install</span> -e <span className="text-db-muted">".[tui]"</span>{'\n\n'}
<span className="text-db-dim"># Download models (~10GB)</span>{'\n'}
<span className="text-db-accent">python -m</span> DeepBl4nder.llm.download --all{'\n\n'}
<span className="text-db-dim"># Start services</span>{'\n'}
<span className="text-db-accent">docker compose</span> up -d{'\n\n'}
<span className="text-db-dim"># Launch TUI</span>{'\n'}
<span className="text-db-accent">DeepBl4nder</span> tui</code></pre>
        </div>
      </section>

      {/* Architecture Preview */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold text-db-text mb-3">4-Layer Architecture</h2>
          <p className="text-db-muted">Clean separation of concerns for maintainability</p>
        </div>

        <div className="grid md:grid-cols-4 gap-4">
          {[
            { label: 'UI Layer', desc: 'TUI + CLI', icon: Terminal, color: '#AAFF00' },
            { label: 'Agent Layer', desc: '14 NOOA Agents', icon: Bot, color: '#88CC00' },
            { label: 'LLM Layer', desc: 'Cascade Routing', icon: Brain, color: '#E6C229' },
            { label: 'Worker Layer', desc: 'Docker + GPU', icon: Cpu, color: '#56B6C2' },
          ].map((layer) => {
            const Icon = layer.icon
            return (
              <div key={layer.label} className="bg-db-surface border border-db-border rounded-xl p-5 text-center">
                <Icon className="w-8 h-8 mx-auto mb-3" style={{ color: layer.color }} />
                <h3 className="font-semibold text-db-text text-sm">{layer.label}</h3>
                <p className="text-xs text-db-dim mt-1">{layer.desc}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-6">
          {[
            { value: '14', label: 'AI Agents' },
            { value: '36+', label: 'Skills' },
            { value: '3', label: 'Local Models' },
            { value: '4', label: 'Engines' },
            { value: '10', label: 'Plugins' },
            { value: '0', label: 'API Keys' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl font-bold gradient-text mb-1">{stat.value}</div>
              <div className="text-sm text-db-muted">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-db-border">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <img src="/DeepBl4nder/logo.svg" alt="DeepBl4nder" width={120} height={30} />
            <p className="text-db-dim text-sm">
              Open-source under MIT License
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
