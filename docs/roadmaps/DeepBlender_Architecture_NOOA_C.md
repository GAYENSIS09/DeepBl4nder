> **Statut :** feuille de route architecturale de départ  
> **Version :** 0.3 — NOOA capabilities + production lifecycles + transitions  
> **Principe directeur :** exploiter au maximum les capacités réellement présentes dans NVIDIA NeMo Labs OO-Agents et ne pas reconstruire dans DeepBlender ce que NOOA fournit déjà.

---

## 0. Source de vérité et méthode

Ce document croise deux sources :

1. **ADD DeepBlender** : vision, pipeline audiovisuel, objectifs, compétences, cas d'usage et métriques.
2. **NOOA actuel** : architecture et capacités exposées dans le dépôt NVIDIA-NeMo/labs-OO-Agents.

Le dépôt actuel expose notamment :

- `nooa` core ;
- agents Python orientés objet ;
- méthodes agentiques et méthodes déterministes ;
- typed I/O ;
- auto-retry ;
- objets vivants passés par référence ;
- Code-as-Action ;
- APIs de contexte et d'événements ;
- tracing des appels LLM, exécutions de code et méthodes ;
- stratégies ;
- context blocks ;
- progressive disclosure ;
- skills ;
- MCP ;
- sandbox ;
- CLI / trace viewer ;
- `nooa-memory` pour la mémoire long terme ;
- pipeline d'évaluation.

NOOA est actuellement présenté comme un projet de recherche dont l'API publique peut évoluer. DeepBlender doit donc encapsuler le **domaine de production**, pas figer inutilement les détails internes de NOOA.

---

# 1. Vision

DeepBlender est une plateforme de production audiovisuelle assistée par agents IA.

L'objectif est de transformer une intention comme :

> « Fais une scène de suspense dans une ruelle. »

en une chaîne de production traçable :

```text
Brief
 ↓
Narration
 ↓
Storyboard
 ↓
Prévis / Animatic
 ↓
Faisabilité
 ↓
Assets
 ↓
Lookdev
 ↓
Rigging
 ↓
Layout
 ↓
Animation / Camera / Lighting / Simulation
 ↓
Pre-render
 ↓
QA
 ↓
Revision
 ↓
Final Render
 ↓
Compositing
 ↓
Audio
 ↓
Sous-titres / Langues
 ↓
Final QA
 ↓
Export

NOOA constitue le runtime agentique.

DeepBlender constitue le monde métier de production.

2. Principes fondamentaux
P1 — Agent = objet Python
class BlenderAgent(Agent):
    scene: Scene

    async def build_scene(self, spec: SceneSpec) -> Scene:
        """Build the requested Blender scene."""
        ...

L'agent possède :

état ;
méthodes ;
contrats ;
capacités ;
contexte.
P2 — ... = raisonnement agentique
async def plan_shot(self, shot: ShotSpec) -> ShotPlan:
    """Plan the shot."""
    ...
P3 — corps Python = déterminisme
def frame_count(self, duration: float, fps: int) -> int:
    return round(duration * fps)
P4 — Python est le langage de composition

NOOA permet au modèle d'agir via du code Python. DeepBlender doit donc favoriser :

objets vivants
+
typed interfaces
+
Python

plutôt qu'une forêt de micro-tools.

P5 — NOOA avant toute abstraction propriétaire

Avant d'ajouter une abstraction :

NOOA sait-il déjà le faire ?
        │
       oui → utiliser NOOA
        │
       non
        ↓
Est-ce une responsabilité du domaine audiovisuel ?
        │
       oui → DeepBlender
        │
       non → ne pas ajouter
3. Architecture des responsabilités
┌─────────────────────────────────────────────────────────┐
│                     DEEPBLENDER                         │
│                                                         │
│  Production audiovisuelle + Blender + Artifacts + QA   │
│                                                         │
│       ┌───────────────────────────────────────┐         │
│       │                  NOOA                 │         │
│       │                                       │         │
│       │ Agent / Context / Memory / Events     │         │
│       │ State / Strategies / Code / Tracing   │         │
│       │ Skills / MCP / Sandbox / Evaluation   │         │
│       └───────────────────────────────────────┘         │
│                                                         │
│  Blender / Audio / Render Farm / Storage / FFmpeg      │
└─────────────────────────────────────────────────────────┘
4. Ce qui appartient à NOOA

DeepBlender doit exploiter les primitives NOOA existantes pour :

runtime agentique ;
agent object model ;
state porté par les objets ;
méthodes agentiques ;
typed contracts ;
typed I/O ;
auto-retry ;
live-object references ;
Code-as-Action ;
strategies ;
context APIs ;
context blocks ;
progressive disclosure ;
event APIs ;
tracing ;
skills ;
MCP ;
sandbox/intégration sandbox ;
mémoire long terme via nooa-memory ;
évaluation agentique via le pipeline fourni ;
CLI / trace viewer lorsque pertinent.

NOOA trace notamment les appels LLM, exécutions de code et invocations de méthodes avec leurs relations parent-enfant.

5. Ce qui appartient à DeepBlender

DeepBlender doit fournir :

Project ;
Sequence ;
Shot ;
Scene ;
Asset ;
Character ;
Camera ;
Animation ;
Material ;
Audio ;
Render ;
QAReport ;
Revision ;
Artifact ;
production state ;
production provenance ;
production dependency graph ;
Blender integration ;
Blender workers ;
render scheduling ;
asset lifecycle ;
audio pipeline ;
compositing ;
export ;
production budgets ;
production security policies ;
human approvals.
6. La distinction essentielle : Agent Run vs Production Run
Agent Run

Concerne NOOA :

Agent
 ↓
Context
 ↓
Memory
 ↓
Method
 ↓
LLM
 ↓
Code / Tool / Agent
 ↓
Validation
 ↓
Result
 ↓
Events / Trace
Production Run

Concerne DeepBlender :

Project
 ↓
Production Step
 ↓
Artifact
 ↓
Worker
 ↓
Render / Process
 ↓
QA
 ↓
Revision
 ↓
Artifact version

Les deux doivent être corrélés, pas fusionnés.

7. Identité de corrélation

Chaque opération importante doit pouvoir être reliée :

project_id
sequence_id
shot_id
production_run_id
step_id
agent_run_id
event_id
artifact_id
artifact_version
worker_id
model
skill_versions
cost
timestamps

Ainsi :

Render_42
 ↓
Artifact_91
 ↓
ProductionRun_12
 ↓
Shot_07
 ↓
AgentRun_83
 ↓
BlenderAgent.build_scene()
 ↓
Skill blender-python v4
 ↓
NOOA trace
8. Pipeline audiovisuel complet
Étape 1 — Intention & briefing

Entrée :

texte utilisateur

Sortie :

BriefSpec

Agent possible :

DirectorAgent

NOOA :

context ;
memory ;
typed output ;
trace.

DeepBlender :

BriefSpec ;
project state.
Étape 2 — Scénario / structure narrative

Sortie :

StorySpec
SceneNarrative
CharacterArc
DialogueSpec

Skills :

storytelling
dialogue
dramaturgy
Étape 3 — Storyboard

Sortie :

Storyboard
ShotPlan[]

Skills :

storyboard
cinematography
composition
Étape 4 — Prévis / Animatic

Entrées :

Storyboard
ShotPlan
AudioReference

Sorties :

Animatic
TimingSpec
CameraPreview

Responsabilités :

NOOA
→ décision / planification

DeepBlender
→ création / rendu de la prévis
Étape 5 — Faisabilité technique

L'agent doit pouvoir évaluer :

durée
complexité
assets nécessaires
simulation
GPU
temps de rendu
budget
risques

Sortie :

FeasibilityReport
Étape 6 — Assets

Pipeline :

AssetSpec
 ↓
Search / Generate / Import
 ↓
Validate
 ↓
Register
 ↓
Version

Types :

characters
props
environment
textures
HDRI
audio
Étape 7 — UV / Texturing / Shading

Sorties :

MaterialSpec
TextureSet
LookDev

Skills :

uv
texturing
shading
lookdev
Étape 8 — Rigging / Weight Painting

Sorties :

RigSpec
WeightReport
PoseLibrary
Étape 9 — Layout

Entrées :

ShotPlan
Assets
CameraPlan

Sortie :

LayoutScene
Étape 10 — Animation / Camera / Lighting / Simulation

Sous-domaines :

character animation
object animation
camera
lighting
particles
cloth
physics
fluid

Sorties :

AnimatedScene
CameraPass
LightingPass
SimulationCache
Étape 11 — Pre-render

Pipeline :

Scene
 ↓
Worker
 ↓
Render
 ↓
Preview Artifact
 ↓
Technical QA
Étape 12 — QA / Révisions
QAReport
 ↓
PASS ─────────→ Finalization
 │
FAIL
 ↓
RevisionSpec
 ↓
Affected Step
 ↓
Re-execution

La révision doit retourner à l'étape concernée, et non recommencer aveuglément toute la production.

Exemple :

Camera QA failure
    ↓
CameraAgent
    ↓
Layout / Camera
    ↓
Pre-render

ou :

Rig failure
    ↓
RiggingAgent
    ↓
Animation
    ↓
Pre-render
Étape 13 — Final Render

Choix :

local
worker pool
render farm

Le scheduler appartient à DeepBlender.

Étape 14 — Compositing

Pipeline :

Render Passes
 ↓
Compositing
 ↓
CompositeArtifact
Étape 15 — Audio

Sous-domaines :

sound design
music
voice
mixing

Pipeline :

Animatic / Video
 ↓
AudioPlan
 ↓
Audio generation / import
 ↓
Mix
 ↓
AudioMaster
Étape 16 — Langues
Dialogue
 ↓
Translation
 ↓
Voice / Dubbing
 ↓
Subtitles
 ↓
Language Package
Étape 17 — Final QA

Contrôles :

visual
technical
audio
continuity
language
codec
color
framerate
resolution
metadata
Étape 18 — Export

Sorties :

master
web
preview
subtitle packages
audio stems
project archive
9. Skills

Les skills sont des unités de connaissance / procédure.

Structure :

skills/
├── storytelling/
├── dialogue/
├── storyboard/
├── cinematography/
├── composition/
├── feasibility/
├── modeling/
├── assets/
├── uv/
├── texturing/
├── shading/
├── rigging/
├── animation/
├── camera/
├── lighting/
├── simulation/
├── rendering/
├── compositing/
├── sound-design/
├── music/
├── voice/
├── translation/
├── subtitles/
├── continuity/
└── qa/

Chaque skill peut contenir :

SKILL.md
references/
examples/
scripts/
templates/

NOOA doit être utilisé pour le mécanisme de skills lorsque ses primitives le permettent.

DeepBlender possède le contenu métier des skills.

10. Progressive disclosure

Tous les skills ne doivent pas être injectés dans chaque contexte.

Principe :

Agent
 ↓
skill discovery
 ↓
skill description
 ↓
documentation pertinente
 ↓
reference/example
 ↓
action

Exemple :

CameraAgent
 ↓
cinematography skill
 ↓
lens/composition reference
 ↓
shot-specific instructions

Cela réduit le contexte inutile.

11. Tools

Un tool représente une primitive d'action importante.

Exemples :

inspect_scene
load_asset
save_blend
render
inspect_render
create_audio
compose
export

Ne pas créer :

move_object
rotate_object
scale_object
set_location
set_rotation
...

si le même résultat peut être obtenu naturellement via Python/Code-as-Action.

12. Plugins / intégrations externes
plugins/
├── blender/
├── render-farm/
├── ffmpeg/
├── audio/
├── tts/
├── storage/
├── asset-library/
└── subtitle/

Un plugin est une frontière d'intégration.

Il ne devient pas un deuxième runtime agentique.

13. Blender Worker
NOOA Agent
 ↓
DeepBlender capability
 ↓
Blender plugin
 ↓
Worker Manager
 ↓
Blender Worker
 ↓
Blender process

Le worker possède :

worker_id
GPU
scene
process
environment
timeout
status
artifacts
logs

Objectif initial :

3 workers parallèles
1 worker / scène
GPU
ajout dynamique d'un worker
sans redémarrage
14. Code généré

Pipeline obligatoire :

Agent
 ↓
Python generated
 ↓
NOOA validation
 ↓
DeepBlender policy
 ↓
Sandbox
 ↓
Worker
 ↓
Blender

NOOA effectue des validations de code, mais sa documentation précise que les contrôles in-process ne constituent pas une frontière de confinement suffisante.

La vraie frontière doit être :

OS sandbox
container
VM
NVIDIA OpenShell

selon l'environnement retenu.

15. Context

Le contexte n'est pas une base de données DeepBlender parallèle.

NOOA gère :

context
context blocks
dynamic prompts
summarization
model-facing context APIs

DeepBlender fournit :

Project state
Shot state
Scene state
relevant artifacts
production constraints
16. Memory

Deux niveaux :

NOOA Memory
    ↓
mémoire long terme de l'agent

DeepBlender Production State
    ↓
vérité persistante du projet

Exemple :

Memory
→ « Le réalisateur préfère des focales longues pour ce projet. »

Production State
→ « Shot 07 utilise actuellement une caméra 85mm, version 3. »

Ne pas remplacer nooa-memory par un DeepBlenderMemoryManager sans nécessité.

17. Events et tracing

NOOA fournit le tracing des :

LLM calls
code execution
method invocation
orchestration
helper calls

avec relations parent/enfant.

DeepBlender ajoute seulement les événements de production :

ProjectCreated
ShotCreated
ArtifactCreated
RenderStarted
RenderCompleted
QACompleted
RevisionRequested
HumanApproval
ExportCompleted

Architecture :

NOOA trace
     │
     │ correlation IDs
     ▼
DeepBlender production trace
18. Observabilité

Vue globale :

                    OBSERVABILITY
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
          NOOA                        DB
             │                         │
     agent / LLM / code          production
     context / methods           workers / renders
     events / strategies         artifacts / costs
             │                         │
             └────────────┬────────────┘
                          ▼
                   Production Run

Métriques :

latency
tokens
LLM cost
render cost
worker time
GPU utilization
retries
failures
QA score
artifact count
budget
19. Budget et coûts

Chaque ProductionRun doit suivre :

LLM cost
render cost
storage cost
external API cost
total cost
budget
remaining budget

Exemple :

Budget: 1.00 €
       ↓
LLM       0.18 €
Render    0.46 €
Audio     0.08 €
Storage   0.02 €
          ------
Total     0.74 €

Le système doit pouvoir interrompre ou demander une validation lorsqu'une politique de budget l'exige.

20. Production state

DeepBlender doit conserver la vérité du projet :

Project
 ├── Sequences
 │    └── Shots
 │         ├── Specs
 │         ├── Assets
 │         ├── Scene versions
 │         ├── Render versions
 │         ├── QA reports
 │         └── Revisions
 └── Global constraints

NOOA state et production state sont corrélés mais ne sont pas la même chose.

21. Artifact lifecycle
SPEC
 ↓
GENERATED
 ↓
VALIDATED
 ↓
EXECUTED
 ↓
CREATED
 ↓
INSPECTED
 ↓
QA
 ├── REJECTED
 │      ↓
 │   REVISION
 │      ↓
 │   NEW VERSION
 │
 └── APPROVED
        ↓
     PUBLISHED

Artifact :

id
type
version
hash
parents
creator
agent_run
production_run
skill_versions
model
timestamps
cost
status
22. Provenance

Question :

Pourquoi cet artifact existe-t-il ?

Réponse :

Artifact
 ↓
Production step
 ↓
Shot
 ↓
Agent Run
 ↓
NOOA trace
 ↓
Context
 ↓
Memory
 ↓
Skill
 ↓
Code / Tool
 ↓
Worker
 ↓
Input artifacts

La provenance permet de reproduire ou expliquer une production.

23. Graphs

Trois graphes sont distingués.

Dependency graph
Asset
 ↓
Scene
 ↓
Shot
 ↓
Render
Provenance graph
Brief
 ↓
Spec
 ↓
AgentRun
 ↓
Code
 ↓
Blend
 ↓
Render
Knowledge graph

Optionnel :

Character
 ├── appears_in → Shot
 ├── interacts_with → Character
 └── uses → Asset

Un graphe n'est pas imposé comme mécanisme d'exécution de tous les agents.

24. Collaboration multi-agents

La collaboration doit utiliser les mécanismes Python/NOOA avant d'introduire un workflow engine propriétaire.

Séquentielle
plan = await director.plan(brief)
scene = await blender.build(plan)
report = await qa.check(scene)
Parallèle
camera, lighting, animation = await asyncio.gather(
    cinematography.plan(shot),
    lighting.plan(shot),
    animation.plan(shot),
)
Hiérarchique
DirectorAgent
 ├── StoryAgent
 ├── CinematographyAgent
 ├── BlenderAgent
 ├── AudioAgent
 └── QAAgent
Révision
QAAgent
 ↓
RevisionSpec
 ↓
responsible agent
 ↓
new artifact
25. Transition Agent → Agent

Chaque collaboration doit conserver :

caller
callee
input type
output type
context
relevant memory
shared/live objects
trace parent
errors

Exemple :

DirectorAgent
      │
      │ ShotSpec
      ▼
CameraAgent
      │
      │ CameraPlan
      ▼
BlenderAgent
26. Transition Agent → Skill
Agent
 ↓
discover skill
 ↓
load relevant documentation
 ↓
reference/example
 ↓
apply skill
 ↓
result

Le skill enrichit le contexte ; il n'est pas un agent indépendant.

27. Transition Agent → Tool / Plugin
Agent
 ↓
typed call
 ↓
policy / permissions
 ↓
tool
 ↓
plugin
 ↓
external system
 ↓
typed result
 ↓
event / trace
 ↓
agent
28. Transition Agent → CodeAct
Agent
 ↓
reasoning
 ↓
generated Python
 ↓
NOOA code validation
 ↓
DeepBlender policy
 ↓
sandbox
 ↓
execution
 ↓
stdout / stderr / result
 ↓
event
 ↓
agent state

Une erreur doit devenir une information exploitable par la boucle de réparation.

29. Transition Worker → Artifact
Worker
 ↓
execution
 ↓
output
 ↓
artifact registration
 ↓
hash
 ↓
version
 ↓
provenance
 ↓
production state
30. Transition Artifact → QA
Artifact
 ↓
QA input
 ↓
technical checks
 ↓
visual checks
 ↓
semantic checks
 ↓
continuity checks
 ↓
QAReport
31. Transition QA → Revision
QAReport
 ↓
FAIL
 ↓
Issue classification
 ↓
affected production step
 ↓
RevisionSpec
 ↓
responsible agent
 ↓
new execution

Exemple :

Camera issue
 → CameraAgent
 → Layout
 → Pre-render

et non :

Camera issue
 → recommencer toute la production
32. Transition Human → Production
Artifact / Preview
 ↓
Human review
 ↓
APPROVE
    → continue
REJECT
    → RevisionSpec
MODIFY
    → new production input

L'humain intervient aux endroits où son jugement est important.

33. Lifecycle d'un Agent Run
CREATED
 ↓
CONTEXT BUILT
 ↓
MEMORY RECALLED
 ↓
METHOD STARTED
 ↓
LLM / CODE / TOOL
 ↓
STATE UPDATED
 ↓
EVENTS / TRACE
 ↓
OUTPUT VALIDATED
 ↓
COMPLETED

Erreur :

EXECUTION
 ↓
ERROR
 ↓
EVENT
 ↓
CONTEXT UPDATE
 ↓
RETRY / REPAIR / ESCALATE
34. Lifecycle d'un Production Run
CREATED
 ↓
PLANNED
 ↓
RUNNING
 ↓
ARTIFACTS CREATED
 ↓
QA
 ├── PASS → COMPLETED
 │
 ├── FAIL → REVISION
 │             ↓
 │          RUNNING
 │
 └── BLOCKED → HUMAN
35. Reprise après crash

La fiabilité est une exigence de l'ADD :

une production interrompue doit pouvoir reprendre sans perte.

Architecture :

ProductionRun
 ↓
persistent events
 ↓
checkpoint / state
 ↓
crash
 ↓
restart
 ↓
recover unconsumed work
 ↓
replay / resume

Important :

NOOA fournit une partie des primitives de runtime/event sourcing ;
DeepBlender doit garantir la persistance et la reprise de l'état de production ;
les artifacts déjà validés ne doivent pas être recréés inutilement.

La stratégie exacte de replay doit être implémentée après étude détaillée des APIs NOOA réellement disponibles.

36. Évaluation

Le projet doit utiliser le pipeline d'évaluation fourni par NOOA pour les capacités agentiques lorsque cela est pertinent.

Golden set DeepBlender :

scene_001
scene_002
...
scene_N

Mesures :

task success
QA first-pass rate
revision count
latency
cost
tool/code failures
37. Critères de succès ADD
Latence
Brief → first preview < 5 min
10-second sequence < 10 min
Coût
Demo scene < 1 €
Qualité
first-pass QA ≥ 60 %
Évolutivité
3 workers parallèles
1 worker / scène
ajout sans redémarrage
Fiabilité
crash
 ↓
resume
 ↓
aucune perte
Observabilité
state + cost visible
budget alert < 30 s
Sécurité
generated code
 ↓
validation
 ↓
policy
 ↓
sandbox
38. Human-in-the-loop

Points possibles :

Brief
 ↓
Story
 ↓
Storyboard
 ↓
[APPROVAL]
 ↓
Previs
 ↓
[APPROVAL]
 ↓
Production
 ↓
Preview
 ↓
[APPROVAL]
 ↓
Final

La présence humaine est configurable selon le type de projet.

39. Architecture des dossiers
deepblender/
│
├── pyproject.toml
├── README.md
│
├── docs/
│   ├── architecture/
│   │   ├── nooa.md
│   │   ├── capabilities.md
│   │   ├── transitions.md
│   │   ├── lifecycles.md
│   │   ├── agents.md
│   │   ├── skills.md
│   │   ├── tools.md
│   │   ├── plugins.md
│   │   ├── context-memory.md
│   │   ├── observability.md
│   │   ├── workers.md
│   │   ├── artifacts.md
│   │   ├── provenance.md
│   │   ├── graphs.md
│   │   └── security.md
│   │
│   └── production/
│       ├── pipeline.md
│       ├── storyboard.md
│       ├── previs.md
│       ├── assets.md
│       ├── animation.md
│       ├── rendering.md
│       ├── compositing.md
│       ├── audio.md
│       ├── localization.md
│       └── qa.md
│
├── src/
│   └── deepblender/
│       │
│       ├── agents/
│       │   ├── director.py
│       │   ├── story.py
│       │   ├── storyboard.py
│       │   ├── previs.py
│       │   ├── feasibility.py
│       │   ├── assets.py
│       │   ├── modeling.py
│       │   ├── lookdev.py
│       │   ├── rigging.py
│       │   ├── layout.py
│       │   ├── animation.py
│       │   ├── cinematography.py
│       │   ├── lighting.py
│       │   ├── simulation.py
│       │   ├── rendering.py
│       │   ├── compositing.py
│       │   ├── audio.py
│       │   ├── localization.py
│       │   └── qa.py
│       │
│       ├── domain/
│       │   ├── project.py
│       │   ├── sequence.py
│       │   ├── shot.py
│       │   ├── scene.py
│       │   ├── asset.py
│       │   ├── character.py
│       │   ├── camera.py
│       │   ├── animation.py
│       │   ├── audio.py
│       │   ├── render.py
│       │   ├── artifact.py
│       │   ├── revision.py
│       │   └── qa.py
│       │
│       ├── blender/
│       │   ├── plugin.py
│       │   ├── bridge.py
│       │   ├── worker.py
│       │   └── scheduler.py
│       │
│       ├── codegen/
│       │   ├── blender_python.py
│       │   ├── validator.py
│       │   └── policy.py
│       │
│       ├── production/
│       │   ├── runs.py
│       │   ├── state.py
│       │   ├── recovery.py
│       │   ├── scheduler.py
│       │   └── budget.py
│       │
│       ├── artifacts/
│       │   ├── registry.py
│       │   ├── versioning.py
│       │   └── provenance.py
│       │
│       ├── graphs/
│       │   ├── dependency.py
│       │   ├── provenance.py
│       │   └── knowledge.py
│       │
│       └── integrations/
│           ├── ffmpeg.py
│           ├── audio.py
│           ├── tts.py
│           ├── storage.py
│           ├── renderfarm.py
│           └── subtitles.py
│
├── skills/
│   ├── storytelling/
│   ├── dialogue/
│   ├── storyboard/
│   ├── cinematography/
│   ├── composition/
│   ├── feasibility/
│   ├── modeling/
│   ├── assets/
│   ├── uv/
│   ├── texturing/
│   ├── shading/
│   ├── rigging/
│   ├── animation/
│   ├── camera/
│   ├── lighting/
│   ├── simulation/
│   ├── rendering/
│   ├── compositing/
│   ├── sound-design/
│   ├── music/
│   ├── voice/
│   ├── translation/
│   ├── subtitles/
│   ├── continuity/
│   └── qa/
│
├── plugins/
│   ├── blender/
│   ├── render-farm/
│   ├── ffmpeg/
│   ├── audio/
│   ├── tts/
│   ├── storage/
│   ├── assets/
│   └── subtitles/
│
├── projects/
│   └── examples/
│
└── tests/
    ├── agents/
    ├── skills/
    ├── domain/
    ├── transitions/
    ├── lifecycles/
    ├── blender/
    ├── workers/
    ├── recovery/
    └── integration/
40. Ce qui ne doit PAS être créé

Sauf nécessité démontrée :

❌ GenericAgentRuntime
❌ GenericAgentLoop
❌ GenericContextManager
❌ GenericMemoryManager
❌ GenericEventBus
❌ GenericStateManager
❌ GenericLLMOrchestrator
❌ GenericWorkflowEngine
❌ GenericHandoffEngine
❌ GenericTracingSystem

Avant de créer l'un de ces composants :

1. vérifier NOOA
2. lire l'exemple correspondant
3. vérifier le code source
4. tester l'API
5. seulement ensuite décider
41. Ce qui doit rester DeepBlender
✓ Production domain
✓ Blender domain
✓ Production state
✓ Artifact registry
✓ Production provenance
✓ Production graphs
✓ Render scheduling
✓ Blender workers
✓ Asset lifecycle
✓ Audio pipeline
✓ Compositing
✓ Localization
✓ Production budgets
✓ Human approvals
✓ Production QA
✓ Production security policies
42. MVP

Le MVP ne cherche pas à couvrir immédiatement les 18 étapes.

Il démontre la boucle fondamentale :

Brief
 ↓
DirectorAgent
 ↓
SceneSpec
 ↓
ShotSpec
 ↓
BlenderAgent
 ↓
Skill
 ↓
CodeAct
 ↓
Sandbox
 ↓
Blender Worker
 ↓
Preview Render
 ↓
QAAgent
 ↓
PASS / Revision
 ↓
Artifact

Cible :

5–10 secondes
1 scène
3–5 agents
3 workers maximum
43. Première verticale recommandée

Pour éviter de construire tout le studio avant de prouver l'architecture :

Brief
 ↓
Story
 ↓
Storyboard
 ↓
Shot
 ↓
Blender scene
 ↓
Camera
 ↓
Lighting
 ↓
Animation simple
 ↓
Render
 ↓
QA
 ↓
Revision

Puis seulement :

Assets avancés
Rigging
Simulation
Audio
Compositing
Localization
Render farm
44. Roadmap
Phase 0 — NOOA audit

Étudier directement :

examples/
src/nooa/
packages/nooa-memory/
packages/nooa-cli/
util/eval_pipeline/
skills/

Identifier pour chaque fonctionnalité :

API
example
source
test
limitation

Livrable :

NOOA_CAPABILITY_MATRIX.md
Phase 1 — NOOA proof of concept

Reproduire les exemples NOOA pertinents :

agent
typed output
tools
strategies
context blocks
progressive disclosure
tracing
skills
MCP
sandbox
memory
Phase 2 — Blender vertical slice
Brief
 ↓
SceneSpec
 ↓
Blender
 ↓
Render
 ↓
QA
Phase 3 — Production state / artifacts

Ajouter :

Project
Shot
Artifact
Revision
Provenance
Phase 4 — Recovery / observability / budget

Ajouter :

ProductionRun
correlation
recovery
cost
worker metrics
Phase 5 — Skills complets

Ajouter progressivement :

storytelling
storyboard
cinematography
assets
modeling
lookdev
rigging
animation
lighting
simulation
Phase 6 — Audio / compositing / localization

Ajouter :

sound
music
voice
mix
compositing
translation
subtitles
Phase 7 — Industrialisation
worker pool
render farm
GPU scheduling
storage
caching
parallelism
45. Architecture finale
                                USER
                                  │
                                  ▼
                         DEEPBLENDER API
                                  │
                                  ▼
                    ┌────────────────────────┐
                    │          NOOA          │
                    │                        │
                    │ Agent Objects          │
                    │ State                  │
                    │ Context                │
                    │ Memory                 │
                    │ Events                 │
                    │ Strategies             │
                    │ Code-as-Action         │
                    │ Validation             │
                    │ Skills                 │
                    │ MCP                    │
                    │ Tracing                │
                    │ Sandbox                │
                    │ Evaluation             │
                    └───────────┬────────────┘
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
             Skills          Tools           Agents
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                       PRODUCTION DOMAIN
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
   Blender                  Audio                    Assets
       │                        │                        │
     Worker                   Tools                  Library
       │                        │
       └──────────────┬─────────┘
                      ▼
                   ARTIFACTS
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
         Provenance  QA      Graphs
             │        │
             └────┬───┘
                  ▼
          PRODUCTION STATE
                  │
                  ▼
              REVISION
                  │
                  └──────────────→ NOOA
46. Règle d'or finale

DeepBlender ne doit pas devenir :

« un framework d'agents qui utilise NOOA ».

Il doit devenir :

« une plateforme de production audiovisuelle dont le runtime agentique est NOOA ».

Donc :

NOOA
=
agent runtime

DeepBlender
=
production runtime / domain

Skills
=
knowledge

Tools
=
actions

Plugins
=
external boundaries

Workers
=
isolated execution

Artifacts
=
production outputs

Graphs
=
production relationships

QA
=
quality control

Human
=
creative authority
47. Critère architectural de réussite

L'architecture est réussie si :

un agent DeepBlender reste un objet Python NOOA ;
le contexte, la mémoire, les événements et le tracing utilisent les mécanismes NOOA existants ;
les skills peuvent évoluer sans modifier le runtime ;
les tools/plugins peuvent évoluer sans modifier les agents ;
les agents manipulent des objets métier typés ;
le code Blender peut être généré et exécuté de manière contrôlée ;
chaque artifact possède une provenance ;
chaque production peut être reprise ;
les erreurs retournent vers l'étape pertinente ;
l'humain peut reprendre le contrôle ;
les coûts et la latence sont mesurables ;
l'ajout d'un worker ne nécessite pas de refonte du runtime ;
le système peut passer progressivement de 5 secondes à des productions plus complexes ;
aucune abstraction DeepBlender ne duplique inutilement une capacité NOOA.
48. Décision architecturale

NOOA est la fondation agentique.

DeepBlender ne doit pas concurrencer cette fondation.

Le projet doit exploiter en profondeur les capacités NOOA disponibles aujourd'hui, tout en isolant dans DeepBlender uniquement ce qui appartient réellement à la production audiovisuelle.

La priorité d'implémentation n'est donc pas :

écrire beaucoup de code

mais :

étudier NOOA
→ mapper ses capacités
→ les intégrer
→ construire uniquement les briques métier manquantes
→ valider avec une verticale Blender
→ étendre progressivement à toute la chaîne de production.

'''

path = Path("/mnt/data/DeepBlender_Architecture_NOOA_First_v0.3.md")
path.write_text(md, encoding="utf-8")
print(path)