# 04 — Agents : 14 agents NOOA, runs, transitions, collaboration

> Architecture Local-First — Consolidée août 2026

## 14 Agents NOOA

```
StoryAgent → StoryboardAgent → DirectorAgent
    │
    ├─► CharacterDesignerAgent
    ├─► EnvironmentArtistAgent
    │
    ▼
BlenderAgent → QAAgent
    │
    ├─► AudioAgent
    │   ├─► MusicComposerAgent
    │   └─► SoundDesignerAgent
    │
    ├─► CompositingAgent
    ├─► AnimatorAgent
    ├─► LocalizationAgent
    └─► ReviewAgent
```

### Agents Core (Pipeline Principal)

| Agent | Responsabilité | Module |
|-------|---------------|--------|
| **StoryAgent** | Structure narrative, actes, beats, dialogues | `story.py` |
| **StoryboardAgent** | Plan visuel, caméras, composition par shot | `storyboard.py` |
| **DirectorAgent** | Décisions finales, coordination, SceneSpec | `director.py` |
| **BlenderAgent** | Génération script bpy, exécution worker | `blender.py` |
| **QAAgent** | QA technique/visuel/sémantique, RevisionSpec | `qa.py` |

### Agents Post-Production

| Agent | Responsabilité | Module |
|-------|---------------|--------|
| **CharacterDesignerAgent** | Specs personnages, apparence, personnalité | `char.py` |
| **EnvironmentArtistAgent** | Environnements, lighting, mood | `env.py` |
| **AnimatorAgent** | Animation personnages, keyframes | `animator.py` |
| **AudioAgent** | Plan audio, tracks, mix | `audio.py` |
| **MusicComposerAgent** | Composition musique, tempo, thème | `music.py` |
| **SoundDesignerAgent** | SFX, ambiances, Foley | `sfx.py` |
| **CompositingAgent** | Post-processing, color grading | `comp.py` |
| **LocalizationAgent** | Multi-langue, sous-titres, doublage | `loc.py` |
| **ReviewAgent** | Review finale, approval, delivery | `review.py` |

### Agents Moteurs Externes (Optionnels)

| Agent | Moteur | Module |
|-------|--------|--------|
| **UE5Agent** | Unreal Engine 5 (Lumen/Nanite/MRQ) | `ue5.py` |
| **GodotAgent** | Godot 4 (GDScript/WebGL) | `godot.py` |
| **AIVideoAgent** | CogVideoX / SVD / AnimateDiff | `ai_video.py` |

---

## Factory Centralisée — Source Unique

**Tous les agents sont instanciés via `agents.factory.build_agents()`** — c'est la **seule** source de vérité.

```python
from DeepBl4nder.agents.factory import build_agents

(story, storyboard, director, blender, qa,
 audio, animator, char, comp, env, loc, music, sfx, review) = build_agents()
```

Utilisé par :
- TUI (`tui/embedded_api.py`)
- Tests
- Tout consommateur externe

---

## Agent Run vs Production Run

```
Agent Run (NOOA)                    Production Run (DeepBl4nder)
Agent → Context → Memory             Project → Production Step → Artifact
  → Method → LLM → Code/Tool           → Worker → Render/Process → QA
  → Validation → Result                → Revision → Artifact Version
  → Events / Trace
```

Les deux sont **corrélés** par : `project_id`, `sequence_id`, `shot_id`, `production_run_id`, `step_id`, `agent_run_id`, `event_id`, `artifact_id`, `artifact_version`, `worker_id`, `model`, `skill_versions`, `cost`, `timestamps` — **jamais fusionnés**.

---

## Lifecycles

**Agent Run** (NOOA) :
```
CREATED → CONTEXT BUILT → MEMORY RECALLED → METHOD STARTED → LLM/CODE/TOOL
  → STATE UPDATED → EVENTS/TRACE → OUTPUT VALIDATED → COMPLETED
  Erreur : ERROR → EVENT → CONTEXT UPDATE → RETRY / REPAIR / ESCALATE
```

**Production Run** (DeepBl4nder) :
```
CREATED → PLANNED → RUNNING → ARTIFACTS CREATED → QA → PASS → COMPLETED
  / FAIL → REVISION → RUNNING / BLOCKED → HUMAN
```

---

## Transitions Principales

| Transition | Description |
|------------|-------------|
| **Agent → Agent** | Caller/callee, input/output types, contexte, mémoire, objets partagés, trace parent |
| **Agent → Skill** | Discover → load doc → reference/example → apply → result (enrichit contexte) |
| **Agent → Tool/Plugin** | Typed call → policy/permissions → tool → plugin → système externe → typed result |
| **Agent → CodeAct** | Raisonnement → Python généré → validation NOOA → policy DeepBl4nder → sandbox → exécution |
| **Artifact → QA** | Checks techniques, visuels, sémantiques, continuité → `QAReport` |
| **QA → Revision** | FAIL → classification → étape affectée → `RevisionSpec` → agent responsable → nouvelle exécution |

---

## Pipeline de Production (Séquentiel)

```
Brief
  │
  ▼
StoryAgent           # Narrative, acts, beats, dialogues
  │
  ▼
StoryboardAgent      # Visual plan, cameras, composition
  │
  ▼
DirectorAgent        # Final decisions, SceneSpec coordination
  │
  ├─► CharacterDesignerAgent
  ├─► EnvironmentArtistAgent
  │
  ▼
BlenderAgent         # Script bpy, worker execution
  │
  ▼
QAAgent              # Technical, visual, semantic, continuity
  │
  ├── PASS → Render → Compositing → Audio → Review → COMPLETED
  │
  └── FAIL → RevisionSpec → Agent responsable → RE-RUN (max 3)
```

---

## Révision Ciblée (QA → Revision)

```
QA FAIL
  │
  ▼
Classification issue:
  ├── CAMERA → CameraAgent → Layout → Pre-render
  ├── LIGHTING → LightingAgent → Re-light → Pre-render
  ├── ANIMATION → AnimatorAgent → Re-animate → Pre-render
  ├── CODE → BlenderAgent → Fix script → Re-run
  └── SEMANTIC → DirectorAgent → Re-plan → Re-run
```

Seule l'étape affectée est re-exécutée (pas toute la production).

---

## Collaboration

| Type | Exemple |
|------|---------|
| **Séquentielle** | `plan = await director.plan(brief); scene = await blender.build(plan); report = await qa.check(scene)` |
| **Parallèle** | `asyncio.gather(cinematography.plan(shot), lighting.plan(shot), animation.plan(shot))` |
| **Hiérarchique** | DirectorAgent supervise Story/Cinematography/Blender/Audio/QA |
| **Révision** | QAAgent → RevisionSpec → agent responsable → nouvel artifact |

La collaboration utilise les mécanismes Python/NOOA (`asyncio`, appels imbriqués, stratégies) — **pas de workflow engine propriétaire**.

---

## Human-in-the-Loop (TUI)

Dans le TUI, l'utilisateur peut :
- **APPROVE** → continue
- **REJECT** → RevisionSpec
- **MODIFY** → nouveau input

Points d'intervention configurables :
```
Brief → Story → Storyboard → [APPROVAL] → Previs → [APPROVAL] → Production → Preview → [APPROVAL] → Final
```

---

## Factory — Code Réel

```python
# DeepBl4nder/agents/factory.py
def build_agents() -> tuple[...]:
    llm = build_llm()
    return (
        StoryAgent(llm=llm),
        StoryboardAgent(llm=llm),
        DirectorAgent(llm=llm),
        BlenderAgent(llm=llm),
        QAAgent(llm=llm),
        AudioAgent(llm=llm),
        LocalizationAgent(llm=llm),
        CompositingAgent(llm=llm),
        CharacterDesignerAgent(llm=llm),
        AnimatorAgent(llm=llm),
        EnvironmentArtistAgent(llm=llm),
        MusicComposerAgent(llm=llm),
        SoundDesignerAgent(llm=llm),
        ReviewAgent(llm=llm),
    )
```