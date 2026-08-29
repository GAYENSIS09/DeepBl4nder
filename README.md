# DeepBl4nder

<p align="center">
  <img src="public/logo.svg" alt="DeepBl4nder Logo" width="300"/>
</p>

<p align="center">
  <strong>AI-Powered Multi-Engine Film Production Pipeline</strong><br/>
  Transform text prompts into 3D scenes, animations, and videos.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/blender-4.1+-orange.svg" alt="Blender 4.1+">
  <img src="https://img.shields.io/badge/UE5-lumen%2Fnanite-black?logo=unrealengine" alt="Unreal Engine 5">
  <img src="https://img.shields.io/badge/Godot-4-green?logo=godotengine" alt="Godot 4">
  <img src="https://img.shields.io/badge/AI%20Video-CogVideoX%2FSVD-purple" alt="AI Video">
  <img src="https://img.shields.io/badge/NOOA-0.0.8-red" alt="NOOA">
</p>

---

## What is DeepBl4nder?

DeepBl4nder is a **multi-agent production system** that orchestrates AI agents to create 3D content across multiple engines. Describe what you want in natural language, and a team of specialized agents will:

1. **Plan** the story and storyboard
2. **Design** characters and environments  
3. **Build** the scene in your chosen engine (Blender, UE5, Godot, or AI Video)
4. **Render** the final output
5. **QA** and iterate until quality is achieved

```
"You are a hacker who discovers memories were sold" → [Agents] → 3D Scene + Animation
```

## Architecture

```
                          USER
                            │
                            ▼
                   DeepBl4nder (Domain)
                            │
                            ▼
               NOOA Agent Runtime
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   Blender Agent      UE5 Agent         Godot Agent      AI Video Agent
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
   Blender Bridge     UE5 Bridge        Godot Bridge      AI Video Bridge
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
   Blender Worker     UE5 Server        Godot Server      AI Video Server
   (Headless)         (Lumen/Nanite)    (GDScript/WebGL)  (CogVideoX/SVD)
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Engine** | Blender, Unreal Engine 5, Godot 4, AI Video (CogVideoX, SVD, AnimateDiff) |
| **Multi-Agent** | Director, Story, Character, Environment, Blender, QA, Audio, Compositing, Localization agents |
| **26 Skills** | Cinematography, lighting, rigging, animation, sound design, and more |
| **Real-time Monitoring** | Live SSE streaming of pipeline progress, costs, and approvals |
| **Human-in-the-Loop** | Approve, reject, or request revisions at any stage |
| **Budget Control** | Per-production cost tracking with alerts |
| **Crash Recovery** | Automatic resume from last checkpoint via event journal |

## Supported Engines

| Engine | Status | Capabilities |
|--------|--------|-------------|
| **Blender** | Production Ready | Full bpy scripting, Cycles/EEVEE render, headless execution |
| **Unreal Engine 5** | Implemented | Lumen GI, Nanite, MRQ rendering, Sequencer control |
| **Godot 4** | Implemented | GDScript execution, WebGL export, headless mode |
| **AI Video** | Implemented | Text-to-Video (CogVideoX), Image-to-Video (SVD), AnimateDiff |

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Configure your LLM API key
cp .env.example .env
# Edit .env and set at least one: GROQ_API_KEY, GEMINI_API_KEY, NVIDIA_API_KEY

# Start everything
docker compose up -d
```

**Default credentials:** `admin@DeepBl4nder.local` / `changeme`

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | [3000](http://localhost:3000) | Next.js web interface |
| API | [8000](http://localhost:8000) | FastAPI REST + SSE streaming |
| API Docs | [8000/docs](http://localhost:8000/docs) | Swagger UI |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache / Queue |
| MinIO | 9000/9001 | Object storage |
| Langfuse | 3001 | LLM observability |

**Optional engines** (Docker profiles):
- `ue5-server` (port 8080) — Unreal Engine 5 REST API
- `godot-server` (port 8081) — Godot 4 REST API  
- `ai-video-server` (port 8082) — AI Video generation REST API

### Verify

```bash
curl http://localhost:8000/health
docker compose ps
```

## Local Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
alembic upgrade head
python -m uvicorn DeepBl4nder.api.app:app --reload

# Test
pytest
```

## CLI

```bash
DeepBl4nder --version
DeepBl4nder inspect scene.json
DeepBl4nder validate scene.json
DeepBl4nder seed
```

## Production Pipeline

```
Brief → Story → Storyboard → Director → Character/Environment → Blender → QA → Render
                                                                    │
                                                              ┌─────┘
                                                              ▼
                                                         Revision Loop
```

Each step is handled by a specialized NOOA agent with its own skills, strategies, and validation. The system automatically retries with feedback when QA fails.

## Project Structure

```
DeepBl4nder/
├── agents/          # NOOA agents (director, blender, ue5, godot, ai_video, qa, ...)
├── domain/          # Typed domain models (SceneSpec, QAReport, ...)
├── skills/          # 26 skill definitions (cinematography, lighting, ...)
├── bridges/         # REST clients for external engines
├── plugins/         # 13 plugins (blender, ue5, godot, ai-video, ffmpeg, ...)
├── codegen/         # AST validation & code generation
├── artifacts/       # Versioning & provenance
├── production/      # Pipeline runner, budget, recovery
├── api/             # FastAPI gateway + SSE
├── frontend/        # Next.js 14 web interface
└── tests/           # 253 tests
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Runtime | NOOA 0.0.8 |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 / SQLite (dev) |
| Cache | Redis 7 |
| Storage | MinIO |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| 3D Engine | Blender 4.1 (headless) |
| Real-time Engine | Unreal Engine 5 (optional) |
| Open Source Engine | Godot 4 (optional) |
| AI Video | CogVideoX / SVD / AnimateDiff (optional) |
| Video Post | FFmpeg |
| LLM Providers | Gemini, Groq, NVIDIA, OpenRouter, Cloudflare |
| Observability | Langfuse |
| Validation | AST + CodePolicy |
| CI/CD | GitHub Actions, Ruff, Mypy, Pytest |

## Quality Metrics

| Metric | Target |
|--------|--------|
| Brief → First Render | < 5 min (demo), < 10 min (10s sequence) |
| Cost per Demo Scene | < $1.00 (LLM + render) |
| First-pass QA Rate | >= 60% at maturity |
| Parallel Workers | 3 per machine |
| Crash Recovery | Automatic via event replay |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.
