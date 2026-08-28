# DeepBl4nder

<p align="center">
  <img src="public/logo.svg" alt="DeepBl4nder Logo" width="300"/>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/blender-4.1+-orange.svg" alt="Blender 4.1+">
</p>

---

## Context and Vision

The core idea is to leverage a multi-agent architecture using [NVIDIA NeMo Labs OO-Agents](https://github.com/NVIDIA-NeMo/labs-OO-Agents) to drive Blender in a structured way. Before discussing agents, it is important to understand how a film or animation is actually produced:

1. Intent and Briefing
2. Script and Narrative Structure
3. Storyboard
4. Previsualization (Previs / Animatic) + Reference Soundtrack
5. Technical Feasibility Study
6. Asset Preparation (Modeling)
7. UV Mapping / Texturing / Shading
8. Rigging and Weight Painting
9. Staging (Layout) in Blender
10. Animation, Camera, and Lighting (add simulations if needed)
11. Preliminary Render (Quality Tests)
12. Iterations and Corrections (back to steps 9 or 10)
13. Final Render (Render Farm or Local)
14. Compositing
15. Final Audio Mixing, Subtitles, and Languages
16. Quality Control and Export (codec, colors, etc.)

This approach would allow transforming a vague request such as "make a suspense scene in an alleyway" into a usable Blender scene, then into an animated or filmed version.

## Objectives and Non-Objectives

### Objectives

- Transform a textual intent into a Blender scene, storyboard, short sequence, or visual study.
- Break down production into precise competencies linked to well-defined agents and sub-agents.
- Provide a reusable orchestration runtime with a modular and extensible architecture.
- Ensure traceability (provenance, versions), observability, and cost control.
- Keep the human in the loop at every step where the decision has value.

### Non-Objectives

- Generate autonomous feature films from the start (the MVP targets 5 to 10 second sequences).
- Replace studio expertise: DeepBl4nder is assisted production, not a replacement.
- Write all the code at once: this document describes the target; implementation follows an incremental path.

### Quality and Success Metrics

The architecture cannot be judged without measurable targets. These objectives are reviewed at each implementation milestone:

- **Latency**: from brief to first trial render, target < 5 min on demo scene; < 10 min for a 10 s sequence.
- **Cost**: target < 1 EUR per demo scene (LLM + render), measured via cost provenance.
- **Quality**: first-pass QA pass rate >= 60% at maturity, measured on a golden set of reference scenes.
- **Scalability**: 3 parallel workers on one machine, 1 worker per scene, GPU render; the system tolerates adding a worker without restart.
- **Reliability**: an interrupted production (Runtime Controller crash) resumes by replaying unconsumed events; no data loss accepted.
- **Observability**: state and cost visible in real time; budget overrun alert within 30 s.
- **Security**: no generated code runs outside the authorized perimeter; no unauthorized operation is silently executed.

## Competencies to Cover

- Narrative and dramatic structure
- Dialogue writing
- Shot breakdown
- Visual composition
- Asset creation and management
- Rigging and posing
- Character and object animation
- Camera and framing
- Lighting and ambiance
- Sound design
- Music and mixing
- Voices, accents, and diction
- Translation and subtitles
- Feasibility study and previsualization
- Continuity and quality control

## Use Cases

- Generate a Blender scene from a text brief.
- Create a simple storyboard before animation.
- Produce an animatic to preview an episode or short film.
- Prepare a stylized sequence (anime, cartoon, or semi-realistic).
- Quickly study several variants of set, lighting, or camera before production.
- Evaluate if an idea is technically feasible within a given deadline and resources.
- Help a creator iterate faster on set, camera, and movement.
- Add an audio track, sound effects, and ambient music suited to the scene.
- Manage multiple languages for dialogues, subtitles, and interface.

## Quick Start

### Prerequisites

- Python 3.12+
- Blender 4.1+
- PostgreSQL (or use Docker)
- An API key for at least one LLM provider (Groq, Gemini, NVIDIA, OpenRouter, or Cloudflare)

### Docker (Recommended)

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Start all services
docker compose up -d

# Access the API
curl http://localhost:8000/health

# Access the frontend
# Open http://localhost:3000
```

### Local Development

```bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials

# Run database migrations
alembic upgrade head

# Start the API
python -m uvicorn DeepBl4nder.api.app:app --reload

# Run tests
pytest
```

### CLI Usage

```bash
# Show version
DeepBl4nder --version

# Inspect a scene spec
DeepBl4nder inspect scene.json

# Validate a scene spec
DeepBl4nder validate scene.json

# Seed default accounts
DeepBl4nder seed
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
