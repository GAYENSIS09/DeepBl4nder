# DeepBlender — Architecture NOOA-First

> **Statut :** feuille de route architecturale de départ  
> **Version :** 0.2 — NOOA-first  
> **Principe :** exploiter au maximum les capacités natives de NVIDIA NeMo Labs OO-Agents et ne pas réimplémenter ce que NOOA fournit déjà.

---

## 1. Vision

DeepBlender est une plateforme de production audiovisuelle assistée par agents IA, construite **au-dessus de NVIDIA NeMo Labs OO-Agents (NOOA)**.

L'objectif est de transformer une intention créative en production Blender exploitable, itérative et traçable :

```text
Brief
  ↓
Compréhension / planification
  ↓
SceneSpec / ShotSpec
  ↓
Storyboard / Prévis
  ↓
Génération d'actions Python
  ↓
Blender
  ↓
Render
  ↓
QA
  ├── PASS → Artifact final
  └── FAIL → Revision
                ↓
             nouvelle itération
```

Le MVP vise d'abord des séquences de **5 à 10 secondes**.

La philosophie fondamentale est :

> **NOOA fournit le runtime agentique. DeepBlender fournit le domaine de production audiovisuelle.**

---

# 2. Principe NOOA-first

DeepBlender ne doit pas devenir un deuxième framework d'agents.

Nous exploitons directement les primitives NOOA lorsqu'elles sont pertinentes :

```text
NOOA
├── Agent = Python object
├── Methods = capabilities
├── Fields = state
├── Docstrings = model-facing instructions
├── Type annotations = contracts
├── ... method body = agentic completion
├── normal Python body = deterministic code
├── typed input/output
├── live Python objects / references
├── context management
├── state management
├── state rendering
├── event APIs
├── memory APIs
├── validated LLM loops
├── strategies
├── Code-as-Action / Python execution
├── programmable loops
├── asyncio
├── nested agentic calls
└── model-facing harness APIs
```

**Ne pas recréer ces abstractions dans DeepBlender sans nécessité démontrée.**

---

# 3. Ce que DeepBlender apporte

DeepBlender ajoute uniquement les concepts propres à la production :

```text
DeepBlender
├── Production domain
├── Blender domain objects
├── Skills métier
├── Blender tools / integrations
├── External plugins
├── Blender workers
├── Generated code policies
├── Assets
├── Artifacts
├── Provenance
├── Production dependency graphs
├── QA métier
├── Render management
├── Production budgets / policies
└── Human approval points
```

---

# 4. Matrice de responsabilité

| Capacité | NOOA | DeepBlender |
|---|---:|---:|
| Agent runtime | **Natif** | Utilise |
| Agent = objet Python | **Natif** | Utilise |
| État de l'agent | **Natif** | Ajoute l'état métier |
| Context management | **Natif** | Fournit le contenu métier |
| Context rendering | **Natif** | Fournit éventuellement des renderers métier |
| Event APIs | **Natif** | Émet des événements métier lorsque nécessaire |
| Event history | **Natif** | Utilise |
| Long-term memory | **Natif** | Stocke les connaissances métier comme objets métier lorsque nécessaire |
| LLM loop | **Natif** | Configure / utilise |
| Validation des sorties | **Natif** | Définit les types/contracts métier |
| Typed I/O | **Natif** | Définit les modèles métier |
| Live object references | **Natif** | Utilise pour Scene, Shot, Asset, etc. |
| Code-as-Action | **Natif** | Utilise massivement pour Blender |
| Python orchestration | **Natif / modèle NOOA** | Utilise |
| `asyncio` | **Natif / modèle Python** | Utilise |
| Nested agentic calls | **Natif** | Utilise |
| Strategies | **Natif** | Configure par capacité |
| Model selection par méthode | **Natif selon stratégie/configuration** | Configure |
| Scoped context | **Natif** | Utilise |
| Memory operations | **Natif** | Exploite |
| Blender API | — | **DeepBlender** |
| Blender integration | — | **DeepBlender** |
| Blender worker isolation | — | **DeepBlender** |
| Render scheduling | — | **DeepBlender** |
| Asset management | — | **DeepBlender** |
| Artifact registry | — | **DeepBlender** |
| Provenance de production | — | **DeepBlender** |
| Production dependency graph | — | **DeepBlender** |
| Blender QA | — | **DeepBlender** |
| Code security policy | — | **DeepBlender** |
| Render farm | — | **DeepBlender / plugin** |

> Cette matrice distingue les primitives décrites par NOOA des responsabilités spécifiques au domaine Blender. Elle ne prétend pas que NOOA fournit un système complet de gestion de production.

---

# 5. Le modèle objet NOOA

Le code DeepBlender doit suivre autant que possible le modèle objet de NOOA.

Conceptuellement :

```python
class BlenderAgent:
    scene: Scene
    project: Project

    def inspect_scene(self) -> SceneInfo:
        ...

    def plan_shot(self, shot: ShotSpec) -> ShotPlan:
        ...

    def build_scene(self, spec: SceneSpec) -> SceneResult:
        ...

    def validate(self, scene: Scene) -> QAReport:
        ...
```

Les méthodes `...` deviennent des capacités agentiques.

À l'inverse :

```python
class ProductionUtils:

    def frame_count(self, duration: float, fps: int) -> int:
        return round(duration * fps)
```

reste du Python déterministe.

Cette frontière est essentielle :

```text
...             → décision / raisonnement agentique
corps Python    → logique déterministe
```

---

# 6. Types et objets vivants

Une priorité de DeepBlender est d'utiliser les **objets Python typés comme interface de travail**.

Au lieu de transformer systématiquement tout en JSON :

```text
Scene
Shot
Asset
Camera
Character
Material
Render
QAReport
```

peuvent devenir des objets manipulables par les agents NOOA.

Conceptuellement :

```python
scene = agent.scene
shot = project.shots["shot_01"]

plan = await agent.plan_shot(shot)

scene.camera = plan.camera
```

L'intérêt est de conserver :

- références ;
- état ;
- types ;
- relations ;
- méthodes ;
- contexte.

Les objets métier ne doivent donc pas être conçus uniquement comme des DTO sérialisés.

---

# 7. Context management

Le contexte agentique est délégué à NOOA.

DeepBlender fournit les informations métier que NOOA doit rendre disponibles :

```text
NOOA Context
     │
     ├── current agent state
     ├── relevant memory
     ├── method context
     ├── event context
     └── DeepBlender objects
             │
             ├── Project
             ├── Scene
             ├── Shot
             ├── Assets
             └── QA state
```

DeepBlender ne crée pas de `ContextManager` parallèle.

---

# 8. Memory

NOOA fournit une couche de mémoire longue durée.

Elle peut servir à conserver ce que l'agent doit apprendre ou rappeler :

```text
BlenderAgent Memory
├── conventions de projet
├── décisions précédentes
├── erreurs fréquentes
├── stratégies efficaces
├── préférences de production
└── connaissances utiles
```

Conceptuellement, NOOA expose des opérations de mémoire permettant notamment de :

```text
remember
recall
search
update
forget
associate
deref
```

La distinction importante est :

```text
NOOA Memory
    =
mémoire cognitive / opérationnelle de l'agent

DeepBlender Project Data
    =
vérité persistante de la production
```

---

# 9. Events et observabilité

Les événements agentiques et l'historique d'événements doivent être exploités via NOOA lorsqu'ils couvrent le besoin.

DeepBlender ne doit pas créer un deuxième event bus pour les événements agentiques.

Exemple :

```text
NOOA Events
├── agent started
├── method called
├── capability invoked
├── model response
├── validation
├── exception
├── memory operation
└── agent completed
```

DeepBlender peut ajouter des événements métier :

```text
SceneCreated
RenderStarted
RenderCompleted
QAFailed
ArtifactCreated
RevisionRequested
```

mais ils doivent rester des **événements du domaine**, et non une réimplémentation du runtime NOOA.

### Observabilité

Nous séparons :

```text
NOOA observability
    ↓
agent / model / loop / context / events

DeepBlender observability
    ↓
production / Blender / workers / renders / artifacts / costs
```

L'objectif est de relier les deux, pas de les remplacer.

---

# 10. Code-as-Action

C'est une capacité centrale pour DeepBlender.

Le modèle doit pouvoir utiliser Python comme langage d'action.

Au lieu de multiplier les micro-tools :

```text
create_cube
move_object
rotate_object
set_material
...
```

le modèle peut manipuler les objets et appeler les capacités disponibles en Python.

Conceptuellement :

```python
scene = blender.inspect_scene()

for obj in scene.objects:
    ...

await blender.render(...)
```

Cela permet :

- boucles ;
- conditions ;
- transformations ;
- composition d'actions ;
- accès aux objets vivants ;
- appels imbriqués ;
- concurrence avec `asyncio`.

Pour Blender, cette capacité est particulièrement adaptée à la génération de scripts `bpy`.

---

# 11. Génération de code Blender

Le code généré reste soumis aux politiques DeepBlender.

Pipeline :

```text
NOOA / Agent
      ↓
Code-as-Action / Python
      ↓
DeepBlender Code Policy
      ↓
Validation
      ↓
Blender Worker
      ↓
Blender
```

Le principe est :

> **NOOA donne au modèle la capacité d'agir en Python ; DeepBlender définit le périmètre dans lequel cette action est autorisée.**

---

# 12. Strategies

Les stratégies NOOA doivent être exploitées plutôt que remplacées.

Une capacité peut nécessiter une stratégie adaptée :

```text
Simple typed task
    ↓
PredictStrategy

Complex Blender manipulation
    ↓
CodeActStrategy
```

Les paramètres tels que :

- modèle ;
- contexte ;
- validation ;
- troncature ;
- comportement de boucle ;

doivent être configurés au niveau NOOA lorsque ses mécanismes le permettent.

DeepBlender ne doit pas construire un `LLMOrchestrator` propriétaire pour reproduire cela.

---

# 13. Async et collaboration entre agents

La concurrence doit utiliser les mécanismes Python/NOOA, notamment `asyncio`.

Exemple conceptuel :

```python
results = await asyncio.gather(
    cinematography_agent.plan(shot),
    lighting_agent.plan(shot),
    animation_agent.plan(shot),
)
```

Ou :

```python
plan = await director.plan_shot(shot)

camera = await cinematography.plan(plan)
lighting = await lighting.plan(plan)
animation = await animation.plan(plan)
```

Le système n'a pas besoin d'un graph de handoff propriétaire pour chaque collaboration.

---

# 14. Skills

Les skills sont des paquets de connaissance spécialisés.

Architecture :

```text
skills/
├── blender-python/
│   ├── SKILL.md
│   ├── references/
│   ├── examples/
│   └── scripts/
│
├── cinematography/
│   ├── SKILL.md
│   ├── references/
│   └── examples/
│
├── lighting/
│   └── SKILL.md
├── animation/
│   └── SKILL.md
├── modeling/
│   └── SKILL.md
├── rigging/
│   └── SKILL.md
├── materials/
│   └── SKILL.md
├── storytelling/
│   └── SKILL.md
├── storyboard/
│   └── SKILL.md
└── qa/
    └── SKILL.md
```

Un skill contient :

```text
instructions
connaissances
références
exemples
scripts
conventions
```

Le skill n'est pas un agent.

Un agent peut exploiter plusieurs skills :

```text
BlenderAgent
├── blender-python
├── cinematography
├── lighting
└── animation
```

---

# 15. Tools

Les tools sont des capacités d'action du domaine.

Exemples :

```text
inspect_scene
save_scene
render
load_asset
inspect_render
```

Ils doivent rester aussi petits que possible.

Mais il faut éviter de transformer chaque opération Blender en micro-tool si **Code-as-Action** permet une composition plus naturelle.

Principe :

```text
Tool
    = capacité externe / primitive importante

Python / CodeAct
    = composition de capacités
```

---

# 16. Plugins

Les plugins sont les frontières d'intégration avec les systèmes externes.

Exemples :

```text
Blender
FFmpeg
Audio
TTS
Asset Library
Storage
Render Farm
Git
```

Architecture :

```text
Agent
  ↓
Tool / Python
  ↓
Plugin
  ↓
External system
```

Le plugin ne doit pas devenir un deuxième runtime agentique.

---

# 17. Blender Worker

Le processus Blender doit être isolé.

```text
NOOA Agent
    ↓
DeepBlender capability
    ↓
Blender Plugin
    ↓
Worker Manager
    ↓
Blender Worker
    ↓
Blender process
```

Responsabilités DeepBlender :

- lancement ;
- timeout ;
- arrêt ;
- récupération d'erreur ;
- allocation GPU ;
- parallélisation ;
- récupération des artifacts.

Exemple :

```text
Worker 1 → Shot 001
Worker 2 → Shot 002
Worker 3 → Shot 003
```

---

# 18. Production domain

DeepBlender doit définir ses propres objets métier.

Exemples :

```text
Project
Scene
Sequence
Shot
Asset
Character
Camera
Material
Animation
Render
QAReport
Artifact
Revision
```

Ces objets peuvent ensuite être utilisés directement par les agents NOOA.

---

# 19. Artifacts

Un artifact est un résultat ou une unité persistante de production.

Exemples :

```text
SceneSpec
ShotSpec
Storyboard
Python script
.blend
Render
Audio
Video
QAReport
```

Chaque artifact doit pouvoir être relié à :

```text
id
version
parents
creator
agent run
skill versions
model
parameters
hash
status
timestamp
```

---

# 20. Provenance

La provenance est une responsabilité métier DeepBlender.

NOOA fournit le contexte et les événements agentiques nécessaires à l'observabilité de l'agent, mais DeepBlender doit reconstruire la provenance de production.

Question cible :

> « Pourquoi ce fichier `.png` existe-t-il et quelle suite de décisions l'a produit ? »

Réponse :

```text
Render
 ↓
Blend
 ↓
Python
 ↓
ShotSpec
 ↓
SceneSpec
 ↓
Agent run
 ↓
Skills
 ↓
NOOA context / events
```

---

# 21. Graphs

Il ne faut pas faire du graph un mécanisme obligatoire pour tout.

## Workflow

Peut être du Python normal :

```text
Brief
 ↓
SceneSpec
 ↓
Blender
 ↓
Render
 ↓
QA
 ↓
Revision
```

## Dependency graph

Responsabilité DeepBlender :

```text
Asset A
  ↓
Scene
  ↓
Shot
  ↓
Render
```

## Provenance graph

Responsabilité DeepBlender :

```text
Brief
 ↓
Spec
 ↓
Code
 ↓
Blend
 ↓
Render
```

## Knowledge graph

Optionnel, pour :

```text
Character
 ├── appears_in → Shot
 ├── wears → Costume
 └── interacts_with → Asset
```

Les graphes représentent les **relations métier**, pas le runtime NOOA.

---

# 22. QA

QA est une responsabilité DeepBlender.

```text
Technical QA
Visual QA
Continuity QA
Semantic QA
```

Le résultat est typé :

```python
class QAReport:
    passed: bool
    score: float
    issues: list[Issue]
    recommendations: list[str]
```

Puis :

```text
QA
 ├── PASS → Artifact approved
 └── FAIL → RevisionSpec
```

L'agent NOOA peut ensuite utiliser cette information pour décider de la correction.

---

# 23. Boucle agentique de production

La boucle cible devient :

```text
                 Brief
                   ↓
              DirectorAgent
                   ↓
                SceneSpec
                   ↓
              BlenderAgent
                   ↓
            NOOA CodeAct / Python
                   ↓
              Blender Worker
                   ↓
                 Render
                   ↓
                QAAgent
                /      \
             PASS      FAIL
              │          │
              ▼          ▼
          Artifact    RevisionSpec
                           │
                           ▼
                     BlenderAgent
```

La boucle de raisonnement est NOOA.

La boucle de production est DeepBlender.

Elles doivent rester connectées mais distinctes.

---

# 24. Mémoire + artifacts + événements

Ces trois notions ne doivent pas être confondues.

```text
                 NOOA
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
      Memory    Events    Context
        │         │         │
        └─────────┼─────────┘
                  │
                  ▼
             Agent state

              DeepBlender
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
    Artifacts  Production  Graphs
                  state
```

### Memory

Ce que l'agent peut apprendre/rappeler.

### Events

Ce qui s'est produit dans le runtime.

### Artifacts

Ce qui a été produit.

### Production state

La vérité actuelle du projet.

---

# 25. Architecture des dossiers

```text
deepblender/
│
├── pyproject.toml
├── README.md
│
├── docs/
│   ├── architecture/
│   │   ├── nooa.md
│   │   ├── agents.md
│   │   ├── skills.md
│   │   ├── tools.md
│   │   ├── plugins.md
│   │   ├── workers.md
│   │   ├── artifacts.md
│   │   ├── provenance.md
│   │   └── graphs.md
│   │
│   └── production/
│       ├── pipeline.md
│       ├── qa.md
│       └── rendering.md
│
├── src/
│   └── deepblender/
│       │
│       ├── agents/
│       │   ├── director.py
│       │   ├── blender.py
│       │   └── qa.py
│       │
│       ├── domain/
│       │   ├── project.py
│       │   ├── scene.py
│       │   ├── shot.py
│       │   ├── asset.py
│       │   ├── render.py
│       │   └── qa.py
│       │
│       ├── skills/
│       │   ├── registry.py
│       │   ├── loader.py
│       │   └── resolver.py
│       │
│       ├── blender/
│       │   ├── plugin.py
│       │   ├── worker.py
│       │   └── bridge.py
│       │
│       ├── codegen/
│       │   ├── blender_python.py
│       │   ├── validator.py
│       │   └── policy.py
│       │
│       ├── artifacts/
│       │   ├── registry.py
│       │   ├── versioning.py
│       │   └── provenance.py
│       │
│       ├── graphs/
│       │   ├── dependencies.py
│       │   ├── provenance.py
│       │   └── knowledge.py
│       │
│       ├── production/
│       │   ├── pipeline.py
│       │   ├── scheduler.py
│       │   └── policies.py
│       │
│       └── api/
│           └── server.py
│
├── skills/
│   ├── blender-python/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── examples/
│   │   └── scripts/
│   ├── cinematography/
│   ├── lighting/
│   ├── animation/
│   ├── modeling/
│   ├── rigging/
│   ├── materials/
│   ├── storytelling/
│   ├── storyboard/
│   └── qa/
│
├── plugins/
│   ├── blender/
│   ├── ffmpeg/
│   ├── audio/
│   └── assets/
│
├── projects/
│   └── examples/
│
└── tests/
    ├── agents/
    ├── domain/
    ├── blender/
    ├── skills/
    ├── workers/
    └── integration/
```

---

# 26. Ce qui ne doit PAS être créé

À éviter sauf besoin réel :

```text
❌ ContextManager
❌ MemoryManager
❌ AgentLoop
❌ GenericAgentRuntime
❌ GenericHandoffEngine
❌ GenericEventBus
❌ GenericStateManager
❌ GenericLLMOrchestrator
❌ GenericToolWorkflowEngine
```

Si un besoin semble correspondre à l'une de ces catégories :

1. vérifier d'abord les primitives NOOA ;
2. utiliser NOOA directement ;
3. n'ajouter une abstraction DeepBlender que si elle représente une responsabilité métier absente de NOOA.

---

# 27. Ce qui DOIT être DeepBlender

```text
✓ Blender integration
✓ Blender Worker
✓ GPU scheduling
✓ Blender-specific tools
✓ Production objects
✓ Asset management
✓ Render management
✓ Artifact registry
✓ Production provenance
✓ Production dependency graph
✓ Blender QA
✓ Code security policies
✓ Project persistence
✓ Render farm adapters
✓ External production integrations
```

---

# 28. Skills + Tools + Plugins

Ces trois concepts sont volontairement séparés :

```text
Skill
  =
ce que l'agent sait faire / sait comment faire

Tool
  =
action disponible

Plugin
  =
connexion à un système externe
```

Exemple :

```text
BlenderAgent

Skills:
  cinematography
  lighting
  blender-python

Tools:
  inspect_scene
  render
  save_scene

Plugin:
  Blender
```

---

# 29. Collaboration

La collaboration ne doit pas être imposée par un framework de graph.

Elle peut être :

### Séquentielle

```python
plan = await director.plan(brief)
scene = await blender.build(plan)
report = await qa.check(scene)
```

### Parallèle

```python
camera, lighting, animation = await asyncio.gather(
    cinematography.plan(shot),
    lighting.plan(shot),
    animation.plan(shot),
)
```

### Hiérarchique

```text
DirectorAgent
   │
   ├── BlenderAgent
   ├── QAAgent
   └── AssetAgent
```

### Agentique

Un agent peut décider d'appeler une autre capacité agentique lorsqu'il le faut.

Le choix dépend du problème, pas d'une infrastructure de workflow imposée.

---

# 30. Human-in-the-loop

L'humain intervient là où son jugement apporte une valeur élevée :

```text
Brief
 ↓
Plan
 ↓
[HUMAN APPROVAL]
 ↓
Production
 ↓
Preview
 ↓
[HUMAN APPROVAL]
 ↓
Final
```

---

# 31. Pipeline audiovisuel cible

```text
1. Intention & Briefing
2. Scénario
3. Storyboard
4. Prévis / Animatic
5. Faisabilité technique
6. Assets
7. UV / Texturing / Shading
8. Rigging
9. Layout
10. Animation / Caméra / Lumière
11. Render préliminaire
12. QA / Révisions
13. Render final
14. Compositing
15. Audio / Voix / Mixage
16. Sous-titres / Langues
17. QA final
18. Export
```

---

# 32. MVP

Le premier objectif :

> **À partir d'un brief, produire une séquence Blender de 5–10 secondes, la rendre, l'évaluer et effectuer au moins une itération de correction.**

Architecture minimale :

```text
NOOA
 │
 ├── DirectorAgent
 ├── BlenderAgent
 └── QAAgent
       │
       ▼
DeepBlender
 │
 ├── Blender plugin
 ├── Blender worker
 ├── Skills
 ├── Code policy
 └── Artifacts
```

Skills initiales :

```text
blender-python
cinematography
lighting
animation
qa
```

---

# 33. Exemple de première scène

Brief :

> « Une ruelle sombre sous la pluie, un personnage marche lentement vers une porte pendant cinq secondes. »

Le système doit pouvoir faire :

```text
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
Skills
 ↓
CodeAct / Python
 ↓
Blender Worker
 ↓
Render
 ↓
QAAgent
 ↓
Revision
 ↓
Render v2
```

Résultats attendus :

```text
SceneSpec
ShotSpec
generated Python
.blend
render
QA report
provenance
```

---

# 34. Feuille de route

## Phase 0 — Étude NOOA

Avant d'écrire des abstractions DeepBlender :

- étudier les exemples NOOA ;
- identifier les APIs réellement disponibles ;
- identifier les stratégies ;
- identifier les mécanismes de mémoire ;
- identifier context/events/state ;
- identifier CodeAct ;
- identifier les mécanismes de collaboration ;
- identifier les patterns `asyncio` ;
- reproduire les exemples NOOA pertinents.

**Objectif : ne rien réimplémenter par ignorance.**

## Phase 1 — Agent NOOA minimal

Créer un agent DeepBlender qui :

- possède un état typé ;
- possède des méthodes agentiques ;
- manipule un objet Blender ;
- utilise un skill ;
- utilise un tool/plugin ;
- produit un résultat typé.

## Phase 2 — Blender

- connexion Blender ;
- worker ;
- inspection ;
- génération Python ;
- sauvegarde ;
- render.

## Phase 3 — CodeAct

- génération de code ;
- manipulation d'objets vivants ;
- boucles ;
- appels imbriqués ;
- `asyncio`.

## Phase 4 — Skills

- registry ;
- loading ;
- progressive disclosure ;
- références ;
- exemples.

## Phase 5 — Memory / Context

Utiliser les mécanismes NOOA pour :

- préférences ;
- connaissances ;
- conventions ;
- décisions ;
- historique utile.

Ne pas créer de système parallèle.

## Phase 6 — Collaboration

Exploiter :

- nested agentic calls ;
- `asyncio` ;
- méthodes spécialisées ;
- stratégies.

## Phase 7 — QA

Créer :

```text
QAReport
RevisionSpec
```

et la boucle :

```text
FAIL → Revision → Re-run
```

## Phase 8 — Artifacts

Créer :

- registry ;
- versioning ;
- provenance ;
- manifests.

## Phase 9 — Production graphs

Ajouter :

- dependency graph ;
- provenance graph ;
- knowledge graph si nécessaire.

## Phase 10 — Industrialisation

- workers multiples ;
- GPU scheduling ;
- render farm ;
- stockage ;
- audio ;
- FFmpeg ;
- assets ;
- compositing.

---

# 35. Règle d'or

À chaque nouvelle fonctionnalité, poser cette question :

> **« Est-ce que NOOA sait déjà faire cela ? »**

Si oui :

```text
UTILISER NOOA
```

Si non :

```text
Est-ce une responsabilité du domaine audiovisuel ?
```

Si oui :

```text
AJOUTER À DEEPBLENDER
```

Sinon :

```text
Ne pas ajouter.
```

---

# 36. Architecture finale conceptuelle

```text
                         USER
                           │
                           ▼
                    DeepBlender API
                           │
                           ▼
                 ┌───────────────────┐
                 │       NOOA        │
                 │                   │
                 │ Agent runtime     │
                 │ Context           │
                 │ Memory            │
                 │ State             │
                 │ Events            │
                 │ Strategies        │
                 │ CodeAct           │
                 │ Validation        │
                 │ Typed contracts   │
                 │ Live objects      │
                 │ asyncio           │
                 └─────────┬─────────┘
                           │
                           ▼
                 DEEPBLENDER AGENTS
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          Skills         Tools        Domain
                                         │
                            ┌────────────┼────────────┐
                            ▼            ▼            ▼
                         Blender      Assets       Production
                            │
                         Plugin
                            │
                         Worker
                            │
                         Blender
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              Render                  QA
                 │                     │
                 └──────────┬──────────┘
                            ▼
                        Artifacts
                            │
                    ┌───────┴───────┐
                    ▼               ▼
                Provenance       Graphs
```

---

# 37. Formule finale

```text
NOOA
    = cerveau + runtime agentique

DeepBlender
    = monde de production audiovisuelle

Skills
    = connaissances spécialisées

Tools
    = capacités d'action

Plugins
    = frontières externes

Workers
    = exécution isolée

Artifacts
    = résultats persistants

Graphs
    = relations métier

QA
    = vérification

Human
    = jugement créatif
```

> **DeepBlender ne doit pas chercher à être meilleur que NOOA dans le domaine des agents. Il doit devenir extrêmement bon dans le domaine Blender / production audiovisuelle tout en exploitant profondément les primitives NOOA.**

---

# 38. Critère architectural de réussite

L'architecture est saine si l'on peut demander :

> « Est-ce que cette fonctionnalité est déjà fournie par NOOA ? »

et supprimer toute abstraction DeepBlender qui ne fait que la reproduire.

À l'inverse, si l'on demande :

> « Comment cet agent sait-il que ce render correspond au Shot 12, quelle version de l'asset il utilise, quel GPU l'a produit et quelle révision a corrigé le QA ? »

la réponse doit venir de DeepBlender.

C'est cette frontière qui permet de garder l'architecture petite, extensible et fidèle à NOOA.
