# Référence Production Pipeline — DeepBl4nder

> Document de référence exhaustif pour le module `DeepBl4nder/production/`.
> Dernière mise à jour : 2026-08-27

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture et flux de données](#2-architecture-et-flux-de-données)
3. [Module par module](#3-module-par-module)
   - [3.1 `__init__.py`](#31-__init__py)
   - [3.2 `runner.py` — Orchestrateur principal](#32-runnerpy--orchestrateur-principal)
   - [3.3 `postprod.py` — Post-production](#33-postprodpy--post-production)
   - [3.4 `events.py` — Journal d'événements](#34-eventspy--journal-de-vénements)
   - [3.5 `context.py` — Injection de contexte NOOA](#35-contextpy--injection-de-contexte-nooa)
   - [3.6 `budget.py` — Suivi budgétaire](#36-budgetpy--suivi-budgétaire)
   - [3.7 `checkpoints.py` — Points de contrôle](#37-checkpointspy--points-de-contrôle)
   - [3.8 `runs.py` — Runs de production](#38-runspy--runs-de-production)
   - [3.9 `rendering.py` — Gestion du rendu](#39-renderingpy--gestion-du-rendu)
   - [3.10 `plugins.py` — Raccourcis plugins](#310-pluginspy--raccourcis-plugins)
   - [3.11 `fallbacks.py` — Fallbacks déterministes](#311-fallbackspy--fallbacks-déterministes)
4. [Dépendances inter-modules](#4-dépendances-inter-modules)
5. [Constantes et configurations](#5-constantes-et-configurations)

---

## 1. Vue d'ensemble

Le package `DeepBl4nder/production/` constitue le **cœur orchestrateur** du pipeline DeepBl4nder. Il connecte les agents IA (NOOA) aux briques de production (rendu, post-production, plugins) en garantissant :

- **Traçabilité** : chaque transition d'étape est journalisée avant d'être appliquée (append-only).
- **Observabilité** : événements temps réel via `EventBus` (SSE gateway) et hooks.
- **Fiabilité** : reprise après crash par rejeu d'événements non consommés.
- **Contrôle budgétaire** : enforcement déterministe et alertes en temps réel.
- **Déterminisme** : fallbacks structuraux quand les générations LLM échouent deux fois.

### Fichiers du package

| Fichier | Rôle principal |
|---|---|
| `__init__.py` | Expositions publiques du package |
| `runner.py` | Orchestrateur principal du pipeline (1334 lignes) |
| `postprod.py` | Étapes de post-production (audio, musique, compositing, etc.) |
| `events.py` | Journal persistant (JSONL) et bus pub/sub |
| `context.py` | Injection de variables NOOA dans les agents |
| `budget.py` | Suivi des coûts et alertes de dépassement |
| `checkpoints.py` | Points de contrôle pour reprise après crash |
| `runs.py` | Modèle `ProductionRun` et `ProductionStep` |
| `rendering.py` | Gestion du rendu Blender (single-shot et parallèle) |
| `plugins.py` | Mixin de raccourcis d'accès aux plugins |
| `fallbacks.py` | Génération déterministe de secours |

---

## 2. Architecture et flux de données

```
Brief
  │
  ▼
StoryAgent ──▶ StorySpec
  │
  ▼
StoryboardAgent ──▶ StoryboardSpec
  │                    [HITL Approval Gate]
  ▼
DirectorAgent ──▶ SceneSpec ──▶ ProvenanceGraph
  │                │
  │  [optionnel]   ├──▶ CharacterDesignerAgent
  │                └──▶ EnvironmentArtistAgent
  ▼
BlenderAgent / UE5Agent / GodotAgent / AIVideoAgent ──▶ BlenderScript / UE5Commands / GodotCommands / AIVideoCommands
  │                          ▼
  │                     Validation AST / REST API
  ▼
QAAgent ──▶ QAReport
  │          │
  │   [échec?] ──▶ RevisionSpec ──▶ boucle de révision
  │          │
  ▼   [passé]
AnimationAgent (optionnel)
  │
  ▼
┌─────────────────── Post-production parallèle ───────────────────┐
│  RenderManager │ MusicComposer │ SoundDesigner │ LocalizationAgent │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                    CompositingAgent ──▶ FFmpegPlugin
                             │
                             ▼
                     ReviewAgent ──▶ RunOutcome
```

### Cycle de vie d'un run

1. **Création** : `ProductionRun` créé avec `status="created"`, étapes définies.
2. **Vérification budget** : si `BudgetTracker.over_budget()`, le run passe `blocked` immédiatement.
3. **Reprise** : `CheckpointManager.load_checkpoints()` charge les étapes validées d'un run interrompu.
4. **Exécution séquentielle** : story → storyboard → director → character_design → environment → script → qa → animation.
5. **Boucle QA → révision** : si `QAReport.passed == False`, injection du feedback et régénération (jusqu'à `max_revisions`).
6. **Post-production parallèle** : render, music, sound_design, audio, localization en `asyncio.gather`.
7. **Compositing** : fusion vidéo+audio+sous-titres via FFmpeg.
8. **État terminal** : `completed` ou `blocked`.

---

## 3. Module par module

### 3.1 `__init__.py`

**Chemin** : `DeepBl4nder/production/__init__.py`

**Description** : Définit l'interface publique du package via `__all__`.

**Exports** :

| Nom | Type | Module source |
|---|---|---|
| `BudgetAlert` | `dataclass(frozen=True)` | `budget.py` |
| `BudgetTracker` | `dataclass` | `budget.py` |
| `EventBus` | `class` | `events.py` |
| `EventLog` | `dataclass` | `events.py` |
| `PipelineRunner` | `class` | `runner.py` |
| `ProductionEvent` | `dataclass(frozen=True)` | `events.py` |
| `ProductionRun` | `dataclass` | `runs.py` |
| `ProductionStep` | `dataclass` | `runs.py` |
| `RunOutcome` | `dataclass` | `runner.py` |

---

### 3.2 `runner.py` — Orchestrateur principal

**Chemin** : `DeepBl4nder/production/runner.py` (1334 lignes)

**Description** : Le fichier central du pipeline. Il relie les agents NOOA aux briques de production, orchestre l'exécution complète d'un brief en un `RunOutcome`, et gère les boucles de révision, la reprise, le cache LLM, et les plugins.

#### Constantes et types

```python
CostHook = Callable[[str], float]
```

```python
_STEPS = ("story", "storyboard", "director", "character_design",
          "environment", "blender", "qa", "animation", "render")
```

```python
_POST_STEPS = ("music", "sound_design", "audio", "localization",
               "compositing", "review")
```

```python
_RESUME_STEP_BY_KEY = {
    "story": "story",
    "storyboard": "storyboard",
    "scene": "director",
    "character_design": "character_design",
    "environment": "environment",
    "script": "blender",
    "report": "qa",
    "animation": "animation",
}
```

#### Fonction utilitaire

```python
def _compact(payload: dict[str, Any], limit: int = 400) -> str
```
- **Paramètres** : `payload` — dict JSON-serializable ; `limit` — taille max en caractères (défaut 400).
- **Retour** : chaîne sur une ligne, tronquée si nécessaire avec `…(N car.)`.
- **Usage** : formatage des payloads d'événements pour le journal texte.

#### Fonction utilitaire

```python
def _to_mapping(obj: Any) -> dict[str, Any]
```
- Sérialise un dataclass du domaine en dict JSON-safe via `to_mapping()` ou `asdict()`.

#### Fonction utilitaire

```python
def _safe_name(name: str) -> str
```
- Réduit un nom en nom de fichier sûr (alphanumériques + `-_`).

---

##### `_ForwardingEventLog` (classe interne)

**Hérite de** : `EventLog`

**Description** : Subclasse d'`EventLog` qui relaie chaque événement persisté à un hook temps réel.

**Constructeur** :
```python
def __init__(self, path: Path, forward: Callable[[str, dict[str, Any]], None]) -> None
```
- `path` : chemin du fichier JSONL.
- `forward` : callback `(kind, payload) -> None` invoqué après chaque `append`.

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `append` | `(kind: str, payload: dict[str, Any] \| None = None) -> ProductionEvent` | Appelle `super().append()` puis `self._forward(kind, event.payload)`. |

---

##### `RunOutcome` (dataclass)

**Description** : Résultat complet d'un run : état, artifacts, coûts et specs finales.

**Champs** :

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `run` | `ProductionRun` | *(requis)* | Objet run avec toutes les étapes |
| `artifacts` | `ArtifactRegistry` | *(requis)* | Registre des artifacts produits |
| `provenance` | `ProvenanceGraph` | *(requis)* | Graphe de provenance |
| `budget` | `BudgetTracker \| None` | `None` | Suivi budgétaire |
| `scene` | `SceneSpec \| None` | `None` | Spécification de scène finale |
| `script` | `BlenderScript \| None` | `None` | Script Blender généré |
| `report` | `QAReport \| None` | `None` | Rapport d'évaluation QA |
| `revisions` | `int` | `0` | Nombre de révisions effectuées |
| `render_output` | `RenderOutput \| None` | `None` | Sortie de rendu vidéo |
| `audio_plan` | `AudioPlan \| None` | `None` | Plan audio |
| `audio_master` | `AudioMaster \| None` | `None` | Master audio |
| `composite_spec` | `CompositeSpec \| None` | `None` | Spécification de compositing |
| `language_packages` | `list[LanguagePackage] \| None` | `None` | Packages de localisation |
| `music_plan` | `MusicPlan \| None` | `None` | Plan musique |
| `sound_design_plan` | `SoundDesignPlan \| None` | `None` | Plan sound design |

---

##### `PipelineRunner` (classe principale)

**Hérite de** : `PluginShortcuts`

**Description** : Exécute `brief → DirectorAgent → BlenderAgent → QAAgent` sous production. Tous les plugins sont utilisés via un `PluginRegistry` unique.

**Constructeur** :

```python
def __init__(
    self,
    *,
    project_id: str,                    # Identifiant projet
    director: Any,                      # Agent directeur
    blender: Any,                       # Agent Blender
    qa: Any,                            # Agent QA
    workdir: Path,                      # Répertoire de travail
    plugins: PluginRegistry | None,     # Registre de plugins (défaut: PluginRegistry())
    artifacts: ArtifactRegistry | None, # Registre d'artifacts (défaut: ArtifactRegistry())
    provenance: ProvenanceGraph | None, # Graphe de provenance
    budget: BudgetTracker | None,       # Tracker budgétaire
    cost_hook: CostHook | None,         # Hook de calcul de coût par étape
    max_revisions: int,                 # Nombre max de révisions QA (défaut: 1)
    max_render_retries: int,            # Nombre max de retries rendu (défaut: 2)
    event_hook: Callable[[str, dict[str, Any]], None] | None,  # Hook temps réel
    story: Any = None,                  # StoryAgent (optionnel)
    storyboard: Any = None,             # StoryboardAgent (optionnel)
    character_designer: Any = None,     # CharacterDesignerAgent (optionnel)
    environment_artist: Any = None,     # EnvironmentArtistAgent (optionnel)
    animator: Any = None,               # AnimatorAgent (optionnel)
    audio: Any = None,                  # AudioAgent (optionnel)
    music_composer: Any = None,         # MusicComposerAgent (optionnel)
    sound_designer: Any = None,         # SoundDesignerAgent (optionnel)
    localization: Any = None,           # LocalizationAgent (optionnel)
    compositing: Any = None,            # CompositingAgent (optionnel)
    review: Any = None,                 # ReviewAgent (optionnel)
    target_languages: list[str] | None, # Langues cibles de localisation
    blender_bridge: Any = None,         # Bridge d'exécution Blender
    ue5: Any = None,                    # Agent UE5
    ue5_bridge: Any = None,             # Bridge UE5
    session_factory: Any = None,        # Factory SQLAlchemy pour patches
    production_id: str | None = None,   # ID production (pour patches API)
    enable_cache: bool = True,          # Activer le cache LLM
    enable_parallel_shots: bool = True, # Rendu parallèle des plans
    max_parallel_shots: int = 4,        # Nombre max de plans parallèles
    max_parallel_llm: int = 2,          # Nombre max d'appels LLM parallèles
) -> None
```

**Attributs internes créés** :

| Attribut | Type | Description |
|---|---|---|
| `_llm_cache` | `dict[str, tuple[Any, float]]` | Cache LLM in-memory (clé → (valeur, expiry)) |
| `_cache_ttl` | `int` | TTL du cache en secondes (défaut: 3600) |
| `_llm_semaphore` | `asyncio.Semaphore` | Sémaphore de rate-limiting LLM |
| `_gpu_semaphore` | `asyncio.Semaphore` | Sémaphore de concurrence GPU |
| `_cpu_semaphore` | `asyncio.Semaphore` | Sémaphore de concurrence CPU (4) |
| `event_log` | `EventLog` ou `_ForwardingEventLog` | Journal d'événements |
| `production_run` | `ProductionRun` | Objet run de production |
| `_director_art` | `str \| None` | ID artifact director (chaînage de provenance) |
| `checkpoints` | `CheckpointManager` | Gestionnaire de checkpoints |
| `rendering` | `RenderManager` | Gestionnaire de rendu |
| `context_injector` | `ContextInjector` | Injecteur de contexte NOOA |
| `postprod` | `PostProductionRunner` | Runner de post-production |

**Méthodes publiques** :

| Méthode | Signature | Description |
|---|---|---|
| `run` | `async (brief: Brief) -> RunOutcome` | Exécute le pipeline complet et renvoie l'état final. |

**Méthodes privées** :

| Méthode | Signature | Description |
|---|---|---|
| `_emit` | `(kind: str, payload: dict[str, Any]) -> None` | Relaye un événement vers le hook temps réel et journalise en log. |
| `_reported_llm_meta` | `(agent: Any) -> dict[str, Any]` | Récupère les métadonnées du dernier appel LLM d'un agent (provider, model). |
| `_cache_key` | `(*args, **kwargs) -> str` | Génère une clé de cache déterministe (SHA-256 tronqué à 32). |
| `_cache_get` | `(key: str) -> Any \| None` | Récupère une valeur du cache si non expirée. |
| `_cache_set` | `(key: str, value: Any, ttl: int \| None) -> None` | Stocke une valeur dans le cache avec TTL. |
| `_cache_invalidate` | `(prefix: str) -> None` | Invalide toutes les entrées commençant par `prefix`. |
| `_load_pending_patches` | `() -> list[Patch]` | Charge les patches non appliqués depuis la base de données (SQLAlchemy). |
| `_mark_patches_applied` | `(patch_targets: list[str]) -> None` | Marque les patches comme appliqués en base. |
| `_cached_agent_call` | `async (agent, method_name, cache_prefix, *args, **kwargs) -> Any` | Appel d'agent avec cache LLM et semaphore. |
| `_load_latest_scene_spec` | `() -> SceneSpec \| None` | Charge la dernière `SceneSpec` depuis les artifacts ou la DB. |
| `_get_org_id` | `() -> str \| None` | Récupère l'`organization_id` depuis la table `Production`. |
| `_with_generation_retry` | `async (step: str, call_factory: Callable) -> Any` | Rejoue une fois l'appel agent après `GenerationError`. |
| `_run_story` | `async (brief: Brief) -> StorySpec \| None` | Exécute `StoryAgent → StorySpec`. |
| `_run_storyboard` | `async (story_spec: StorySpec) -> StoryboardSpec \| None` | Exécute `StoryboardAgent → StoryboardSpec`. |
| `_synthesize_storyboard` | `(story_spec: StorySpec) -> StoryboardSpec` | Fallback déterministe pour le storyboard. |
| `_synthesize_blender_script` | `(scene: SceneSpec) -> BlenderScript` | Fallback déterministe pour le script Blender. |
| `_plan` | `async (brief, story_spec, storyboard_spec) -> SceneSpec` | Exécute `DirectorAgent → SceneSpec`. |
| `_build` | `async (scene: SceneSpec) -> tuple[Any, Path]` | Route vers le bon moteur (Blender ou UE5). |
| `_build_ue5` | `async (scene: SceneSpec) -> tuple[UE5Commands, Path]` | Génère et exécute les commandes UE5. |
| `_synthesize_ue5_commands` | `(scene: SceneSpec) -> UE5Commands` | Fallback déterministe pour les commandes UE5. |
| `_build_blender` | `async (scene: SceneSpec) -> tuple[BlenderScript, Path]` | Génère le script Blender (logique originale). |
| `_assess` | `async (scene, script_path, validation, script) -> QAReport` | Exécute `QAAgent.assess()` avec validation AST. |
| `_target_step` | `(report: QAReport, validation: ValidationReport) -> str` | Détermine l'étape cible de la révision. |
| `_run_character_design` | `async (scene: SceneSpec) -> Any` | Exécute `CharacterDesignerAgent`. |
| `_run_environment` | `async (scene: SceneSpec) -> Any` | Exécute `EnvironmentArtistAgent`. |
| `_run_animation` | `async (scene: SceneSpec) -> Any` | Exécute `AnimatorAgent`. |
| `_record_revision` | `(target: str, report: QAReport, revision: int) -> None` | Enregistre une `RevisionSpec` et un artifact de révision. |
| `_charge` | `(step: str, artifact: Artifact \| None) -> None` | Enregistre le coût d'une étape via `cost_hook` et `BudgetTracker`. |
| `_write_json` | `(filename: str, data: Any) -> Path` | Écrit un fichier JSON dans le workdir. |

**Flux détaillé de `run()`** :

1. Initialise le `ProductionRun` (status `running`, étapes `_STEPS` + `_POST_STEPS`).
2. Vérifie le budget (`BudgetTracker.over_budget()`).
3. Injecte l'historique du run (`ContextInjector.inject_run_history()`).
4. Gère les demandes de révision humaine (HITL) via `revision_request_*.json`.
5. Charge les patches pending depuis la DB.
6. Charge les checkpoints (`CheckpointManager.load_checkpoints()`).
7. Calcule la chaîne de reprise et les étapes invalidées par révision/patches.
8. Exécute séquentiellement : story → storyboard → HITL approval → director → character_design → environment → script.
9. Valide le script (AST Blender ou commandes UE5).
10. Exécute le QA (boucle de révision si échec).
11. Animation (optionnelle, si QA passé).
12. Post-production parallèle (`asyncio.gather`).
13. Compositing et review finale.
14. Retourne `RunOutcome`.

---

### 3.3 `postprod.py` — Post-production

**Chemin** : `DeepBl4nder/production/postprod.py` (428 lignes)

**Description** : Extrait de `PipelineRunner` pour décomposer le runner principal. Gère : audio, musique, sound design, compositing, review, merge final, localization.

##### `PostProductionRunner` (classe)

**Hérite de** : `PluginShortcuts`

**Constructeur** :

```python
def __init__(
    self,
    *,
    audio: Any,                          # AudioAgent
    music_composer: Any,                  # MusicComposerAgent
    sound_designer: Any,                  # SoundDesignerAgent
    localization: Any,                    # LocalizationAgent
    compositing: Any,                     # CompositingAgent
    review: Any,                          # ReviewAgent
    workdir: Path,                        # Répertoire de travail
    artifacts: ArtifactRegistry,          # Registre d'artifacts
    provenance: ProvenanceGraph,          # Graphe de provenance
    production_run: ProductionRun,        # Run de production
    event_log: EventLog,                  # Journal d'événements
    plugins: Any,                         # PluginRegistry
    event_hook: Callable,                 # Hook d'émission
    charge: Callable,                     # Fonction de facturation
    write_json: Callable,                 # Fonction d'écriture JSON
    target_languages: list[str],          # Langues cibles
    llm_semaphore: asyncio.Semaphore,     # Sémaphore LLM
    reported_llm_meta: Callable,          # Fonction de métadonnées LLM
    with_generation_retry: Callable,      # Fonction de retry
    director_art: str | None = None,      # ID artifact director
) -> None
```

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `run_audio` | `async (scene: SceneSpec) -> tuple[AudioPlan, AudioMaster]` | Exécute `AudioAgent → AudioPlugin`. Génère l'ambiance, crée le master audio, enregistre les artifacts `audio_plan` et `audio_master`. |
| `run_music` | `async (scene: SceneSpec) -> MusicPlan \| None` | Exécute `MusicComposerAgent → MusicPlan`. Enregistre l'artifact `music_plan`. |
| `run_sound_design` | `async (scene: SceneSpec) -> SoundDesignPlan \| None` | Exécute `SoundDesignerAgent → SoundDesignPlan`. Enregistre l'artifact `sound_design_plan`. |
| `run_review` | `async (scene, render_output, audio_plan, composite_spec) -> Any` | Exécute `ReviewAgent → ReviewReport`. Enregistre l'artifact `review_report`. |
| `run_compositing` | `async (scene, render_output, audio_plan) -> CompositeSpec` | Exécute `CompositingAgent → FFmpegPlugin`. Génère le composite, puis fusionne via `merge_final_output`. |
| `merge_final_output` | `async (scene, render_output, audio_plan, workdir) -> None` | Fusionne vidéo + audio + sous-titres en un seul fichier `.mp4` via FFmpeg. Gère les volumes (ambiance 0.3, musique 0.5, voix 1.0), les sous-titres SRT, et le codec libx264/AAC. |
| `target_languages_for` | `(scene: SceneSpec) -> list[str]` | Détermine les langues cibles : `target_languages` > `spoken_languages` des personnages > `default_languages` du localization agent. |
| `run_localization` | `async (scene: SceneSpec) -> list[LanguagePackage]` | Exécute `LocalizationAgent → SubtitlePlugin/TTSPlugin` pour chaque langue cible en parallèle (`asyncio.gather`). |

**Détail de `merge_final_output`** :

1. Vérifie l'existence du fichier vidéo et des fichiers audio (ambiance, musique, voix).
2. Construit les filtres FFmpeg :
   - Volume : ambiance=0.3, musique=0.5, voix=1.0.
   - Mixage `amix` si >1 source audio.
   - Sous-titres SRT avec style forcé (taille 24, blanc, outline).
3. Encode en libx264 (CRF 23, preset medium) + AAC (128k).
4. Enregistre l'artifact `final_output`.
5. Tente le stockage et le knowledge graph (non bloquant).

**Détail de `run_localization`** :

Pour chaque langue cible :
1. Appelle `localization.plan_localization(scene, lang, languages=targets)` sous sémaphore LLM.
2. Génère les sous-titres via `SubtitlePlugin.generate()` si disponible.
3. Génère la voix via `TTSPlugin.generate()` si disponible.
4. Enregistre l'artifact `language_package`.

---

### 3.4 `events.py` — Journal d'événements

**Chemin** : `DeepBl4nder/production/events.py` (111 lignes)

**Description** : Journal persistant append-only (JSONL) et bus pub/sub mémoire. La fiabilité DeepBl4nder repose sur ce journal : chaque transition d'étape est persistée avant d'être appliquée.

#### Constantes

```python
STEP_EVENTS = ("step_started", "step_completed", "step_failed")
RUN_EVENTS = ("run_started", "run_completed", "run_blocked")
APPROVAL_EVENTS = ("approval_requested", "approval_granted", "approval_rejected")
```

##### `ProductionEvent` (dataclass, frozen)

**Description** : Un événement persisté du journal (rejeu et reprise).

| Champ | Type | Description |
|---|---|---|
| `seq` | `int` | Numéro de séquence (auto-incrémenté) |
| `kind` | `str` | Type d'événement (ex: `step_started`, `run_completed`) |
| `ts` | `float` | Timestamp Unix |
| `payload` | `dict[str, Any]` | Données associées (défaut: `{}`) |

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `to_json` | `() -> str` | Sérialise en JSON (clés triées). |

##### `EventLog` (dataclass)

**Description** : Journal append-only : chaque événement est flush avant retour.

| Champ | Type | Description |
|---|---|---|
| `path` | `Path` | Chemin du fichier JSONL |
| `_cached_last_seq` | `int \| None` | Cache du dernier numéro de séquence |

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `__post_init__` | `() -> None` | Crée le répertoire parent si nécessaire. |
| `append` | `(kind: str, payload: dict \| None) -> ProductionEvent` | Crée un événement avec seq incrémenté, l'écrit en JSONL avec flush, retourne l'événement. |
| `load` | `() -> list[ProductionEvent]` | Charge tous les événements depuis le fichier (une ligne = un JSON). |
| `_last_seq` | `() -> int` | Retourne le dernier numéro de séquence (cache ou calculé). |
| `last_seq` | `() -> int` | Interface publique de `_last_seq`. |

##### `EventBus` (classe)

**Description** : Bus pub/sub mémoire pour l'observabilité temps réel (SSE gateway).

**Constructeur** :

```python
def __init__(self) -> None
```
- Initialise `_subscribers: list[queue.Queue]` et `_lock: threading.Lock`.

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `subscribe` | `() -> queue.Queue[dict[str, Any]]` | Crée et retourne une `Queue` abonnée. Thread-safe. |
| `unsubscribe` | `(subscriber: queue.Queue) -> None` | Retire un abonné. Thread-safe. |
| `publish` | `(event: dict[str, Any]) -> None` | Publie un event dans toutes les queues. Thread-safe. |

---

### 3.5 `context.py` — Injection de contexte NOOA

**Chemin** : `DeepBl4nder/production/context.py` (192 lignes)

**Description** : Centralise la logique d'injection de variables de contexte (`run_history`, `revision_feedback`, etc.) dans les agents du pipeline. Utilisé en duck-typing : chaque agent peut exposer un attribut `context` (behaviour `__setitem__`).

##### `ContextInjector` (classe)

**Constructeur** :

```python
def __init__(
    self,
    agents: list[tuple[str, Any]],  # Liste de (nom, agent)
    event_log: Any,                  # EventLog
    workdir: Path,                   # Répertoire de travail
) -> None
```

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `_agents_with_context` | `() -> list[tuple[Any, Any]]` | Retourne les couples `(agent, context)` des agents ayant un attribut `context` non-None. |
| `_set_context` | `(context: Any, key: str, value: str) -> None` | Écrit une variable NOOA via `set_static` (si dispo), `set`, ou `__setitem__`. |
| `_format_feedback` | `(report: QAReport, revision: int) -> str` | Formate le feedback QA lisible : score, issues par kind/step, recommandations. |
| `inject_run_history` | `() -> None` | Injecte les 8 derniers événements du run comme `run_history` dans tous les agents. |
| `inject_revision_feedback` | `(target: str, report: QAReport, revision: int, agents_map: dict \| None) -> None` | Injecte le feedback QA formaté dans l'agent cible (`revision_feedback`). |
| `latest_revision_request` | `() -> dict[str, Any] \| None` | Lit le fichier `revision_request_*.json` le plus récent du workdir (HITL). |
| `inject_human_feedback` | `(target: str, comment: str, agents_map: dict \| None) -> None` | Injection HITL : comment humain → `revision_feedback` dans l'agent cible. |
| `consume_revision_requests` | `() -> None` | Marque les fichiers `revision_request_*.json` comme `.applied.json`. |

**Format du feedback QA** (`_format_feedback`) :

```markdown
### Révision N — QA échoué (score X.XX)
Issues à corriger :
- [issue_kind] (step) message
Recommandations :
- recommendation
```

**Format du feedback HITL** (`inject_human_feedback`) :

```markdown
### Révision humaine
Instructions du producteur :
<commentaire>
```

---

### 3.6 `budget.py` — Suivi budgétaire

**Chemin** : `DeepBl4nder/production/budget.py` (92 lignes)

**Description** : Suivi des coûts d'un run avec politique d'arrêt et alerte de dépassement (Roadmap C §19). L'alerte est émise à la transition budget franchi (temps réel < 30s).

##### `BudgetAlert` (dataclass, frozen)

**Description** : Émis quand le budget est franchi (une seule fois par dépassement).

| Champ | Type | Description |
|---|---|---|
| `run_id` | `str` | Identifiant du run |
| `budget` | `float` | Budget maximum |
| `total` | `float` | Total des coûts |
| `overshoot` | `float` | Dépassement (`total - budget`) |

##### `BudgetTracker` (dataclass)

**Description** : Suivi des coûts d'un run avec politique d'arrêt et alerte.

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `budget` | `float` | *(requis)* | Budget maximum |
| `llm` | `float` | `0.0` | Coûts LLM |
| `render` | `float` | `0.0` | Coûts de rendu |
| `storage` | `float` | `0.0` | Coûts de stockage |
| `external` | `float` | `0.0` | Coûts API externes |
| `run_id` | `str` | `""` | Identifiant du run |
| `_listeners` | `list[Callable]` | `[]` | Callbacks d'alerte (interne) |
| `_alerted` | `bool` | `False` | Flag anti-doublon d'alerte (interne) |

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `subscribe` | `(listener: Callable[[BudgetAlert], None]) -> None` | Abonne un listener aux alertes de dépassement. |
| `reset_alert` | `() -> None` | Réinitialise le flag `_alerted` (permet une nouvelle alerte). |
| `_charge` | `(cost: float) -> None` | Vérifie si le budget est dépassé et émet une `BudgetAlert` si première fois. |
| `add_llm` | `(cost: float) -> None` | Ajoute un coût LLM. |
| `add_render` | `(cost: float) -> None` | Ajoute un coût de rendu. |
| `add_storage` | `(cost: float) -> None` | Ajoute un coût de stockage. |
| `add_external` | `(cost: float) -> None` | Ajoute un coût externe. |
| `over_budget` | `() -> bool` | Retourne `True` si `total > budget`. |
| `report` | `() -> dict[str, float]` | Retourne le rapport complet : `llm`, `render`, `storage`, `external`, `total`, `budget`, `remaining`. |

**Propriétés** :

| Propriété | Type | Description |
|---|---|---|
| `total` | `float` | `llm + render + storage + external` |
| `remaining` | `float` | `max(0.0, budget - total)` |

---

### 3.7 `checkpoints.py` — Points de contrôle

**Chemin** : `DeepBl4nder/production/checkpoints.py` (248 lignes)

**Description** : Gestion des checkpoints de reprise du pipeline. Responsable de la persistance et de la lecture des étapes validées (brief fingerprint, chaîne de checkpoints, reprise depuis un run interrompu).

##### `_safe_name` (fonction utilitaire)

```python
def _safe_name(name: str) -> str
```
- Réduit un nom d'agent à un nom de fichier sûr (alphanumériques + `-_`).

##### `CheckpointManager` (classe)

**Constructeur** :

```python
def __init__(
    self,
    *,
    workdir: Path,                    # Répertoire de travail
    story: Any = None,                # StoryAgent
    storyboard: Any = None,           # StoryboardAgent
    animator: Any = None,             # AnimatorAgent
    write_json: Callable,             # Fonction d'écriture JSON
    production_run: ProductionRun,    # Run de production
    emit: Callable,                   # Fonction d'émission d'événements
    event_log: EventLog,              # Journal d'événements
) -> None
```

**Attributs internes** :

| Attribut | Type | Description |
|---|---|---|
| `_current_brief_sha` | `str \| None` | Empreinte SHA-256 du brief courant |

**Méthodes statiques** :

| Méthode | Signature | Description |
|---|---|---|
| `brief_fingerprint` | `(brief: Brief) -> str` | Empreinte SHA-256 du texte du brief. Changement → tous checkpoints invalidés. |
| `script_fingerprint` | `(code: str) -> str` | Empreinte SHA-256 du code généré. Lie rapports/rendus à leur script exact. |

**Méthodes de marquage** :

| Méthode | Signature | Description |
|---|---|---|
| `mark_checkpoint` | `(step: str) -> None` | Marque une étape fraîchement complétée comme « reprise possible » dans `run_state.json`. |
| `reuse_step` | `(name: str, payload: dict \| None) -> None` | Étape servie depuis un checkpoint : marquée complétée sans ré-exécution. Émet `step_resumed`. |

**Méthodes de lecture** :

| Méthode | Signature | Description |
|---|---|---|
| `_load_resume_state` | `() -> dict` | Charge `run_state.json` (brief_sha256 + steps). |
| `_read_checkpoint_file` | `(filename: str) -> Any \| None` | Lit et déserialise un fichier JSON du workdir. |
| `checkpoint_story` | `() -> StorySpec \| None` | Charge `story_spec.json`. |
| `checkpoint_storyboard` | `() -> StoryboardSpec \| None` | Charge `storyboard_spec.json`. |
| `checkpoint_scene` | `() -> SceneSpec \| None` | Charge `scene_spec.json` (vérifie `schema_version`). |
| `checkpoint_script` | `() -> tuple[BlenderScript, Path] \| None` | Charge les métadonnées `blender_script.json` + le fichier `script.py`. |
| `checkpoint_report` | `(script_code: str) -> QAReport \| None` | Charge `qa_report.json`. Valide que `passed == True` et que l'empreinte du script correspond. |
| `checkpoint_render` | `(script_code: str) -> RenderOutput \| None` | Charge `render_output.json`. Valide l'empreinte du script et l'existence du fichier vidéo. |

**Méthode de chaîne** :

| Méthode | Signature | Description |
|---|---|---|
| `load_checkpoints` | `(brief: Brief) -> dict[str, Any]` | Chaîne de checkpoints valides : s'arrête au premier maillon manquant. Clés : `story`, `storyboard`, `scene`, `script`, `report`, `render`. Les étapes upstream ne comptent que si l'agent correspondant est actif. |

---

### 3.8 `runs.py` — Runs de production

**Chemin** : `DeepBl4nder/production/runs.py` (163 lignes)

**Description** : Modèles `ProductionRun` et `ProductionStep` pour la corrélation production/agent, le suivi d'étapes et la reprise.

#### Type

```python
RunStatus = Literal["created", "planned", "running", "awaiting_approval",
                     "completed", "revision", "blocked"]
```

##### `ProductionStep` (dataclass)

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `name` | `str` | *(requis)* | Nom de l'étape |
| `status` | `str` | `"pending"` | Statut de l'étape |
| `agent_run_id` | `str` | `""` | ID du run agent associé |
| `artifact_id` | `str` | `""` | ID de l'artifact produit |
| `started_at` | `float` | `time.time()` | Timestamp de démarrage |

##### `ProductionRun` (dataclass)

**Description** : Un run de production, porteur de l'identité de corrélation (Roadmap C §7).

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `project_id` | `str` | *(requis)* | Identifiant projet |
| `id` | `str` | `uuid4().hex[:12]` | Identifiant unique du run |
| `status` | `RunStatus` | `"created"` | Statut du run |
| `steps` | `dict[str, ProductionStep]` | `{}` | Étapes du run indexées par nom |
| `correlation` | `dict[str, str]` | `{}` | Map de corrélation agent → run |
| `created_at` | `float` | `time.time()` | Timestamp de création |
| `log` | `EventLog \| None` | `None` | Journal d'événements |

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `add_step` | `(step: ProductionStep) -> ProductionStep` | Ajoute une étape au run. |
| `mark_step` | `(name: str, status: str) -> None` | Met à jour le statut d'une étape. |
| `start_step` | `(name: str) -> None` | Marque l'étape `running`, log `step_started`. |
| `complete_step` | `(name: str) -> None` | Marque l'étape `completed`, log `step_completed`, affiche la durée. |
| `fail_step` | `(name: str) -> None` | Marque l'étape `failed`, log `step_failed`. |
| `request_approval` | `(name: str) -> None` | HITL : bloque l'étape en attente, met le run en `awaiting_approval`. |
| `approve` | `(name: str) -> None` | Accorde l'approbation, remet le run en `running`. |
| `reject` | `(name: str, reason: str) -> None` | Rejette l'approbation, met le run en `revision`. |
| `step` | `(name: str) -> ProductionStep \| None` | Retourne l'étape par nom. |
| `pending_steps` | `() -> list[str]` | Liste des étapes en statut `pending`. |
| `recover` | `@classmethod (project_id, log) -> ProductionRun` | Reconstruit un run depuis le journal (rejeu des événements non consommés). |
| `snapshot` | `() -> dict[str, object]` | Point de reprise minimal (id, project_id, status, correlation, steps). |

**Logique de `recover()`** :

1. Crée un nouveau `ProductionRun`.
2. Parcourt tous les événements du journal.
3. Pour chaque `step_started` sans `step_completed`/`step_failed` correspondant → status `pending`.
4. Pour chaque `approval_requested` sans `approval_granted`/`approval_rejected` → `awaiting_approval`.
5. Détermine le statut final du run.

---

### 3.9 `rendering.py` — Gestion du rendu

**Chemin** : `DeepBl4nder/production/rendering.py` (377 lignes)

**Description** : Extrait de `runner.py` pour isoler la logique de rendu (single-shot, parallel-shots, fusion ffmpeg) dans une classe testable.

##### `RenderManager` (classe)

**Hérite de** : `PluginShortcuts`

**Constructeur** :

```python
def __init__(
    self,
    *,
    blender_bridge: Any,                  # Bridge d'exécution Blender
    blender: Any,                         # BlenderAgent
    workdir: Path,                        # Répertoire de travail
    artifacts: ArtifactRegistry,          # Registre d'artifacts
    provenance: ProvenanceGraph,          # Graphe de provenance
    production_run: ProductionRun,        # Run de production
    event_log: EventLog,                  # Journal d'événements
    plugins: PluginRegistry,              # Registre de plugins
    emit: Callable,                       # Hook d'émission
    charge: Callable,                     # Fonction de facturation
    max_render_retries: int = 2,          # Max retries
    gpu_semaphore: asyncio.Semaphore | None = None,  # Sémaphore GPU
    write_json: Callable,                 # Écriture JSON
    mark_checkpoint: Callable,            # Marquage checkpoint
    get_director_art: Callable,           # Récupération artifact director
) -> None
```

**Méthodes** :

| Méthode | Signature | Description |
|---|---|---|
| `run_render` | `async (scene: SceneSpec, script: BlenderScript) -> RenderOutput \| None` | Exécute le script Blender via la bridge, produit une vidéo. Boucle de self-repair avec `max_render_retries`. |
| `run_render_parallel_shots` | `async (scene: SceneSpec, script: BlenderScript) -> RenderOutput \| None` | Rend chaque plan en parallèle (sémaphore GPU), fusionne les résultats. |
| `merge_shot_videos` | `async (outputs: list[RenderOutput], base_name: str) -> Path \| None` | Fusionne plusieurs vidéos avec ffmpeg concat. |

**Détail de `run_render`** :

1. Vérifie la disponibilité de la `blender_bridge`.
2. Snapshot le workdir pour détecter les nouveaux fichiers.
3. Boucle d'exécution :
   - Appelle `blender_bridge.run_script(script, workdir)`.
   - Détecte les nouveaux fichiers média (`.mp4`, `.png`, `.exr`, etc.).
   - Si aucun fichier → `RuntimeError`.
   - Sinon, crée `RenderOutput` avec les métadonnées de la scène.
   - Écrit le checkpoint `render_output.json`.
   - Enregistre l'artifact `render_output`.
   - Tente le stockage et le knowledge graph.
4. En cas d'échec : demande `blender_agent.refine_script()` puis réessaie.

**Détail de `run_render_parallel_shots`** :

1. Crée une `SceneSpec` par plan.
2. Pour chaque plan, génère un script via `blender.build_script()`, valide l'AST, exécute via bridge.
3. Limite la concurrence via `_gpu_semaphore`.
4. Fusionne les vidéos valides avec `merge_shot_videos` (ffmpeg concat).
5. Crée un `RenderOutput` fusionné avec durée totale.

---

### 3.10 `plugins.py` — Raccourcis plugins

**Chemin** : `DeepBl4nder/production/plugins.py` (45 lignes)

**Description** : Mixin pour les raccourcis d'accès aux plugins par nom depuis un `PluginRegistry`.

##### `PluginShortcuts` (classe)

**Description** : Fournit des propriétés en accès rapide aux plugins enregistrés. Attend que `self.plugins` soit un `PluginRegistry` avec une méthode `.get(name)`.

**Propriétés** :

| Propriété | Type | Nom du plugin |
|---|---|---|
| `audio_plugin` | `Any` | `"audio"` |
| `ffmpeg_plugin` | `Any` | `"ffmpeg"` |
| `subtitle_plugin` | `Any` | `"subtitle"` |
| `tts_plugin` | `Any` | `"tts"` |
| `blender_plugin` | `Any` | `"blender"` |
| `storage_plugin` | `Any` | `"storage"` |
| `git_plugin` | `Any` | `"git"` |
| `knowledge_graph_plugin` | `Any` | `"knowledge-graph"` |
| `asset_library_plugin` | `Any` | `"asset-library"` |

**Utilisé par** : `PipelineRunner`, `PostProductionRunner`, `RenderManager`.

---

### 3.11 `fallbacks.py` — Fallbacks déterministes

**Chemin** : `DeepBl4nder/production/fallbacks.py` (254 lignes)

**Description** : Fallbacks déterministes pour les étapes Storyboard et Blender. Ces fonctions produisent des sorties structurellement valides quand les générations LLM échouent deux fois de suite. Elles n'utilisent que des types du domaine.

#### Constantes

```python
_SHOT_ANGLE_CYCLE = ("wide", "medium", "closeup")
_MAX_SYNTH_SHOTS = 12
```

##### `synthesize_storyboard` (fonction)

```python
def synthesize_storyboard(story_spec: StorySpec) -> StoryboardSpec
```

**Description** : Filet ultime du storyboard : un plan par beat de l'histoire.

**Logique** :
1. Parcourt `story_spec.acts[].beats[]`.
2. Pour chaque beat avec description non vide :
   - Extrait la description, la durée (bornée entre 2s et 12s), l'angle de caméra cyclique (`wide/medium/closeup`), les personnages.
   - Crée un `StoryboardShot`.
3. Limite à `_MAX_SYNTH_SHOTS` (12) plans.
4. Si aucun beat : crée un plan d'exposition unique depuis le `synopsis` ou `logline`.
5. Retourne un `StoryboardSpec` avec `total_duration` calculé.

##### `synthesize_blender_script` (fonction)

```python
def synthesize_blender_script(scene: SceneSpec, workdir: Path) -> BlenderScript
```

**Description** : Filet ultime de l'étape blender : script bpy déterministe.

**Logique** :
1. Calcule les paramètres : fps, résolution, frames totales, chemin de sortie absolu.
2. Détermine la couleur de monde selon `lighting_mood` (sombre/neutral/jour).
3. Génère un script bpy comportant :
   - `read_factory_settings(use_empty=True)`.
   - Configuration de la résolution et des frames.
   - Sol (plane size 40).
   - Éclairage : `SUN` + `AREA` + `Background` world.
   - Volumétrie si `env.rain` (scatter density 0.08).
   - Repères personnages (cubes positionnés en cercle).
   - Caméra animée avec keyframes interpolés sur la durée totale.
   - Moteur EEVEE (fallback Cycles 32 samples).
   - Rendu en FFmpeg H264/MPEG4.
   - Appel `bpy.ops.render.render(animation=True)`.
4. Nom de scène : `scene_synthetisee_<slug>`.
5. Retourne un `BlenderScript` avec le code généré.

---

## 4. Dépendances inter-modules

### Imports externes au package `production/`

| Module source | Symboles utilisés |
|---|---|
| `DeepBl4nder.agents.base` | `GenerationError` |
| `DeepBl4nder.artifacts.provenance` | `ProvenanceGraph` |
| `DeepBl4nder.artifacts.registry` | `Artifact`, `ArtifactRegistry` |
| `DeepBl4nder.codegen.validator` | `ValidationReport`, `validate_for_worker` |
| `DeepBl4nder.domain.patch` | `Patch`, `apply_patches` |
| `DeepBl4nder.domain.project` | `Brief` |
| `DeepBl4nder.domain.qa` | `Issue`, `IssueKind`, `QAReport`, `RevisionSpec` |
| `DeepBl4nder.domain.scene` | `BlenderScript`, `SceneSpec`, `RenderOutput`, `ShotSpec`, `ENGINE_BLENDER`, `ENGINE_UE5`, `ENGINE_GODOT`, `ENGINE_AI_VIDEO` |
| `DeepBl4nder.domain.ue5` | `UE5Commands`, `UE5Command` |
| `DeepBl4nder.domain.godot` | `GodotCommands`, `GodotCommand` |
| `DeepBl4nder.domain.ai_video` | `AIVideoCommands`, `AIVideoCommand` |
| `DeepBl4nder.domain.media` | `AudioPlan`, `AudioMaster`, `CompositeSpec`, `LanguagePackage`, `MusicPlan`, `SoundDesignPlan` |
| `DeepBl4nder.domain.narrative` | `StorySpec`, `StoryboardSpec`, `StoryboardShot` |
| `DeepBl4nder.plugins.registry` | `PluginRegistry` |
| `DeepBl4nder.qa.visual` | `assess_render`, `visual_qa_to_report` |

### Dépendances interne du package `production/`

```
runner.py ─────────┬──▶ events.py (EventLog, ProductionEvent)
                   ├──▶ context.py (ContextInjector)
                   ├──▶ budget.py (BudgetTracker)
                   ├──▶ checkpoints.py (CheckpointManager)
                   ├──▶ rendering.py (RenderManager)
                   ├──▶ postprod.py (PostProductionRunner)
                   ├──▶ plugins.py (PluginShortcuts)
                   ├──▶ runs.py (ProductionRun, ProductionStep)
                    ├──▶ fallbacks.py (synthesize_blender_script, synthesize_storyboard)
                    └──▶ (mêmes dépendances artifacts/provenance que runner.py)

postprod.py ──────┬──▶ events.py (EventLog)
                   ├──▶ plugins.py (PluginShortcuts)
                   ├──▶ runs.py (ProductionRun)
                   └──▶ (mêmes dépendances artifacts/provenance que runner.py)

rendering.py ─────┬──▶ events.py (EventLog)
                   ├──▶ checkpoints.py (CheckpointManager)
                   ├──▶ plugins.py (PluginShortcuts)
                   └──▶ runs.py (ProductionRun)

checkpoints.py ───┬──▶ events.py (EventLog)
                   └──▶ runs.py (ProductionRun)

context.py ───────└──▶ domain.qa (QAReport)

events.py ────────└── (aucune dépendance production interne)

budget.py ────────└── (aucune dépendance production interne)

runs.py ──────────└──▶ events.py (EventLog, STEP_EVENTS, APPROVAL_EVENTS)

plugins.py ───────└── (aucune dépendance)

fallbacks.py ─────└──▶ domain.scene, domain.narrative
```

---

## 5. Constantes et configurations

### Variables d'environnement

| Variable | Valeur par défaut | Description |
|---|---|---|
| `DeepBl4nder_AUTO_APPROVE` | `"0"` | Si `"1"`, le HITL approval gate est contourné automatiquement. |

### Paramètres par défaut du `PipelineRunner`

| Paramètre | Défaut | Description |
|---|---|---|
| `max_revisions` | `1` | Nombre maximum de boucles de révision QA. |
| `max_render_retries` | `2` | Nombre maximum de retries en cas d'échec de rendu. |
| `max_parallel_shots` | `4` | Nombre maximum de plans rendus en parallèle. |
| `max_parallel_llm` | `2` | Nombre maximum d'appels LLM simultanés. |
| `enable_cache` | `True` | Cache LLM in-memory activé. |
| `enable_parallel_shots` | `True` | Rendu parallèle des plans activé. |
| `_cache_ttl` | `3600` (1h) | Durée de vie du cache LLM. |

### Fichiers du workdir

| Fichier | Format | Description |
|---|---|---|
| `events.jsonl` | JSONL | Journal d'événements append-only. |
| `run_state.json` | JSON | État de reprise : `{brief_sha256, steps[]}`. |
| `story_spec.json` | JSON | StorySpec sérialisée. |
| `storyboard_spec.json` | JSON | StoryboardSpec sérialisée. |
| `scene_spec.json` | JSON | SceneSpec sérialisée. |
| `blender_script.json` | JSON | Métadonnées du script : `{scene_name, version, code_sha256}`. |
| `<scene_name>/script.py` | Python | Script Blender généré. |
| `qa_report.json` | JSON | Rapport QA : `{script_sha256, passed, score, issues[], recommendations[]}`. |
| `render_output.json` | JSON | Métadonnées rendu : `{script_sha256, render_output}`. |
| `ue5_commands.json` | JSON | Commandes UE5 sérialisées. |
| `revision_<N>_<target>.json` | JSON | RevisionSpec pour la révision N. |
| `revision_request_<ts>.json` | JSON | Demande de révision humaine (HITL). |
| `audio_plan.json` | JSON | Plan audio sérialisé. |
| `music_plan.json` | JSON | Plan musique sérialisé. |
| `sound_design_plan.json` | JSON | Plan sound design sérialisé. |
| `composite_spec.json` | JSON | Spécification de compositing sérialisée. |
| `review_report.json` | JSON | Rapport de review finale. |
| `character_design.json` | JSON | Résultat du character design. |
| `environment_design.json` | JSON | Résultat de l'environnement. |
| `animation.json` | JSON | Résultat de l'animation. |
| `language_package_<lang>.json` | JSON | Package de localisation par langue. |
| `render/` | Dossier | Fichiers de rendu (vidéos, images). |
| `audio/` | Dossier | Fichiers audio (ambiance.wav, music.wav, master.wav). |
| `compositing/` | Dossier | Fichiers de compositing. |
| `localization/<lang>/` | Dossier | Sous-titres (SRT) et voix (WAV) par langue. |

### Codes d'événements émis

| Événement | Moment | Données |
|---|---|---|
| `run_started` | Début du run | `{project_id}` |
| `run_completed` | Fin du run | `{}` |
| `run_blocked` | Run bloqué | `{step?, reason?}` |
| `step_started` | Début d'étape | `{step}` |
| `step_completed` | Fin d'étape | `{step}` |
| `step_failed` | Échec d'étape | `{step}` |
| `step_resumed` | Étape reprise depuis checkpoint | `{step, ...}` |
| `step_retry` | Retry de rendu | `{step, attempt}` |
| `llm_call` | Appel LLM | `{step, agent, status, elapsed_s?, model?, ...}` |
| `llm_retry` | Retry après GenerationError | `{step}` |
| `cache_hit` | Cache LLM utilisé | `{key, agent, method}` |
| `cost_recorded` | Coût enregistré | `{step, cost}` |
| `revision_requested` | Révision QA demandée | `{target_step, revision, artifact_id}` |
| `resume_ready` | Reprise disponible | `{steps[]}` |
| `resume_invalidated` | Étapes invalidées | `{from_step}` |
| `patches_applied` | Patches API appliqués | `{count, targets[]}` |
| `approval_requested` | HITL approval demandée | `{step, reason}` |
| `approval_granted` | HITL approval accordée | `{step, auto?}` |
| `approval_required` | HITL requis | `{production_id, step}` |
| `render_skipped` | Rendu ignoré | `{reason}` |
| `render_retry` | Retry rendu | `{attempt, max}` |
| `render_failed` | Rendu échoué | `{error, attempts}` |
| `storyboard_synthesized` | Fallback storyboard | `{shots, reason}` |
| `blender_script_synthesized` | Fallback script | `{scene_name, reason}` |
| `ue5_commands_synthesized` | Fallback UE5 | `{scene, reason}` |
| `ue5_command_failed` | Commande UE5 échouée | `{endpoint, error}` |
| `godot_commands_synthesized` | Fallback Godot | `{scene, reason}` |
| `godot_command_failed` | Commande Godot échouée | `{endpoint, error}` |
| `ai_video_commands_synthesized` | Fallback AI Video | `{scene, reason}` |
| `ai_video_command_failed` | Commande AI Video échouée | `{endpoint, error}` |
| `merge_failed` | Fusion FFmpeg échouée | `{error}` |
| `scene_inspected` | Scène inspectée | `{objects}` |

