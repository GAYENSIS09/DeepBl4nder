# DeepBl4nder

<p align="center">
  <img src="public/logo.svg" alt="DeepBl4nder Logo" width="300"/>
</p>

<p align="center">
  <strong>AI-Powered Local-First 3D Production Pipeline</strong><br/>
  Transform text prompts into 3D scenes, animations, and videos — entirely on your machine.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/blender-4.1+-orange.svg" alt="Blender 4.1+">
  <img src="https://img.shields.io/badge/UE5-lumen%2Fnanite-black?logo=unrealengine" alt="Unreal Engine 5">
  <img src="https://img.shields.io/badge/Godot-4-green?logo=godotengine" alt="Godot 4">
  <img src="https://img.shields.io/badge/AI%20Video-CogVideoX%2FSVD-purple" alt="AI Video">
  <img src="https://img.shields.io/badge/NOOA-0.0.8-red" alt="NOOA">
  <img src="https://img.shields.io/badge/LLM-llama.cpp%2FQwen3-green" alt="Local LLM">
</p>

---

## What is DeepBl4nder?

DeepBl4nder is a **local-first multi-agent production system** that runs entirely on your machine. Describe what you want in natural language, and a team of 14 specialized AI agents will:

1. **Plan** the story and storyboard
2. **Design** characters and environments  
3. **Build** the scene in your chosen engine (Blender, UE5, Godot, or AI Video)
4. **Render** the final output
5. **QA** and iterate until quality is achieved

```
"You are a hacker who discovers memories were sold" → [14 Agents] → 3D Scene + Animation
```

**No API keys required. No cloud dependencies. Your data never leaves your machine.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (TUI)                                   │
│                    ┌────────────────────┐                          │
│                    │ 14 NOOA Agents    │                          │
│                    │ Story, Storyboard,│                          │
│                    │ Director, Blender,│                          │
│                    │ QA, Audio, etc.   │                          │
│                    └────────┬──────────┘                          │
└─────────────────────────────┼─────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LOCAL LLM SERVER (llama.cpp)                     │
│                    ┌──────────────────────────┐                    │
│                    │  Cascade Routing:        │                    │
│                    │  Qwen3-1.5B (fast)       │                    │
│                    │  → Qwen3-4B (general)    │                    │
│                    │  → Qwen3-8B (coding)     │                    │
│                    └──────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Blender  │   │ UE5      │   │ Godot    │
        │ Worker   │   │ Server   │   │ Server   │
        │ (Docker) │   │ (Docker) │   │ (Docker) │
        └──────────┘   └──────────┘   └──────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Local-First** | Runs entirely on your machine — no API keys, no cloud |
| **14 Specialized Agents** | Story, Storyboard, Director, Blender, QA, Audio, Compositing, Localization, Review + more |
| **Local LLM (Qwen3)** | Cascade routing: 1.5B → 4B → 8B models via llama.cpp |
| **Multi-Engine** | Blender 4.1 (primary), Unreal Engine 5, Godot 4, AI Video |
| **TUI Interface** | Terminal UI with live agent stream, artifact browser |
| **Docker Simple** | `docker compose up -d` — LLM + Blender worker |
| **Budget Control** | Per-production cost tracking |
| **Crash Recovery** | Automatic resume via event journal |

---

## Quick Start

### Prerequisites

- Python 3.12+
- NVIDIA GPU with 8GB+ VRAM (for local LLM)
- Docker + NVIDIA Container Toolkit
- Blender 4.1+ (optional, for local runs)

### 1. Clone and Install

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder
pip install -e ".[tui]"
```

### 2. Download Local Models

```bash
# Download Qwen3 models (1.5B, 4B, 8B GGUF)
python -m DeepBl4nder.llm.download --all
```

### 3. Launch with Docker (Recommended)

```bash
# Start LLM server + Blender worker
docker compose up -d
```

This starts:
- **llm-server** (port 8080) — llama.cpp with Qwen3-8B
- **blender-worker** — Blender 4.1 headless + FFmpeg

### 4. Run the TUI

```bash
DeepBl4nder tui
```

The TUI connects to the local LLM server and lets you run productions interactively.

---

## Local Development (No Docker)

```bash
# Install with dev dependencies
pip install -e ".[tui,dev]"

# Download models
python -m DeepBl4nder.llm.download --all

# Run TUI directly (starts LLM server internally)
DeepBl4nder tui
```

---

## Pipeline Flow

```
Brief → Story → Storyboard → Director → Character/Environment → Blender → QA → Render
                                                                     │
                                                               ┌─────┘
                                                               ▼
                                                          Revision Loop
```

Each step is handled by a specialized NOOA agent with its own skills, strategies, and validation. The system automatically retries with feedback when QA fails.

---

## Engines Supported

| Engine | Status | Capabilities |
|--------|--------|-------------|
| **Blender** | Production Ready | Full bpy scripting, Cycles/EEVEE, headless Docker worker |
| **Unreal Engine 5** | Implemented | Lumen GI, Nanite, MRQ rendering, Sequencer (optional profile) |
| **Godot 4** | Implemented | GDScript execution, WebGL export, headless (optional profile) |
| **AI Video** | Implemented | Text-to-Video (CogVideoX), Image-to-Video (SVD) (optional profile) |

---

## Project Structure

```
DeepBl4nder/
├── agents/           # 14 NOOA agents + factory
│   ├── base.py       # BaseAgent with context management
│   ├── factory.py    # build_agents() - single source of truth
│   ├── story.py      # StoryAgent
│   ├── storyboard.py # StoryboardAgent
│   ├── director.py   # DirectorAgent
│   ├── blender.py    # BlenderAgent
│   ├── qa.py         # QAAgent
│   └── ...           # Audio, Compositing, Localization, Review...
├── production/       # PipelineRunner, BudgetTracker, EventLog
├── llm/              # Local LLM system
│   ├── model_registry.py    # Qwen3 model specs
│   ├── classifier.py        # Task classification
│   ├── cascade.py           # Cascade router (1.5B→4B→8B)
│   ├── server.py            # llama-cpp-python server
│   ├── client.py            # HTTP client
│   ├── interface.py         # Unified LLMClient for agents
│   └── download.py          # GGUF model downloader
├── domain/           # Typed domain models (Brief, SceneSpec, etc.)
├── bridges/          # Engine bridges (blender, ue5, godot, ai_video)
├── artifacts/        # ArtifactRegistry, ProvenanceGraph
├── plugins/          # KnowledgeGraph, RenderFarm, etc.
├── codegen/          # AST validator for Blender scripts
├── skills/           # 26 embedded skills
├── tui/              # Textual Terminal UI
│   ├── app.py        # Main TUI app
│   ├── embedded_api.py # In-process pipeline runner
│   ├── event_bridge.py  # Live agent event stream
│   ├── widgets/      # AgentStream, StatusBar, TaskBar
│   └── screens/      # Console, Library, Settings
├── cli.py            # CLI entry point
└── tests/            # Test suite
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Runtime | NOOA 0.0.8 |
| Local LLM | llama.cpp + Qwen3 (GGUF) |
| 3D Engine | Blender 4.1 (headless) |
| Real-time Engine | Unreal Engine 5 (optional) |
| Open Source Engine | Godot 4 (optional) |
| AI Video | CogVideoX / SVD (optional) |
| Video Post | FFmpeg |
| TUI | Textual (Python) |
| Validation | AST + CodePolicy |
| Lint/Type | Ruff, Mypy |
| CI/CD | GitHub Actions |

---

## Configuration

Environment variables (`.env` or shell):

```bash
# LLM
DeepBl4nder_MODELS_DIR=./models        # Where GGUF models are stored
DeepBl4nder_LLM_HOST=127.0.0.1         # LLM server host
DeepBl4nder_LLM_PORT=8080              # LLM server port

# Blender
BLENDER_EXE=/usr/local/bin/blender     # Blender binary path

# Budget
DeepBl4nder_BUDGET=1.0                 # Max USD per production

# TUI
DeepBl4nder_API_URL=http://localhost:8080  # For TUI to connect to LLM
```

---

## Docker Services

```bash
# Core (required)
docker compose up -d

# With UE5
docker compose --profile ue5 up -d

# With Godot
docker compose --profile godot up -d

# With AI Video
docker compose --profile ai-video up -d
```

| Service | Port | Description |
|---------|------|-------------|
| llm-server | 8080 | llama.cpp with Qwen3 models |
| blender-worker | — | Blender headless + FFmpeg |
| ue5-server | 8081 | Unreal Engine 5 (profile) |
| godot-server | 8082 | Godot 4 (profile) |
| ai-video-server | 8083 | AI Video generation (profile) |

---

## Commands

```bash
# Inspect environment
DeepBl4nder inspect

# Validate Blender script
DeepBl4nder validate script.py

# Download models
DeepBl4nder download --all

# Run TUI
DeepBl4nder tui

# Run tests
pytest
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.