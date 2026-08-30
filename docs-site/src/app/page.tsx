import Link from 'next/link'
import Image from 'next/image'
import { ArrowRight, Bot, Cpu, Box, Github, Zap, Shield, Terminal } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-db-bg">
      {/* Header */}
      <header className="border-b border-db-border/50 backdrop-blur-sm sticky top-0 z-50 bg-db-bg/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/logo.svg" alt="DeepBl4nder" width={140} height={35} priority />
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
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-db-accent/5 via-transparent to-transparent" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-db-accent/10 blur-[120px] rounded-full" />

        <div className="relative max-w-4xl mx-auto px-6 py-32 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 mb-8 text-xs font-medium text-db-accent bg-db-accent/10 border border-db-accent/20 rounded-full backdrop-blur-sm">
            <span className="w-2 h-2 bg-db-accent rounded-full animate-pulse" />
            v0.2 - Now with Local LLM
          </div>

          <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
            <span className="gradient-text">AI-Powered</span>
            <br />
            <span className="text-db-text">3D Production</span>
          </h1>

          <p className="text-lg md:text-xl text-db-muted max-w-2xl mx-auto mb-10 leading-relaxed">
            14 specialized AI agents collaborate to bring your stories to life.
            Run locally with Qwen3 models. No API keys required.
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
              <Cpu className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Local LLM</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Qwen3-1.5B/4B/8B via llama-cpp-python. Cascade routing picks the
              right model for each task. Your data stays private.
            </p>
          </div>

          <div className="group bg-db-surface border border-db-border rounded-2xl p-6 hover:border-db-accent/30 transition-all hover:glow-sm">
            <div className="w-12 h-12 bg-db-accent/10 rounded-xl flex items-center justify-center mb-4 group-hover:bg-db-accent/20 transition">
              <Box className="w-6 h-6 text-db-accent" />
            </div>
            <h3 className="text-lg font-semibold text-db-text mb-2">Multi-Engine</h3>
            <p className="text-sm text-db-muted leading-relaxed">
              Blender (primary), Unreal Engine 5, Godot 4, and AI video generation.
              Docker-ready with GPU support.
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
          <pre className="bg-db-bg border border-db-border rounded-xl p-6 text-sm"><code><span className="text-db-dim"># Install</span>{'\n'}
<span className="text-db-accent">pip install</span> -e <span className="text-db-muted">".[tui]"</span>{'\n\n'}
<span className="text-db-dim"># Download models</span>{'\n'}
<span className="text-db-accent">python -m</span> DeepBl4nder.llm.download --all{'\n\n'}
<span className="text-db-dim"># Launch</span>{'\n'}
<span className="text-db-accent">DeepBl4nder</span> tui</code></pre>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold gradient-text mb-1">14</div>
            <div className="text-sm text-db-muted">AI Agents</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold gradient-text mb-1">3</div>
            <div className="text-sm text-db-muted">Local Models</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold gradient-text mb-1">3</div>
            <div className="text-sm text-db-muted">Render Engines</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold gradient-text mb-1">0</div>
            <div className="text-sm text-db-muted">API Keys Needed</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-db-border">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <Image src="/logo.svg" alt="DeepBl4nder" width={120} height={30} />
            <p className="text-db-dim text-sm">
              Open-source under MIT License
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
