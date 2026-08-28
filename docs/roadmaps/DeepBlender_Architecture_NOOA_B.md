# DeepBl4nder — Architecture de référence et feuille de route

> **Statut :** architecture cible et feuille de route initiale  
> **Version :** 0.1  
> **Runtime agentique :** NVIDIA NeMo Labs OO-Agents (NOOA)  
> **Domaine :** production audiovisuelle assistée par agents IA avec Blender

---

## 1. Vision

DeepBl4nder est un runtime de production audiovisuelle assistée par agents IA.

L'objectif initial est de transformer un brief créatif en une courte séquence Blender exploitable, reproductible, observable et itérable, tout en gardant l'humain dans la boucle.

Exemple :

```text
Brief
  ↓
Intention structurée
  ↓
SceneSpec / ShotSpec
  ↓
Storyboard / Prévisualisation
  ↓
Génération Python Blender
  ↓
Validation
  ↓
Blender Worker
  ↓
Render
  ↓
QA
  ↓
Revision
  ↓
Render amélioré
```

Le MVP vise des séquences de **5 à 10 secondes**, et non la génération autonome de longs métrages.

---

# 2. Principe architectural fondamental

DeepBl4nder ne doit pas reconstruire un framework d'agents complet autour de NOOA.

NOOA constitue la couche agentique :

```text
NOOA
├── Agent runtime
├── Context management
├── State / state rendering
├── Memory
├── Events
├── Validated LLM loops
├── Typed inputs / outputs
├── Pass-by-reference
└── Code-as-action
```

DeepBl4nder apporte la couche métier :

```text
DeepBl4nder
├── Agents métier
├── Skills
├── Tools
├── Plugins
├── Production domain
├── Blender integration
├── Code generation
├── Workers
├── Artifacts
├── QA
└── Policies spécifiques au domaine
```

Principe :

> **NOOA fournit le runtime agentique ; DeepBl4nder fournit le monde de production audiovisuelle dans lequel les agents travaillent.**

---

# 3. Répartition des responsabilités

| Élément | Responsabilité |
|---|---|
| NOOA | Runtime agentique, contexte, mémoire, événements, boucle LLM, état |
| Agent | Décision et raisonnement |
| Skill | Connaissance / procédure spécialisée |
| Tool | Action exécutable |
| Plugin | Connexion à un système externe |
| Worker | Exécution isolée d'une opération lourde |
| Artifact | Résultat métier produit ou utilisé |
| Workflow | Organisation déterministe des étapes |
| Graph | Relations complexes entre production, dépendances et provenance |
| QA | Vérification technique, visuelle et sémantique |
| Policy | Permissions, sécurité, budgets et contraintes |
| Human | Validation des décisions à forte valeur |

---

# 4. Architecture générale

```text
                         USER
                           │
                           ▼
                    API / UI / CLI
                           │
                           ▼
                    ┌─────────────┐
                    │    NOOA     │
                    │ Agent       │
                    │ Runtime     │
                    └──────┬──────┘
                           │
                 ┌─────────┼─────────┐
                 │         │         │
              Context    Memory    Events
                 │         │         │
                 └─────────┼─────────┘
                           │
                           ▼
                    DirectorAgent
                           │
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
              Skills     State     Domain
                           │
                           ▼
                     SceneSpec
                           │
                           ▼
                    BlenderAgent
                           │
                     Tool calls
                           │
                           ▼
                    BlenderPlugin
                           │
                           ▼
                    Worker Manager
                           │
                           ▼
                    Blender Worker
                           │
                           ▼
                        Blender
                           │
                           ▼
                        Render
                           │
                           ▼
                       QAAgent
                       /                         PASS      FAIL
                     │          │
                     ▼          ▼
                 Artifact    Revision
                  Registry      │
                                └──► BlenderAgent
```

---

# 5. Architecture des dossiers

```text
DeepBl4nder/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── agents.md
│   │   ├── skills.md
│   │   ├── tools.md
│   │   ├── plugins.md
│   │   ├── workers.md
│   │   ├── artifacts.md
│   │   ├── graphs.md
│   │   ├── security.md
│   │   └── provenance.md
│   │
│   ├── production/
│   │   ├── pipeline.md
│   │   ├── storyboard.md
│   │   ├── previs.md
│   │   ├── animation.md
│   │   ├── rendering.md
│   │   └── qa.md
│   │
│   └── development/
│       ├── contributing.md
│       ├── creating-agent.md
│       ├── creating-skill.md
│       ├── creating-plugin.md
│       └── testing.md
│
├── src/
│   └── DeepBl4nder/
│       │
│       ├── agents/
│       │   ├── base.py
│       │   ├── director/
│       │   │   └── agent.py
│       │   ├── blender/
│       │   │   └── agent.py
│       │   ├── code/
│       │   │   └── agent.py
│       │   └── qa/
│       │       └── agent.py
│       │
│       ├── skills/
│       │   ├── registry.py
│       │   ├── loader.py
│       │   ├── resolver.py
│       │   └── progressive.py
│       │
│       ├── tools/
│       │   ├── base.py
│       │   ├── blender.py
│       │   ├── filesystem.py
│       │   ├── rendering.py
│       │   └── inspection.py
│       │
│       ├── plugins/
│       │   ├── base.py
│       │   ├── blender/
│       │   │   ├── plugin.py
│       │   │   ├── bridge.py
│       │   │   ├── scene.py
│       │   │   ├── render.py
│       │   │   └── inspection.py
│       │   ├── ffmpeg/
│       │   │   └── plugin.py
│       │   ├── audio/
│       │   │   └── plugin.py
│       │   └── assets/
│       │       └── plugin.py
│       │
│       ├── codegen/
│       │   ├── blender_python.py
│       │   ├── templates.py
│       │   ├── validator.py
│       │   ├── sanitizer.py
│       │   └── formatter.py
│       │
│       ├── workers/
│       │   ├── base.py
│       │   ├── manager.py
│       │   ├── blender/
│       │   │   ├── worker.py
│       │   │   └── process.py
│       │   └── render/
│       │       └── worker.py
│       │
│       ├── production/
│       │   ├── specs/
│       │   │   ├── scene.py
│       │   │   ├── shot.py
│       │   │   ├── asset.py
│       │   │   ├── animation.py
│       │   │   └── lighting.py
│       │   ├── workflows.py
│       │   └── dependencies.py
│       │
│       ├── artifacts/
│       │   ├── models.py
│       │   ├── registry.py
│       │   ├── versioning.py
│       │   └── provenance.py
│       │
│       ├── graphs/
│       │   ├── production.py
│       │   ├── dependencies.py
│       │   ├── provenance.py
│       │   └── knowledge.py
│       │
│       ├── qa/
│       │   ├── technical.py
│       │   ├── visual.py
│       │   ├── continuity.py
│       │   └── evaluator.py
│       │
│       ├── policies/
│       │   ├── permissions.py
│       │   ├── code_policy.py
│       │   └── budget.py
│       │
│       └── api/
│           ├── server.py
│           ├── projects.py
│           ├── jobs.py
│           └── websocket.py
│
├── skills/
│   ├── blender-python/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── examples/
│   │   └── scripts/
│   │
│   ├── cinematography/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── examples/
│   │
│   ├── storytelling/
│   │   └── SKILL.md
│   │
│   ├── storyboard/
│   │   └── SKILL.md
│   │
│   ├── animation/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── examples/
│   │
│   ├── lighting/
│   │   └── SKILL.md
│   ├── modeling/
│   │   └── SKILL.md
│   ├── rigging/
│   │   └── SKILL.md
│   ├── materials/
│   │   └── SKILL.md
│   ├── audio/
│   │   └── SKILL.md
│   ├── compositing/
│   │   └── SKILL.md
│   └── qa/
│       └── SKILL.md
│
├── plugins/
│   ├── blender/
│   │   ├── plugin.toml
│   │   └── ...
│   ├── ffmpeg/
│   │   ├── plugin.toml
│   │   └── ...
│   └── audio/
│       ├── plugin.toml
│       └── ...
│
├── projects/
│   └── examples/
│       └── rainy-alley/
│           ├── project.toml
│           ├── project.db
│           ├── assets/
│           ├── scenes/
│           ├── shots/
│           ├── generated/
│           │   ├── python/
│           │   └── manifests/
│           ├── renders/
│           ├── audio/
│           └── exports/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── agents/
│   ├── skills/
│   ├── plugins/
│   ├── workers/
│   ├── security/
│   └── golden/
│
├── configs/
│   ├── default.toml
│   ├── development.toml
│   └── production.toml
│
└── scripts/
    ├── dev.py
    ├── install_skill.py
    ├── install_plugin.py
    └── worker.py
```

---

# 6. Skills : inspiration OpenCode

Les skills sont des paquets de connaissances et de procédures.

Exemple :

```text
skills/blender-python/
├── SKILL.md
├── references/
├── examples/
└── scripts/
```

Le principe est la **progressive disclosure** :

```text
Skill Registry
      ↓
Metadata
      ↓
Skill selection
      ↓
SKILL.md
      ↓
Reference pertinente
      ↓
Exemple ou script ciblé
```

Un agent ne doit pas recevoir toute la documentation Blender à chaque appel.

Exemple minimal :

```markdown
---
name: blender-python
description: Generate and manipulate Blender scenes using bpy safely.
---

# Blender Python

Use bpy to create and modify deterministic Blender scenes.

## Rules

- Prefer reproducible scripts.
- Inspect before destructive operations.
- Keep scene organization explicit.
- Never execute arbitrary system commands.

## References

Read `references/bpy.md` for API details.
Read `references/scene-api.md` for scene organization.
```

---

# 7. Agents

Le MVP reste volontairement limité :

```text
DirectorAgent
      │
      ├── BlenderAgent
      │
      └── QAAgent
```

## DirectorAgent

Responsable de :

- comprendre le brief ;
- structurer l'intention ;
- créer `SceneSpec` et `ShotSpec` ;
- sélectionner les skills ;
- planifier la production.

## BlenderAgent

Responsable de :

- transformer les specs en actions Blender ;
- sélectionner les skills Blender ;
- générer ou demander la génération de Python ;
- utiliser les tools ;
- interagir avec le `BlenderPlugin` ;
- interpréter les résultats du worker.

## QAAgent

Responsable de :

- QA technique ;
- QA visuel ;
- QA de continuité ;
- diagnostic ;
- production d'une `RevisionSpec`.

Plus tard :

```text
StoryAgent
VisualAgent
AnimationAgent
AudioAgent
AssetAgent
TranslationAgent
```

Mais il faut éviter la multiplication prématurée des agents.

---

# 8. Tools et Plugins

Relation :

```text
Agent
  │
  ▼
Tool
  │
  ▼
Plugin
  │
  ▼
Système externe
```

Exemple :

```text
BlenderPlugin
├── inspect_scene()
├── execute_python()
├── render()
├── save_scene()
└── load_asset()
```

Le plugin encapsule la communication avec Blender.

Plugins futurs :

```text
FFmpeg
Audio
TTS
Asset Library
Render Farm
Storage
Git
Knowledge Graph
```

---

# 9. Blender Worker

Blender doit être isolé du processus principal.

```text
NOOA Agent
    │
    ▼
Blender Tool
    │
    ▼
BlenderPlugin
    │
    ▼
Worker Manager
    │
    ▼
Blender Worker
    │
    ▼
Blender Process
```

Avantages :

- isolation ;
- récupération après crash ;
- contrôle CPU/GPU ;
- timeouts ;
- parallélisation ;
- plusieurs scènes simultanées.

Cible :

```text
Worker 1 → Scene A
Worker 2 → Scene B
Worker 3 → Scene C
```

---

# 10. Génération de Python Blender

Le code généré par le modèle ne doit jamais être exécuté directement.

Pipeline :

```text
LLM
 ↓
Generated Python
 ↓
AST parsing
 ↓
Static validation
 ↓
Policy check
 ↓
Sandbox / Worker
 ↓
Blender
 ↓
Result
```

Contrôles :

- imports ;
- accès fichiers ;
- subprocess ;
- réseau ;
- chemins ;
- opérations destructives ;
- ressources ;
- durée d'exécution.

Objectif :

> Aucun code généré ne doit sortir du périmètre autorisé.

---

# 11. Structured Specs

Il est préférable de ne pas demander au modèle :

```text
Brief → énorme script Python
```

Préférer :

```text
Brief
 ↓
SceneSpec
 ↓
ShotSpec
 ↓
AnimationSpec
 ↓
LightingSpec
 ↓
Python Blender
```

Exemple conceptuel :

```python
class ShotSpec:
    duration: float
    camera: CameraSpec
    environment: EnvironmentSpec
    characters: list[CharacterSpec]
    animation: AnimationSpec
    lighting: LightingSpec
```

Cela sépare :

- intention ;
- structure ;
- implémentation.

---

# 12. Artifacts

Un artifact est un résultat concret ou une unité de production identifiable.

Exemples :

```text
Brief
SceneSpec
ShotSpec
Storyboard
Python script
.blend
.png
.mp4
.wav
QA report
Render manifest
```

Exemple de chaîne :

```text
Brief
 ↓
SceneSpec.json
 ↓
ShotSpec.json
 ↓
scene_v001.py
 ↓
scene_v001.blend
 ↓
render_v001.png
 ↓
qa_v001.json
```

Chaque artifact doit idéalement avoir :

```text
id
type
version
created_at
created_by
parent_artifacts
agent_run
skill_versions
model
parameters
hash
status
```

---

# 13. Provenance

Le système doit pouvoir répondre :

> « D'où vient ce rendu ? »

Exemple :

```text
render_v002.png
       │
       └── generated from
              │
              ▼
       scene_v002.blend
              │
              └── generated from
                     │
                     ▼
                scene_v002.py
                     │
                     └── generated from
                            │
                            ▼
                         ShotSpec
                            │
                            ▼
                       SceneSpec
                            │
                            ▼
                      BlenderAgent
                            │
                            ▼
                       NOOA / LLM
                            │
                            ├── Skill A
                            ├── Skill B
                            └── Skill C
```

Cela permet :

- reproductibilité ;
- comparaison de versions ;
- rollback ;
- audit ;
- analyse des coûts ;
- diagnostic.

---

# 14. Graphs

Il faut distinguer plusieurs graphes.

## 14.1 Workflow graph

Décrit les étapes :

```text
Brief
 ↓
Story
 ↓
Storyboard
 ↓
SceneSpec
 ↓
Blender
 ↓
Render
 ↓
QA
 ├── PASS → Final
 └── FAIL → Revision
```

Il peut rester principalement en Python et ne nécessite pas forcément un moteur de graph dédié.

## 14.2 Dependency graph

Décrit les dépendances :

```text
SceneSpec
 ├── Shot01
 │    └── Render01
 │
 └── Shot02
      └── Render02
```

Question :

> « Si cet asset change, quels artifacts faut-il recalculer ? »

## 14.3 Knowledge graph

Décrit les relations sémantiques :

```text
Character_A
 ├── wears → Red_Jacket
 ├── appears_in → Shot_03
 └── interacts_with → Door_A

Shot_03
 ├── located_in → Alley_A
 ├── uses_camera → Camera_02
 └── generated_by → BlenderAgent
```

Il devient particulièrement utile pour :

- continuité ;
- recherche ;
- dépendances ;
- relations entre assets ;
- mémoire de production.

## 14.4 Provenance graph

Décrit la chaîne de création :

```text
Brief
 ↓
SceneSpec
 ↓
ShotSpec
 ↓
Python
 ↓
Blend
 ↓
Render
 ↓
QA
 ↓
Revision
```

À terme, ces graphes peuvent converger vers un **Production Knowledge Graph**.

---

# 15. QA

Le QA comporte plusieurs niveaux.

## Technique

```text
✓ .blend valide
✓ assets présents
✓ références valides
✓ FPS correct
✓ résolution correcte
✓ render terminé
```

## Visuel

```text
✓ personnage visible
✓ composition correcte
✓ éclairage cohérent
✓ caméra correcte
✓ animation présente
```

## Continuité

```text
✓ personnage cohérent
✓ costume cohérent
✓ décor cohérent
✓ relations avec les plans précédents
```

## Sémantique

Comparer :

```text
Brief
  ↕
Render
```

Exemple :

> Le rendu contient bien une ruelle et un personnage, mais l'ambiance lumineuse ne correspond pas au brief.

---

# 16. Boucle de correction

C'est le cœur du MVP :

```text
Brief
 ↓
DirectorAgent
 ↓
SceneSpec
 ↓
BlenderAgent
 ↓
Skills
 ↓
Code generation
 ↓
Validation
 ↓
Blender Worker
 ↓
Render
 ↓
QA
 ├── PASS → Artifact
 │
 └── FAIL
       ↓
   Diagnosis
       ↓
   RevisionSpec
       ↓
   BlenderAgent
```

L'agent ne doit donc pas simplement produire une première réponse : il doit pouvoir **observer le résultat et corriger**.

---

# 17. Pipeline de production cible

```text
1. Intention & Briefing
2. Scénario
3. Storyboard
4. Prévisualisation / Animatic
5. Faisabilité technique
6. Préparation des assets
7. UV / Texturing / Shading
8. Rigging / Weight Painting
9. Layout
10. Animation / Caméra / Lumière / Simulations
11. Rendu préliminaire
12. Itérations / Corrections
13. Rendu final
14. Compositing
15. Mixage / Voix / Sous-titres / Langues
16. QA / Export
```

Le MVP n'automatise pas tout ce pipeline.

---

# 18. Cas d'usage

DeepBl4nder doit progressivement couvrir :

- génération de scènes Blender ;
- storyboard ;
- animatique ;
- prévisualisation ;
- variantes de caméra ;
- variantes de décor ;
- variantes d'éclairage ;
- animation ;
- gestion d'assets ;
- sound design ;
- musique ;
- voix ;
- sous-titres ;
- traduction ;
- compositing ;
- QA ;
- render farm.

---

# 19. Objectifs mesurables

## Latence

```text
Brief → premier rendu
< 5 min pour une scène de démonstration

Brief → séquence 10 s
< 10 min pour la cible initiale
```

## Coût

```text
< 1 € par scène de démonstration
```

Inclure LLM + exécution + rendu.

## Qualité

À maturité :

```text
QA automatique au premier coup ≥ 60 %
```

sur un golden set.

## Scalabilité

```text
3 workers parallèles
1 worker / scène
GPU rendering
```

## Fiabilité

Une interruption du runtime doit permettre :

```text
Crash
 ↓
Restart
 ↓
Recovery
 ↓
Resume
```

avec aucune perte de données de production.

## Observabilité

Le coût et l'état doivent être visibles en temps réel, avec alerte de dépassement de budget en moins de 30 secondes.

---

# 20. Sécurité

Principes :

1. moindre privilège ;
2. isolation de Blender ;
3. validation du code généré ;
4. chemins de fichiers contrôlés ;
5. réseau limité ;
6. ressources limitées ;
7. opérations destructives contrôlées ;
8. aucune opération interdite silencieuse.

Exemple :

```text
BlenderAgent
├── read_scene       ALLOW
├── modify_scene     ALLOW
├── render           ALLOW
├── save             ALLOW
├── shell            DENY
└── arbitrary_network DENY
```

---

# 21. MVP réel

Le premier MVP doit être beaucoup plus petit que l'architecture cible.

```text
DeepBl4nder/
├── src/DeepBl4nder/
│   ├── agents/
│   │   ├── director.py
│   │   ├── blender.py
│   │   └── qa.py
│   ├── skills/
│   │   ├── registry.py
│   │   └── loader.py
│   ├── plugins/
│   │   └── blender.py
│   ├── codegen/
│   │   └── blender_python.py
│   └── workers/
│       └── blender.py
│
├── skills/
│   ├── blender-python/
│   │   └── SKILL.md
│   ├── cinematography/
│   │   └── SKILL.md
│   ├── lighting/
│   │   └── SKILL.md
│   └── animation/
│       └── SKILL.md
│
├── projects/
│   └── demo/
│
└── tests/
```

---

# 22. Première démonstration

Brief :

> « Crée une ruelle sombre sous la pluie, avec un personnage qui marche vers une porte pendant 5 secondes. »

Flux :

```text
Brief
 ↓
DirectorAgent
 ↓
SceneSpec
 ↓
BlenderAgent
 ↓
Skills:
  blender-python
  cinematography
  lighting
  animation
 ↓
Python generation
 ↓
Security validation
 ↓
Blender Worker
 ↓
Render
 ↓
QAAgent
 ↓
PASS / Revision
```

Le MVP est réussi lorsque cette boucle est :

- reproductible ;
- observable ;
- sécurisée ;
- itérative ;
- suffisamment fiable.

---

# 23. Feuille de route

## Phase 0 — NOOA + Blender

- intégrer NOOA ;
- créer le premier agent ;
- connecter Blender ;
- valider un appel simple.

## Phase 1 — Blender Worker

- lancer Blender isolément ;
- exécuter des scripts ;
- récupérer logs et erreurs ;
- sauvegarder `.blend` ;
- rendre une image ou séquence.

## Phase 2 — Skills

Créer :

```text
Skill Registry
Skill Loader
Skill Resolver
Progressive Disclosure
```

Premiers skills :

```text
blender-python
cinematography
lighting
animation
```

## Phase 3 — Structured Specs

Créer :

```text
SceneSpec
ShotSpec
AssetSpec
AnimationSpec
LightingSpec
```

## Phase 4 — QA

Ajouter :

```text
Technical QA
Visual QA
Continuity QA
```

et :

```text
FAIL → Diagnosis → Revision → Render
```

## Phase 5 — Artifacts

Ajouter :

- registry ;
- versions ;
- hashes ;
- manifests ;
- provenance.

## Phase 6 — Graphs

Commencer par :

```text
Dependency Graph
Provenance Graph
```

Puis introduire le :

```text
Production Knowledge Graph
```

lorsque les relations de production le justifient.

## Phase 7 — Workers multiples

Ajouter :

```text
Worker Manager
Scheduler
GPU allocation
Parallel jobs
```

## Phase 8 — Extensions

Ajouter progressivement :

```text
FFmpeg
Audio
TTS
Asset libraries
Render farm
Storage
Git
```

## Phase 9 — Production complète

Étendre vers :

```text
Story
Storyboard
Animatic
Assets
Animation
Lighting
Audio
Compositing
Localization
Final Export
```

---

# 24. Ce qu'il faut éviter

### Ne pas créer un agent par micro-compétence

Éviter :

```text
CameraAgent
LightingAgent
FocalLengthAgent
ColorAgent
...
```

Préférer :

```text
BlenderAgent
├── cinematography skill
├── lighting skill
└── composition skill
```

### Ne pas reconstruire les services déjà fournis par NOOA

Éviter de recréer sans nécessité :

```text
Context manager
Memory manager
Agent loop
Event infrastructure
Observability de base
```

DeepBl4nder doit s'appuyer sur les capacités de NOOA et ne créer une abstraction supplémentaire que lorsqu'elle répond à un besoin métier.

### Ne pas exécuter directement le code généré

Éviter :

```python
exec(llm_output)
```

Préférer :

```text
Generated Python
 ↓
AST
 ↓
Policy
 ↓
Sandbox
 ↓
Worker
```

### Ne pas laisser le LLM contrôler seul le runtime

Le LLM est responsable du raisonnement.

Le runtime reste responsable de :

- sécurité ;
- scheduling ;
- ressources ;
- retries ;
- timeouts ;
- workers ;
- checkpoints ;
- budgets.

---

# 25. Formule architecturale

La philosophie peut être résumée ainsi :

```text
                    NOOA
                     │
        intelligence agentique
                     │
       ┌─────────────┼─────────────┐
       │             │             │
    Context        Memory        Events
       │             │             │
       └─────────────┼─────────────┘
                     │
                    Agent
                     │
       ┌─────────────┼─────────────┐
       │             │             │
    Skills         Tools        State
       │             │             │
       └─────────────┼─────────────┘
                     │
                  Plugins
                     │
                  Workers
                     │
                  Blender
                     │
                 Artifacts
                     │
                    QA
                     │
               PASS / FAIL
                     │
                 Revision
```

Principe directeur :

```text
LLM décide.
Python structure.
Skills enseignent.
Tools agissent.
Plugins connectent.
Workers exécutent.
Policies contrôlent.
Artifacts persistent.
Graphs relient.
QA vérifie.
Humain valide.
NOOA fournit le runtime agentique.
```

---

# 26. Critère de réussite

Le premier jalon n'est pas :

> « produire un film ».

Le premier jalon est :

> **Prendre un brief inédit, produire une séquence Blender de 5–10 secondes, tracer sa production, détecter ses défauts, effectuer une correction et produire une version améliorée.**

La boucle fondamentale de DeepBl4nder est donc :

```text
Intent
  ↓
Plan
  ↓
Skills
  ↓
Structured Specs
  ↓
Code
  ↓
Worker
  ↓
Render
  ↓
QA
  ↓
Revision
```

Cette boucle constitue le **socle de départ**. Le reste de l'architecture est une industrialisation progressive de ce cycle.

