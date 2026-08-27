# Documentation Python — DeepBl4nder (Core)

> **Version du projet :** `0.2.0`
> **Couverture :** Tous les modules Python du package `deepblender/` à l'exclusion de `plugins/` et `production/`.

---

## Table des matières

1. [Modules racines](#1-modules-racines)
   - 1.1 [`deepblender/__init__.py`](#11-deepblender__init__py)
   - 1.2 [`deepblender/cli.py`](#12-deepblenderclipy)
   - 1.3 [`deepblender/llm.py`](#13-deepblenderllmpy)
   - 1.4 [`deepblender/logging_setup.py`](#14-deepblenderlogging_setuppy)
   - 1.5 [`deepblender/nooa_compat.py`](#15-deepblendernooa_compatpy)
2. [Agents](#2-agents)
   - 2.1 [`agents/__init__.py`](#21-agents__init__py)
   - 2.2 [`agents/base.py`](#22-agentsbasepy)
   - 2.3 [`agents/story.py`](#23-agentsstorypy)
   - 2.4 [`agents/board.py`](#24-agentsboardpy)
   - 2.5 [`agents/director.py`](#25-agentsdirectorpy)
   - 2.6 [`agents/blender.py`](#26-agentsblenderpy)
   - 2.7 [`agents/char.py`](#27-agentscharpy)
   - 2.8 [`agents/env.py`](#28-agentsenvpy)
   - 2.9 [`agents/animator.py`](#29-agentsanimatorpy)
   - 2.10 [`agents/audio.py`](#210-agentsaudiopy)
   - 2.11 [`agents/comp.py`](#211-agentscomppy)
   - 2.12 [`agents/loc.py`](#212-agentslocpy)
   - 2.13 [`agents/music.py`](#213-agentsmusicpy)
   - 2.14 [`agents/sfx.py`](#214-agentssfxpy)
   - 2.15 [`agents/qa.py`](#215-agentsqapy)
   - 2.16 [`agents/review.py`](#216-agentsreviewpy)
   - 2.17 [`agents/ue5.py`](#217-agentsue5py)
3. [Domaine (domain/)](#3-domaine)
   - 3.1 [`domain/__init__.py`](#31-domain__init__py)
   - 3.2 [`domain/scene.py`](#32-domainscenepy)
   - 3.3 [`domain/narrative.py`](#33-domainnarrativepy)
   - 3.4 [`domain/media.py`](#34-domainmediapy)
   - 3.5 [`domain/qa.py`](#35-domainqapy)
   - 3.6 [`domain/project.py`](#36-domainprojectpy)
   - 3.7 [`domain/patch.py`](#37-domainpatchpy)
   - 3.8 [`domain/asset.py`](#38-domainassetpy)
   - 3.9 [`domain/ue5.py`](#39-domainue5py)
   - 3.10 [`domain/utils.py`](#310-domainutilspy)
4. [API (api/)](#4-api)
   - 4.1 [`api/__init__.py`](#41-api__init__py)
   - 4.2 [`api/app.py`](#42-apiapppy)
   - 4.3 [`api/bus.py`](#43-apibuspy)
   - 4.4 [`api/db.py`](#44-apidbpy)
   - 4.5 [`api/deps.py`](#45-apidepspy)
   - 4.6 [`api/models.py`](#46-apimodelspy)
   - 4.7 [`api/pipeline.py`](#47-apipipelinepy)
   - 4.8 [`api/schemas.py`](#48-apischemaspy)
   - 4.9 [`api/security.py`](#49-apisecuritypy)
   - 4.10 [`api/seed.py`](#410-apiseedpy)
   - 4.11 [`api/state.py`](#411-apistatepy)
5. [Bridge (bridge/)](#5-bridge)
   - 5.1 [`bridge/__init__.py`](#51-bridge__init__py)
   - 5.2 [`bridge/worker.py`](#52-bridgeworkerpy)
6. [Bridges (bridges/)](#6-bridges)
   - 6.1 [`bridges/blender/bridge.py`](#61-bridgesblenderbridgepy)
   - 6.2 [`bridges/blender/scheduler.py`](#62-bridgesblenderschedulerpy)
   - 6.3 [`bridges/blender/worker.py`](#63-bridgesblenderworkerpy)
   - 6.4 [`bridges/ue5/bridge.py`](#64-bridgesue5bridgepy)
7. [Codegen (codegen/)](#7-codegen)
   - 7.1 [`codegen/__init__.py`](#71-codegen__init__py)
   - 7.2 [`codegen/policy.py`](#72-codegenpolicypy)
   - 7.3 [`codegen/validator.py`](#73-codegenvalidatorpy)
8. [Skills (skills/)](#8-skills)
   - 8.1 [`skills/registry.py`](#81-skillsregistrypy)
9. [QA (qa/)](#9-qa)
   - 9.1 [`qa/visual.py`](#91-qavisualpy)
10. [Assets (assets/)](#10-assets)
    - 10.1 [`assets/characters.py`](#101-assetscharacterspy)
    - 10.2 [`assets/polyhaven.py`](#102-assetspolyhavenpy)

---

## 1. Modules racines

### 1.1 `deepblender/__init__.py`

Module racine du package. Effectue l'initialisation globale au moment de l'import.

**Constantes :**

| Nom | Type | Valeur | Description |
|-----|------|--------|-------------|
| `__version__` | `str` | `"0.2.0"` | Version du projet DeepBl4nder |

**Fonctions privées :**

#### `_install_windows_shims()`

```python
def _install_windows_shims() -> None
```

**Description :** Installe des correctifs de compatibilité pour Windows. Place des shims dans le répertoire temporaire du système pour permettre l'exécution de scripts Blender et d'autres binaires sous Windows.

---

#### `_install_utf8_stdio()`

```python
def _install_utf8_stdio() -> None
```

**Description :** Force les flux d'entrée/sortie standard à utiliser UTF-8 sur les plateformes Windows où l'encodage par défaut n'est pas UTF-8. Évite les erreurs d'encodage lors de l'échange de données JSON entre processus.

---

**Comportement au chargement :**

Lorsque `deepblender` est importé, le module :
1. Charge les variables d'environnement depuis `.env` via `dotenv` (`load_dotenv(override=False)`)
2. Appelle `_install_windows_shims()` si la plateforme est Windows
3. Appelle `_install_utf8_stdio()`

---

### 1.2 `deepblender/cli.py`

Interface en ligne de commande (CLI) pour DeepBl4nder. Fournit des sous-commandes pour l'inspection, la validation, le service API et le seeding de la base de données.

**Imports principaux :**

- `deepblender.codegen.validator.ASTValidator`
- `deepblender.codegen.policy.CodePolicy`
- `deepblender.skills.registry.get_default_registry`
- `deepblender.api.seed.main` (seed_command)
- `deepblender.api.state`

**Constantes :**

| Nom | Description |
|-----|-------------|
| `_CONFIG_DEFAULT` | Chemin par défaut vers un fichier de configuration YAML |

**Fonctions :**

#### `build_parser()`

```python
def build_parser() -> argparse.ArgumentParser
```

**Description :** Construit et retourne l'analyseur d'arguments principal (`argparse.ArgumentParser`). Configure les sous-commandes et leurs arguments.

**Valeur de retour :** `argparse.ArgumentParser` — l'analyseur configuré avec toutes les sous-commandes.

---

#### `main()`

```python
def main(argv: list[str] | None = None) -> None
```

**Description :** Point d'entrée principal de la CLI. Parse les arguments, charge la configuration, initialise le registre des plugins et des skills, puis dispatche vers la sous-commande appropriée.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `argv` | `list[str] \| None` | Arguments de ligne de commande (None = `sys.argv[1:]`) |

**Comportement :**

- Détermine le niveau de verbosité via `--verbose` / `-v`
- Charge la configuration depuis `--config` ou `_CONFIG_DEFAULT`
- Initialise le `PluginRegistry` et le `ToolRegistry`
- Initialise le `SkillRegistry` via `get_default_registry()`
- Dispatche vers : `inspect`, `validate`, `serve`, ou `seed`

**Sous-commandes supportées :**

| Sous-commande | Description |
|---------------|-------------|
| `inspect` | Inspecte un fichier AST et affiche les informations de validation |
| `validate` | Valide un fichier AST contre les politiques de code |
| `serve` | Démarre le serveur API FastAPI |
| `seed` | Initialise la base de données avec les données par défaut |

---

### 1.3 `deepblender/llm.py`

Module de gestion des fournisseurs LLM, du routage intelligent et de la découverte dynamique de modèles. Constitue le cœur du système de résolution de modèles pour les agents.

**Imports :** `random`, `logging`, `time`, `httpx`, `openai`, `dataclasses`

**Constantes :**

#### `_HTTP_TIMEOUT`

```python
_HTTP_TIMEOUT: float = 10.0
```

**Description :** Timeout en secondes pour les requêtes HTTP de découverte de modèles.

---

#### `_MAX_DISCOVERY`

```python
_MAX_DISCOVERY: int = 6
```

**Description :** Nombre maximum de modèles à récupérer lors de la découverte dynamique par endpoint.

---

#### `PROVIDERS`

```python
PROVIDERS: dict[str, LLMProvider] = { ... }
```

**Description :** Dictionnaire global des fournisseurs LLM préconfigurés. Les clés sont les identifiants de fournisseur (ex: `"openai"`, `"deepseek"`, `"zai"`, etc.) et les valeurs sont des instances `LLMProvider`.

**Fournisseurs typiques :**

| Clé | Type | Description |
|-----|------|-------------|
| `"openai"` | `LLMProvider` | OpenAI (GPT-4o, etc.) |
| `"deepseek"` | `LLMProvider` | DeepSeek (compatible OpenAI) |
| `"zai"` | `LLMProvider` | ZAI (compatible OpenAI) |
| `"anthropic"` | `LLMProvider` | Anthropic (Claude) |
| `"mistral"` | `LLMProvider` | Mistral AI |
| `"groq"` | `LLMProvider` | Groq (compatible OpenAI) |

---

#### `MODEL_SELECTION_RULES`

```python
MODEL_SELECTION_RULES: dict[str, dict[str, str]] = { ... }
```

**Description :** Règles de sélection de modèle par tâche. Associe des catégories de tâches (ex: `"code"`, `"vision"`, `"reasoning"`) à des préférences de modèle par fournisseur.

---

**Classes :**

### `LLMProvider`

```python
@dataclasses.dataclass
class LLMProvider:
    name: str
    base_url: str
    api_key_env: str
    models: list[str] = dataclasses.field(default_factory=list)
    cooldown_until: float = 0.0
```

**Description :** Représente un fournisseur de modèle de langage. Stocke la configuration de connexion, la clé API (via variable d'environnement), les modèles disponibles et un mécanisme de cooldown en cas d'échec.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `name` | `str` | Nom du fournisseur |
| `base_url` | `str` | URL de base de l'API (compatible OpenAI) |
| `api_key_env` | `str` | Nom de la variable d'environnement contenant la clé API |
| `models` | `list[str]` | Liste des modèles disponibles (peut être vide, découverts dynamiquement) |
| `cooldown_until` | `float` | Timestamp Unix jusqu'auquel le fournisseur est en cooldown (0 = actif) |

**Méthodes :**

#### `key()`

```python
def key(self) -> str | None
```

**Description :** Récupère la clé API depuis la variable d'environnement.

**Valeur de retour :** `str | None` — la clé API ou `None` si la variable d'environnement n'est pas définie.

---

#### `available()`

```python
def available(self) -> bool
```

**Description :** Vérifie si le fournisseur est disponible (clé API présente et pas en cooldown).

**Valeur de retour :** `bool` — `True` si le fournisseur est utilisable.

---

#### `discover_models()`

```python
def discover_models(self) -> list[str]
```

**Description :** Découvre dynamiquement les modèles disponibles auprès du fournisseur en interrogeant l'endpoint `/v1/models`. Met à jour l'attribut `models` en place.

**Valeur de retour :** `list[str]` — la liste des identifiants de modèles découverts.

**Effets de bord :** Met à jour `self.models` avec les modèles découverts.

---

### `LLMRouter`

```python
@dataclasses.dataclass
class LLMRouter:
    fallback_models: list[str]
    providers: dict[str, LLMProvider]
    mode: str = "fallback"
    _cooldowns: dict[str, float] = dataclasses.field(default_factory=dict)
```

**Description :** Routeur intelligent pour les appels LLM. Supporte deux modes de fonctionnement : fallback (essaie les modèles un par un) et vote (soumet à plusieurs modèles et retourne le meilleur résultat).

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `fallback_models` | `list[str]` | Ordre de priorité des modèles en mode fallback |
| `providers` | `dict[str, LLMProvider]` | Fournisseurs disponibles |
| `mode` | `str` | Mode de routage : `"fallback"` ou `"vote"` |
| `_cooldowns` | `dict[str, float]` | Timestamps de cooldown par modèle (stocke en interne) |

**Méthodes :**

#### `pick()`

```python
def pick(self, task_hint: str = "") -> tuple[LLMProvider, str] | None
```

**Description :** Sélectionne le meilleur fournisseur et modèle disponibles en se basant sur le mode de routage et les indices de tâche.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `task_hint` | `str` | Indice sur le type de tâche (ex: `"code"`, `"vision"`) pour guider la sélection |

**Valeur de retour :** `tuple[LLMProvider, str] | None` — un tuple `(fournisseur, nom_du_modèle)` ou `None` si aucun modèle n'est disponible.

---

#### `record_failure()`

```python
def record_failure(self, provider_name: str, model: str, cooldown: float = 60.0) -> None
```

**Description :** Enregistre un échec pour un modèle spécifique et active un cooldown proportionnel.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Nom du fournisseur |
| `model` | `str` | Identifiant du modèle |
| `cooldown` | `float` | Durée du cooldown en secondes (défaut : 60.0) |

---

#### `record_success()`

```python
def record_success(self, provider_name: str, model: str) -> None
```

**Description :** Enregistre un succès et supprime tout cooldown actif pour le modèle.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `provider_name` | `str` | Nom du fournisseur |
| `model` | `str` | Identifiant du modèle |

---

**Fonctions module-level :**

#### `model_name_of()`

```python
def model_name_of(router: LLMRouter, task_hint: str = "") -> str | None
```

**Description :** Retourne uniquement le nom du modèle sélectionné par le routeur.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `router` | `LLMRouter` | Instance du routeur |
| `task_hint` | `str` | Indice de tâche |

**Valeur de retour :** `str | None` — le nom du modèle ou `None`.

---

#### `build_llm()`

```python
def build_llm(provider: LLMProvider, model: str) -> openai.OpenAI | openai.AzureOpenAI | None
```

**Description :** Construit un client OpenAI compatible pour le fournisseur et modèle donnés. Gère les cas spéciaux (Anthropic, Azure, etc.).

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `provider` | `LLMProvider` | Le fournisseur LLM |
| `model` | `str` | L'identifiant du modèle |

**Valeur de retour :** `openai.OpenAI | openai.AzureOpenAI | None` — un client LLM utilisable ou `None`.

---

#### `get_router()`

```python
def get_router() -> LLMRouter
```

**Description :** Factory singleton qui retourne une instance de `LLMRouter` initialisée avec les fournisseurs et modèles disponibles. Découvre les modèles pour les fournisseurs qui n'en ont pas.

**Valeur de retour :** `LLMRouter` — le routeur global.

---

### 1.4 `deepblender/logging_setup.py`

Module de configuration du système de logging.

**Constantes :**

#### `LOG_FORMAT`

```python
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
```

**Description :** Format de chaîne pour les messages de log.

---

**Fonctions :**

#### `log_file_path()`

```python
def log_file_path() -> Path
```

**Description :** Retourne le chemin du fichier de log principal.

**Chemin retourné :** `<DeepBl4nder_DATA_DIR>/logs/deepblender.log`

**Valeur de retour :** `Path` — chemin absolu vers le fichier de log.

---

#### `setup_logging()`

```python
def setup_logging(level: int = logging.INFO) -> None
```

**Description :** Configure le système de logging pour tout le projet. Installe deux handlers :
- **Console** : affiche les messages au niveau spécifié (format court)
- **Fichier rotatif** : écrit dans le fichier de log avec rotation (10 Mo max, 5 fichiers de backup)

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `level` | `int` | Niveau de logging (défaut : `logging.INFO`) |

**Effets de bord :**
- Crée le répertoire `logs/` si nécessaire
- Configure le logger racine de Python
- Ajoute un `RotatingFileHandler` avec maxBytes=10_000_000, backupCount=5

---

### 1.5 `deepblender/nooa_compat.py`

Module de compatibilité avec le framework NOOA. Contient un monkeypatch pour corriger des problèmes d'enveloppe de réponse provenant de fournisseurs LLM non standard.

**Fonctions :**

#### `install()`

```python
def install() -> None
```

**Description :** Installe un monkeypatch sur `CodeActStrategy._handle_return_result` du framework NOOA. Le patch effectue deux correctifs :

1. **Dés-enveloppage** : Certains LLMs retournent des résultats enveloppés dans des structures non standard (ex: `{ "content": { "output": "..." } }`). Le monkeypatch détecte et déplie ces enveloppes.

2. **Réparation des champs cosmétiques vides** : Si des champs comme `StorySpec.logline` sont vides ou None, le monkeypatch les régénère à partir du contenu principal.

**Effets de bord :** Modifie le comportement global de `CodeActStrategy` du framework NOOA.

---

## 2. Agents

### 2.1 `agents/__init__.py`

Module d'export centralisé pour tous les agents du projet.

**Exports :**

| Classe | Module source |
|--------|---------------|
| `StoryAgent` | `agents.story` |
| `StoryboardAgent` | `agents.board` |
| `DirectorAgent` | `agents.director` |
| `BlenderAgent` | `agents.blender` |
| `CharacterDesignerAgent` | `agents.char` |
| `EnvironmentArtistAgent` | `agents.env` |
| `AnimatorAgent` | `agents.animator` |
| `AudioAgent` | `agents.audio` |
| `CompositingAgent` | `agents.comp` |
| `LocalizationAgent` | `agents.loc` |
| `MusicComposerAgent` | `agents.music` |
| `SoundDesignerAgent` | `agents.sfx` |
| `QAAgent` | `agents.qa` |
| `ReviewAgent` | `agents.review` |
| `UE5Agent` | `agents.ue5` |

---

### 2.2 `agents/base.py`

Module de base pour tous les agents. Définit la classe abstraite `BaseAgent`, le mixin `DefaultsMixin`, les fonctions de postcondition et les helpers pour l'exécution sandbox.

**Imports :**

- `nooa.agents.CodeActStrategy` / `PredictStrategy` / `ReflexionStrategy` / `CodeActLiteStrategy`
- `nooa.agents.Strategy` (type)
- `deepblender.domain` (tous les types de domaine)
- `deepblender.codegen.validator.validate_for_worker`
- `deepblender.logging_setup.setup_logging`

**Classes :**

### `BaseAgent`

```python
class BaseAgent(nooa.Agent):
    def __init__(self, **kwargs):
        ...
```

**Description :** Classe de base abstraite pour tous les agents DeepBl4nder. Hérite de `nooa.Agent` et ajoute des fonctionnalités communes : configuration du logging, activation du sandbox, et typage des stratégies.

**Attributs hérités de `nooa.Agent` :**

| Attribut | Type | Description |
|----------|------|-------------|
| `name` | `str` | Nom de l'agent |
| `agent_config` | `dict` | Configuration de l'agent |
| `skill_names` | `list[str]` | Noms des skills requis |
| `output_type` | `type` | Type de sortie attendue |
| `strategies` | `list[Strategy]` | Stratégies de génération |

**Constructeur :**

```python
def __init__(self, **kwargs):
    setup_logging()
    sandbox = _sandbox_enabled(kwargs)
    # ... configuration des stratégies
    super().__init__(**kwargs)
```

---

### `DefaultsMixin`

```python
class DefaultsMixin:
    # Attributs de classe fournis par les sous-classes
```

**Description :** Mixin qui fournit des valeurs par défaut pour `name`, `agent_config`, `skill_names`, et `output_type`. Les sous-classes qui héritent de ce mixin n'ont qu'à définir ces attributs de classe.

---

**Fonctions de postcondition :**

#### `story_spec_postcondition()`

```python
def story_spec_postcondition(result: dict) -> bool
```

**Description :** Vérifie que le résultat d'un agent est un `StorySpec` valide (a au moins 1 act, 1 beat, et un titre non vide).

---

#### `storyboard_spec_postcondition()`

```python
def storyboard_spec_postcondition(result: dict) -> bool
```

**Description :** Vérifie que le résultat est un `StoryboardSpec` valide (a au moins 1 shot, chaque shot a un id et un type de plan).

---

#### `scene_spec_postcondition()`

```python
def scene_spec_postcondition(result: dict) -> bool
```

**Description :** Vérifie que le résultat est un `SceneSpec` valide (a un engine, au moins 1 shot, et chaque shot a un id).

---

#### `blender_script_postcondition()`

```python
def blender_script_postcondition(result: dict) -> bool
```

**Description :** Vérifie que le résultat est un `BlenderScript` valide (a un champ `script` non vide et de longueur raisonnable).

---

**Fonctions helper :**

#### `codeact_with_sandbox()`

```python
def codeact_with_sandbox(sandbox: bool, **overrides) -> CodeActStrategy
```

**Description :** Factory pour créer une `CodeActStrategy` avec une configuration sandbox optionnelle.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `sandbox` | `bool` | Si `True`, active le mode sandbox (exécution sécurisée) |
| `**overrides` | — | Paramètres additionnels pour la stratégie |

**Valeur de retour :** `CodeActStrategy` — la stratégie configurée.

---

**Exports :**

| Symbole | Source |
|---------|--------|
| `GenerationError` | `nooa.exceptions` |
| `InvariantError` | `nooa.exceptions` |

---

### 2.3 `agents/story.py`

Agent de génération de narration / scénario.

**Classe :**

### `StoryAgent`

```python
class StoryAgent(BaseAgent, DefaultsMixin):
    name = "story_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["storytelling"]
    output_type = StorySpec
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent spécialisé dans la génération de scénarios narratifs. Prend un brief (résumé, genre, thème, cible) et produit un `StorySpec` structuré avec des actes, des beats et des personnages.

**Entrée attendue :** Un `brief` contenant au minimum :
- `summary` : résumé de l'histoire
- `genre` : genre de l'œuvre
- `theme` : thème central
- `target_audience` : public cible

**Sortie :** `StorySpec` (voir `domain/narrative.py`)

**Compétences requises :** `storytelling`

---

### 2.4 `agents/board.py`

Agent de storyboard — décompose la narration en plans visuels.

**Classe :**

### `StoryboardAgent`

```python
class StoryboardAgent(BaseAgent, DefaultsMixin):
    name = "storyboard_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["cinematography"]
    output_type = StoryboardSpec
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un `StorySpec` et le transforme en `StoryboardSpec` — une séquence de shots décrits visuellement (plan type, caméra, éclairage, action).

**Entrée :** `StorySpec`

**Sortie :** `StoryboardSpec` (voir `domain/narrative.py`)

**Compétences requises :** `cinematography`

---

### 2.5 `agents/director.py`

Agent de direction — convertit le storyboard en spécifications de scène détaillées.

**Classe :**

### `DirectorAgent`

```python
class DirectorAgent(BaseAgent, DefaultsMixin):
    name = "director_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["storyboard", "cinematography", "lighting", "composition"]
    output_type = SceneSpec
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un `StoryboardSpec` et le transforme en `SceneSpec` — des instructions détaillées pour le moteur 3D (caméras, éclairage, matériaux, positions, rendu).

**Entrée :** `StoryboardSpec`

**Sortie :** `SceneSpec` (voir `domain/scene.py`)

**Compétences requises :** `storyboard`, `cinematography`, `lighting`, `composition`

---

### 2.6 `agents/blender.py`

Agent de script Blender — génère du code Python Blender exécutable.

**Imports :** `nooa.agents.ReflexionStrategy`

**Fonction privée :**

#### `_blender_reflexion_config()`

```python
def _blender_reflexion_config() -> dict
```

**Description :** Retourne la configuration de la stratégie de réflexion pour l'agent Blender. Configure le nombre d'itérations de réflexion et les critères d'évaluation.

**Valeur de retour :** `dict` — configuration de la réflexion.

---

**Classe :**

### `BlenderAgent`

```python
class BlenderAgent(BaseAgent, DefaultsMixin):
    name = "blender_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = [
        "blender-python", "modeling", "shading", "lighting",
        "camera", "rendering", "animation", "compositing"
    ]
    output_type = BlenderScript
    strategies = [
        codeact_with_sandbox(sandbox),
        ReflexionStrategy(config=_blender_reflexion_config())
    ]
```

**Description :** Agent qui prend un `SceneSpec` et génère un `BlenderScript` — un script Python complet et exécutable pour Blender. Utilise une stratégie de réflexion (ReflexionStrategy) pour améliorer la qualité du code généré en révisant ses propres erreurs.

**Entrée :** `SceneSpec`

**Sortie :** `BlenderScript` (voir `domain/scene.py`)

**Compétences requises :** `blender-python`, `modeling`, `shading`, `lighting`, `camera`, `rendering`, `animation`, `compositing`

---

### 2.7 `agents/char.py`

Agent de design de personnages.

**Classe :**

### `CharacterDesignerAgent`

```python
class CharacterDesignerAgent(BaseAgent, DefaultsMixin):
    name = "character_designer_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["character-design", "modeling"]
    output_type = CharacterDesignResult
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un `CharacterSpec` et produit un `CharacterDesignResult` — des spécifications détaillées de modèle 3D de personnage (géométrie, matériaux, squelette, animations).

**Entrée :** `CharacterSpec`

**Sortie :** `CharacterDesignResult` (voir `domain/media.py`)

**Fonction de postcondition :** `_character_design_postcondition()`

---

### 2.8 `agents/env.py`

Agent d'art environnemental.

**Classe :**

### `EnvironmentArtistAgent`

```python
class EnvironmentArtistAgent(BaseAgent, DefaultsMixin):
    name = "environment_artist_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["environment-art", "texturing", "lighting"]
    output_type = EnvironmentDesignResult
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un `EnvironmentSpec` et produit un `EnvironmentDesignResult` — des spécifications détaillées d'environnement 3D (terrains, bâtiments, végétation, éclairage ambiant).

**Entrée :** `EnvironmentSpec`

**Sortie :** `EnvironmentDesignResult` (voir `domain/media.py`)

**Fonction de postcondition :** `_environment_postcondition()`

---

### 2.9 `agents/animator.py`

Agent d'animation.

**Classe :**

### `AnimatorAgent`

```python
class AnimatorAgent(BaseAgent, DefaultsMixin):
    name = "animator_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["animation", "rigging"]
    output_type = AnimationResult
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend des spécifications de mouvement et produit un `AnimationResult` — des courbes d'animation, des clés, et des métadonnées de timing.

**Entrée :** Spécifications de mouvement (personnage, action, durée)

**Sortie :** `AnimationResult` (voir `domain/media.py`)

**Fonction de postcondition :** `_animation_postcondition()`

---

### 2.10 `agents/audio.py`

Agent audio — planifie les pistes audio (dialogue, effets, musique).

**Classe :**

### `AudioAgent`

```python
class AudioAgent(BaseAgent, DefaultsMixin):
    name = "audio_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["audio", "sound-design"]
    output_type = AudioPlan
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un storyboard ou des spécifications de scène et produit un `AudioPlan` — un plan détaillé des pistes audio nécessaires (dialogue, SFX, musique) avec synchronisation temporelle.

**Sortie :** `AudioPlan` (voir `domain/media.py`)

**Fonction de postcondition :** `_audio_postcondition()`

---

### 2.11 `agents/comp.py`

Agent de composition / post-traitement.

**Classe :**

### `CompositingAgent`

```python
class CompositingAgent(BaseAgent, DefaultsMixin):
    name = "compositing_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["compositing", "post-processing"]
    output_type = CompositeSpec
    strategies = [CodeActLiteStrategy()]
```

**Description :** Agent qui prend des passes de rendu brutes et produit un `CompositeSpec` — des instructions de composition finale (calques, filtres, étalonnage, effets).

**Note :** Utilise `CodeActLiteStrategy` (pas `CodeActStrategy` standard) — version allégée sans exécution sandbox.

**Sortie :** `CompositeSpec` (voir `domain/media.py`)

---

### 2.12 `agents/loc.py`

Agent de localisation.

**Classe :**

### `LocalizationAgent`

```python
class LocalizationAgent(BaseAgent, DefaultsMixin):
    name = "localization_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["localization"]
    output_type = LanguagePackage
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un contenu textuel (dialogues, sous-titres, interfaces) et produit un `LanguagePackage` — un ensemble de traductions et adaptations linguistiques.

**Sortie :** `LanguagePackage` (voir `domain/media.py`)

---

### 2.13 `agents/music.py`

Agent de composition musicale.

**Classe :**

### `MusicComposerAgent`

```python
class MusicComposerAgent(BaseAgent, DefaultsMixin):
    name = "music_composer_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["music-composition"]
    output_type = MusicPlan
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend des indications narratives et produit un `MusicPlan` — un plan musical avec des cues, des instruments, le tempo, l'humeur, et la synchronisation.

**Sortie :** `MusicPlan` (voir `domain/media.py`)

**Fonction de postcondition :** `_music_postcondition()`

---

### 2.14 `agents/sfx.py`

Agent de design sonore.

**Classe :**

### `SoundDesignerAgent`

```python
class SoundDesignerAgent(BaseAgent, DefaultsMixin):
    name = "sound_designer_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["sound-design"]
    output_type = SoundDesignPlan
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend des spécifications de scène et produit un `SoundDesignPlan` — un plan de couches sonores (ambiance, effets ponctuels, réverbération, etc.).

**Sortie :** `SoundDesignPlan` (voir `domain/media.py`)

**Fonction de postcondition :** `_sound_design_postcondition()`

---

### 2.15 `agents/qa.py`

Agent de QA (Quality Assurance).

**Classe :**

### `QAAgent`

```python
class QAAgent(BaseAgent, DefaultsMixin):
    name = "qa_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["quality-assurance"]
    output_type = QAReport
    strategies = [
        codeact_with_sandbox(sandbox),
        PredictStrategy()
    ]
```

**Description :** Agent qui évalue la qualité des sorties des autres agents. Utilise deux stratégies : `CodeActStrategy` (analyse du code) et `PredictStrategy` (évaluation prédictive). Produit un `QAReport` avec des issues classées par sévérité.

**Sortie :** `QAReport` (voir `domain/qa.py`)

**Fonction de postcondition :** `_qa_postcondition()`

---

### 2.16 `agents/review.py`

Agent de revue créative.

**Classe :**

### `ReviewAgent`

```python
class ReviewAgent(BaseAgent, DefaultsMixin):
    name = "review_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["creative-review"]
    output_type = ReviewReport
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui évalue la qualité créative des productions (cohérence narrative, esthétique, impact émotionnel). Produit un `ReviewReport` avec des retours structurés.

**Sortie :** `ReviewReport` (voir `domain/media.py`)

**Fonction de postcondition :** `_review_postcondition()`

---

### 2.17 `agents/ue5.py`

Agent Unreal Engine 5.

**Classe :**

### `UE5Agent`

```python
class UE5Agent(BaseAgent, DefaultsMixin):
    name = "ue5_agent"
    agent_config = {"model": "gpt-4o"}
    skill_names = ["unreal-engine-5", "blueprint", "material-editor"]
    output_type = UE5Commands
    strategies = [codeact_with_sandbox(sandbox)]
```

**Description :** Agent qui prend un `SceneSpec` et produit des `UE5Commands` — une séquence de commandes exécutables dans Unreal Engine 5 (niveaux, matériaux, éclairage, animation, rendu).

**Sortie :** `UE5Commands` (voir `domain/ue5.py`)

**Fonction de postcondition :** `ue5_commands_postcondition()`

---

## 3. Domaine (domain/)

### 3.1 `domain/__init__.py`

Module d'export centralisé pour tous les types de domaine.

**Exports :**

| Symbole | Module source |
|---------|---------------|
| `Engine` | `domain.scene` |
| `ENGINE_BLENDER` | `domain.scene` |
| `ENGINE_UE5` | `domain.scene` |
| `ENGINE_GODOT` | `domain.scene` |
| `ENGINE_AI_VIDEO` | `domain.scene` |
| `SUPPORTED_ENGINES` | `domain.scene` |
| `UE5RenderSpec` | `domain.scene` |
| `UE5CameraSpec` | `domain.scene` |
| `LightingSpec` | `domain.scene` |
| `CharacterSpec` | `domain.scene` |
| `EnvironmentSpec` | `domain.scene` |
| `CameraSpec` | `domain.scene` |
| `ShotSpec` | `domain.scene` |
| `RenderOutput` | `domain.scene` |
| `SceneSpec` | `domain.scene` |
| `BlenderScript` | `domain.scene` |
| `StoryBeat` | `domain.narrative` |
| `Act` | `domain.narrative` |
| `Character` | `domain.narrative` |
| `DialogueLine` | `domain.narrative` |
| `StorySpec` | `domain.narrative` |
| `StoryboardShot` | `domain.narrative` |
| `StoryboardSpec` | `domain.narrative` |
| `CharacterModel` | `domain.media` |
| `EnvironmentAsset` | `domain.media` |
| `AnimationClip` | `domain.media` |
| `AnimationResult` | `domain.media` |
| `CharacterDesignResult` | `domain.media` |
| `EnvironmentDesignResult` | `domain.media` |
| `AudioTrack` | `domain.media` |
| `AudioPlan` | `domain.media` |
| `MusicCue` | `domain.media` |
| `MusicPlan` | `domain.media` |
| `SoundLayer` | `domain.media` |
| `SoundDesignPlan` | `domain.media` |
| `AudioMaster` | `domain.media` |
| `RenderPass` | `domain.media` |
| `CompositeSpec` | `domain.media` |
| `LanguagePackage` | `domain.media` |
| `ReviewReport` | `domain.media` |
| `QAStatus` | `domain.qa` |
| `IssueKind` | `domain.qa` |
| `Issue` | `domain.qa` |
| `QAReport` | `domain.qa` |
| `RevisionSpec` | `domain.qa` |
| `Brief` | `domain.project` |
| `Shot` | `domain.project` |
| `Sequence` | `domain.project` |
| `Project` | `domain.project` |
| `Patch` | `domain.patch` |
| `AssetKind` | `domain.asset` |
| `Asset` | `domain.asset` |
| `UE5Command` | `domain.ue5` |
| `UE5Commands` | `domain.ue5` |
| `new_id` | `domain.utils` |

---

### 3.2 `domain/scene.py`

Types de domaine pour les scènes 3D, les plans, l'éclairage, les caméras et le rendu.

**Constantes :**

| Nom | Type | Valeur | Description |
|-----|------|--------|-------------|
| `ENGINE_BLENDER` | `str` | `"blender"` | Identifiant du moteur Blender |
| `ENGINE_UE5` | `str` | `"unreal"` | Identifiant du moteur Unreal Engine 5 |
| `ENGINE_GODOT` | `str` | `"godot"` | Identifiant du moteur Godot |
| `ENGINE_AI_VIDEO` | `str` | `"ai_video"` | Identifiant du moteur de vidéo IA |
| `SUPPORTED_ENGINES` | `frozenset[str]` | `{ENGINE_BLENDER, ENGINE_UE5, ENGINE_GODOT, ENGINE_AI_VIDEO}` | Ensembles des moteurs supportés |

---

**Classes :**

### `UE5RenderSpec`

```python
@dataclasses.dataclass
class UE5RenderSpec:
    width: int = 1920
    height: int = 1080
    frame_rate: int = 30
    quality: str = "high"
```

**Description :** Spécification de rendu pour Unreal Engine 5.

---

### `UE5CameraSpec`

```python
@dataclasses.dataclass
class UE5CameraSpec:
    position: tuple[float, float, float] = (0.0, -5.0, 2.0)
    look_at: tuple[float, float, float] = (0.0, 0.0, 0.0)
    fov: float = 90.0
```

**Description :** Spécification de caméra pour Unreal Engine 5.

---

### `LightingSpec`

```python
@dataclasses.dataclass
class LightingSpec:
    name: str = "key"
    kind: str = "point"
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    energy: float = 1000.0
    position: tuple[float, float, float] = (0.0, 0.0, 5.0)
```

**Description :** Spécification d'une source de lumière.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `name` | `str` | Nom de la lumière (ex: `"key"`, `"fill"`, `"rim"`) |
| `kind` | `str` | Type de lumière (`"point"`, `"sun"`, `"spot"`, `"area"`) |
| `color` | `tuple[float, float, float]` | Couleur RGB (0.0–1.0) |
| `energy` | `float` | Puissance de la lumière |
| `position` | `tuple[float, float, float]` | Position XYZ |

---

### `CharacterSpec`

```python
@dataclasses.dataclass
class CharacterSpec:
    name: str = ""
    description: str = ""
    mesh: str | None = None
    materials: list[str] = dataclasses.field(default_factory=list)
    skeleton: str | None = None
```

**Description :** Spécification d'un personnage dans une scène.

---

### `EnvironmentSpec`

```python
@dataclasses.dataclass
class EnvironmentSpec:
    name: str = ""
    description: str = ""
    assets: list[str] = dataclasses.field(default_factory=list)
    sky: str | None = None
    ground_material: str | None = None
```

**Description :** Spécification d'un environnement / décor.

---

### `CameraSpec`

```python
@dataclasses.dataclass
class CameraSpec:
    name: str = "camera"
    position: tuple[float, float, float] = (0.0, -10.0, 3.0)
    rotation: tuple[float, float, float] = (90.0, 0.0, 0.0)
    focal_length: float = 50.0
    sensor_width: float = 36.0
    clip_start: float = 0.1
    clip_end: float = 1000.0
```

**Description :** Spécification de caméra pour Blender.

---

### `ShotSpec`

```python
@dataclasses.dataclass
class ShotSpec:
    id: str = ""
    name: str = ""
    description: str = ""
    duration_sec: float = 5.0
    camera: CameraSpec = dataclasses.field(default_factory=CameraSpec)
    characters: list[CharacterSpec] = dataclasses.field(default_factory=list)
    environment: EnvironmentSpec = dataclasses.field(default_factory=EnvironmentSpec)
    lighting: list[LightingSpec] = dataclasses.field(default_factory=list)
    render: RenderOutput = dataclasses.field(default_factory=RenderOutput)
```

**Description :** Spécification complète d'un plan (shot) de production.

---

### `RenderOutput`

```python
@dataclasses.dataclass
class RenderOutput:
    engine: str = ENGINE_BLENDER
    resolution_x: int = 1920
    resolution_y: int = 1080
    frame_start: int = 1
    frame_end: int = 1
    fps: int = 24
    output_path: str = "//output/"
    format: str = "PNG"
```

**Description :** Paramètres de rendu de sortie.

---

### `SceneSpec`

```python
@dataclasses.dataclass
class SceneSpec:
    id: str = ""
    engine: str = ENGINE_BLENDER
    name: str = ""
    description: str = ""
    shots: list[ShotSpec] = dataclasses.field(default_factory=list)
    ue5_render: UE5RenderSpec | None = None
    ue5_camera: UE5CameraSpec | None = None
```

**Description :** Spécification complète d'une scène. Type de sortie des `DirectorAgent` et `UE5Agent`.

**Méthodes :**

#### `to_mapping()`

```python
def to_mapping(self) -> dict
```

**Description :** Sérialise la scène en dictionnaire récursif (tous les dataclasses imbriqués sont convertis).

---

#### `from_mapping()`

```python
@classmethod
def from_mapping(cls, data: dict) -> SceneSpec
```

**Description :** Désérialise une scène depuis un dictionnaire.

---

#### `with_engine()`

```python
def with_engine(self, engine: str) -> SceneSpec
```

**Description :** Retourne une copie de la scène avec un moteur différent.

---

### `BlenderScript`

```python
@dataclasses.dataclass
class BlenderScript:
    script: str = ""
    description: str = ""
    warnings: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Script Python pour Blender. Type de sortie du `BlenderAgent`.

---

### 3.3 `domain/narrative.py`

Types de domaine pour la narration, les scénarios et les storyboards.

**Fonction privée :**

#### `_plain()`

```python
def _plain(value: Any) -> Any
```

**Description :** Nettoie une valeur pour la sérialisation JSON. Convertit les dataclasses en dictionnaires et les enums en strings.

---

**Classes :**

### `StoryBeat`

```python
@dataclasses.dataclass
class StoryBeat:
    id: str = ""
    title: str = ""
    summary: str = ""
    characters: list[str] = dataclasses.field(default_factory=list)
    mood: str = ""
```

**Description :** Un battement narratif individuel (élément de base d'un acte).

---

### `Act`

```python
@dataclasses.dataclass
class Act:
    id: str = ""
    title: str = ""
    summary: str = ""
    beats: list[StoryBeat] = dataclasses.field(default_factory=list)
```

**Description :** Un acte de l'histoire, contenant plusieurs beats.

---

### `Character`

```python
@dataclasses.dataclass
class Character:
    name: str = ""
    role: str = ""
    description: str = ""
    arc: str = ""
```

**Description :** Un personnage de l'histoire.

---

### `DialogueLine`

```python
@dataclasses.dataclass
class DialogueLine:
    character: str = ""
    text: str = ""
    emotion: str = ""
    timing_sec: float = 0.0
```

**Description :** Une ligne de dialogue synchronisée.

---

### `StorySpec`

```python
@dataclasses.dataclass
class StorySpec:
    id: str = ""
    title: str = ""
    logline: str = ""
    genre: str = ""
    theme: str = ""
    target_audience: str = ""
    acts: list[Act] = dataclasses.field(default_factory=list)
    characters: list[Character] = dataclasses.field(default_factory=list)
```

**Description :** Spécification narrative complète. Type de sortie du `StoryAgent`.

**Méthodes :**

#### `to_dict()`

```python
def to_dict(self) -> dict
```

**Description :** Sérialise le scénario en dictionnaire.

---

#### `from_dict()`

```python
@classmethod
def from_dict(cls, data: dict) -> StorySpec
```

**Description :** Désérialise un scénario depuis un dictionnaire.

---

### `StoryboardShot`

```python
@dataclasses.dataclass
class StoryboardShot:
    id: str = ""
    beat_id: str = ""
    description: str = ""
    shot_type: str = ""
    camera_movement: str = ""
    duration_sec: float = 5.0
    characters: list[str] = dataclasses.field(default_factory=list)
    dialogue: list[DialogueLine] = dataclasses.field(default_factory=list)
    notes: str = ""
```

**Description :** Un plan du storyboard, lié à un beat narratif.

---

### `StoryboardSpec`

```python
@dataclasses.dataclass
class StoryboardSpec:
    id: str = ""
    story_id: str = ""
    title: str = ""
    shots: list[StoryboardShot] = dataclasses.field(default_factory=list)
```

**Description :** Spécification complète du storyboard. Type de sortie du `StoryboardAgent`.

**Méthodes :**

#### `to_dict()`

```python
def to_dict(self) -> dict
```

#### `from_dict()`

```python
@classmethod
def from_dict(cls, data: dict) -> StoryboardSpec
```

---

### 3.4 `domain/media.py`

Types de domaine pour les médias : assets, animation, audio, composition, localisation et revue.

**Classes :**

### `CharacterModel`

```python
@dataclasses.dataclass
class CharacterModel:
    id: str = ""
    name: str = ""
    mesh_path: str | None = None
    materials: list[str] = dataclasses.field(default_factory=list)
    skeleton: str | None = None
    animations: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Modèle 3D de personnage finalisé.

---

### `EnvironmentAsset`

```python
@dataclasses.dataclass
class EnvironmentAsset:
    id: str = ""
    name: str = ""
    asset_path: str | None = None
    asset_type: str = ""
    materials: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Asset d'environnement (terrain, bâtiment, prop, etc.).

---

### `AnimationClip`

```python
@dataclasses.dataclass
class AnimationClip:
    id: str = ""
    name: str = ""
    duration_sec: float = 0.0
    frame_start: int = 0
    frame_end: int = 0
    fps: int = 24
    keyframes: list[dict] = dataclasses.field(default_factory=list)
```

**Description :** Un clip d'animation individuel.

---

### `AnimationResult`

```python
@dataclasses.dataclass
class AnimationResult:
    character_id: str = ""
    clips: list[AnimationClip] = dataclasses.field(default_factory=list)
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Résultat complet de l'agent d'animation. Type de sortie du `AnimatorAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `AnimationResult`

---

### `CharacterDesignResult`

```python
@dataclasses.dataclass
class CharacterDesignResult:
    character: CharacterModel = dataclasses.field(default_factory=CharacterModel)
    description: str = ""
    variations: list[CharacterModel] = dataclasses.field(default_factory=list)
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Résultat du `CharacterDesignerAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `CharacterDesignResult`

---

### `EnvironmentDesignResult`

```python
@dataclasses.dataclass
class EnvironmentDesignResult:
    assets: list[EnvironmentAsset] = dataclasses.field(default_factory=list)
    description: str = ""
    skybox: str | None = None
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Résultat du `EnvironmentArtistAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `EnvironmentDesignResult`

---

### `AudioTrack`

```python
@dataclasses.dataclass
class AudioTrack:
    id: str = ""
    kind: str = ""
    file_path: str | None = None
    start_sec: float = 0.0
    end_sec: float = 0.0
    volume: float = 1.0
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Piste audio individuelle (dialogue, SFX, musique).

---

### `AudioPlan`

```python
@dataclasses.dataclass
class AudioPlan:
    tracks: list[AudioTrack] = dataclasses.field(default_factory=list)
    description: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Plan audio complet. Type de sortie du `AudioAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `AudioPlan`

---

### `MusicCue`

```python
@dataclasses.dataclass
class MusicCue:
    id: str = ""
    name: str = ""
    mood: str = ""
    tempo_bpm: int = 120
    instruments: list[str] = dataclasses.field(default_factory=list)
    duration_sec: float = 0.0
    start_sec: float = 0.0
    description: str = ""
```

**Description :** Un moment musical (cue) individuel.

---

### `MusicPlan`

```python
@dataclasses.dataclass
class MusicPlan:
    cues: list[MusicCue] = dataclasses.field(default_factory=list)
    overall_mood: str = ""
    description: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Plan musical complet. Type de sortie du `MusicComposerAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `MusicPlan`

---

### `SoundLayer`

```python
@dataclasses.dataclass
class SoundLayer:
    id: str = ""
    name: str = ""
    kind: str = ""
    description: str = ""
    volume: float = 1.0
    spatial: bool = False
    effects: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Couche sonore individuelle (ambiance, SFX, réverbération).

---

### `SoundDesignPlan`

```python
@dataclasses.dataclass
class SoundDesignPlan:
    layers: list[SoundLayer] = dataclasses.field(default_factory=list)
    description: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Plan de design sonore complet. Type de sortie du `SoundDesignerAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `SoundDesignPlan`

---

### `AudioMaster`

```python
@dataclasses.dataclass
class AudioMaster:
    dialogue: AudioPlan = dataclasses.field(default_factory=AudioPlan)
    sfx: AudioPlan = dataclasses.field(default_factory=AudioPlan)
    music: MusicPlan = dataclasses.field(default_factory=MusicPlan)
    sound_design: SoundDesignPlan = dataclasses.field(default_factory=SoundDesignPlan)
```

**Description :** Plan audio maître combinant tous les sous-plans.

---

### `RenderPass`

```python
@dataclasses.dataclass
class RenderPass:
    id: str = ""
    name: str = ""
    kind: str = ""
    input_path: str | None = None
    settings: dict = dataclasses.field(default_factory=dict)
```

**Description :** Pass de rendu individuel (diffuse, normal, depth, etc.).

---

### `CompositeSpec`

```python
@dataclasses.dataclass
class CompositeSpec:
    passes: list[RenderPass] = dataclasses.field(default_factory=list)
    operations: list[dict] = dataclasses.field(default_factory=list)
    output_path: str = ""
    format: str = "PNG"
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Spécification de composition finale. Type de sortie du `CompositingAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `CompositeSpec`

---

### `LanguagePackage`

```python
@dataclasses.dataclass
class LanguagePackage:
    locale: str = "en"
    translations: dict[str, str] = dataclasses.field(default_factory=dict)
    subtitles: list[dict] = dataclasses.field(default_factory=list)
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Package de localisation. Type de sortie du `LocalizationAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `LanguagePackage`

---

### `ReviewReport`

```python
@dataclasses.dataclass
class ReviewReport:
    score: float = 0.0
    feedback: list[str] = dataclasses.field(default_factory=list)
    suggestions: list[str] = dataclasses.field(default_factory=list)
    approved: bool = False
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Rapport de revue créative. Type de sortie du `ReviewAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `ReviewReport`

---

### 3.5 `domain/qa.py`

Types de domaine pour l'assurance qualité.

**Enums :**

### `QAStatus`

```python
class QAStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIPPED = "skipped"
```

**Description :** Statuts possibles pour un contrôle qualité.

---

### `IssueKind`

```python
class IssueKind(str, Enum):
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    STYLE = "style"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    MISSING = "missing"
    OTHER = "other"
```

**Description :** Catégories d'issues de qualité.

---

**Classes :**

### `Issue`

```python
@dataclasses.dataclass
class Issue:
    kind: IssueKind = IssueKind.OTHER
    severity: str = "info"
    message: str = ""
    file: str | None = None
    line: int | None = None
    suggestion: str | None = None
```

**Description :** Un problème identifié lors du contrôle qualité.

---

### `QAReport`

```python
@dataclasses.dataclass
class QAReport:
    status: QAStatus = QAStatus.PASS
    issues: list[Issue] = dataclasses.field(default_factory=list)
    score: float = 100.0
    summary: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Rapport de contrôle qualité complet. Type de sortie du `QAAgent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `QAReport`

---

### `RevisionSpec`

```python
@dataclasses.dataclass
class RevisionSpec:
    target_scene_id: str = ""
    changes: list[dict] = dataclasses.field(default_factory=list)
    reason: str = ""
    priority: str = "normal"
```

**Description :** Spécification de révision basée sur un rapport QA.

---

### 3.6 `domain/project.py`

Types de domaine pour la gestion de projets.

**Classes :**

### `Brief`

```python
@dataclasses.dataclass
class Brief:
    title: str = ""
    summary: str = ""
    genre: str = ""
    theme: str = ""
    target_audience: str = ""
    duration_minutes: float = 5.0
    style: str = ""
    references: list[str] = dataclasses.field(default_factory=list)
    constraints: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Brief créatif d'un projet de production.

---

### `Shot`

```python
@dataclasses.dataclass
class Shot:
    id: str = ""
    sequence_id: str = ""
    name: str = ""
    status: str = "pending"
    duration_sec: float = 5.0
    description: str = ""
```

**Description :** Un plan individuel dans un sequence du projet.

---

### `Sequence`

```python
@dataclasses.dataclass
class Sequence:
    id: str = ""
    project_id: str = ""
    name: str = ""
    status: str = "pending"
    shots: list[Shot] = dataclasses.field(default_factory=list)
```

**Description :** Une séquence de plans.

---

### `Project`

```python
@dataclasses.dataclass
class Project:
    id: str = ""
    name: str = ""
    brief: Brief = dataclasses.field(default_factory=Brief)
    sequences: list[Sequence] = dataclasses.field(default_factory=list)
    status: str = "draft"
    engine: str = "blender"
```

**Description :** Projet de production complet.

---

### 3.7 `domain/patch.py`

Types et utilitaires pour l'application de patches sur des dictionnaires/nodes de scène.

**Types :**

```python
PathPart = str | int
```

**Description :** Type alias pour les parties d'un chemin d'accès (clé string ou index entier).

---

**Classes :**

### `Patch`

```python
@dataclasses.dataclass
class Patch:
    path: list[PathPart] = dataclasses.field(default_factory=list)
    op: str = "set"
    value: Any = None
    old_value: Any = None
```

**Description :** Un patch atomique à appliquer sur un objet.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `path` | `list[PathPart]` | Chemin d'accès vers la valeur cible (ex: `["shots", 0, "camera", "position"]`) |
| `op` | `str` | Opération : `"set"`, `"delete"`, `"insert"`, `"append"` |
| `value` | `Any` | Nouvelle valeur (pour set/insert/append) |
| `old_value` | `Any` | Ancienne valeur (pour validation/rollback) |

---

**Fonctions :**

#### `parse_path()`

```python
def parse_path(path_str: str) -> list[PathPart]
```

**Description :** Parse une chaîne de chemin en liste de parties. Supporte la notation pointée (`shots.0.camera.position`) avec conversion automatique des entiers.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `path_str` | `str` | Chemin en notation pointée |

**Valeur de retour :** `list[PathPart]` — liste de clés et index.

---

#### `apply_patch()`

```python
def apply_patch(obj: Any, patch: Patch) -> Any
```

**Description :** Applique un patch sur un objet (dict, list, ou dataclass) et retourne l'objet modifié.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `obj` | `Any` | Objet cible (dict, list, ou dataclass) |
| `patch` | `Patch` | Le patch à appliquer |

**Valeur de retour :** `Any` — l'objet modifié.

---

#### `apply_patches()`

```python
def apply_patches(obj: Any, patches: list[Patch]) -> Any
```

**Description :** Applique une liste de patches séquentiellement.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `obj` | `Any` | Objet cible |
| `patches` | `list[Patch]` | Liste de patches à appliquer dans l'ordre |

**Valeur de retour :** `Any` — l'objet modifié après tous les patches.

---

### 3.8 `domain/asset.py`

Types de domaine pour la gestion des assets.

**Types :**

```python
AssetKind = Literal[
    "model", "texture", "hdri", "audio", "animation",
    "material", "script", "scene", "other"
]
```

**Description :** Type literal des catégories d'assets supportées.

---

**Fonctions :**

#### `sha256_of_file()`

```python
def sha256_of_file(path: str | Path) -> str
```

**Description :** Calcule le hash SHA-256 d'un fichier.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `path` | `str \| Path` | Chemin du fichier |

**Valeur de retour :** `str` — hash hexadécimal (64 caractères).

---

**Classes :**

### `Asset`

```python
@dataclasses.dataclass
class Asset:
    id: str = ""
    kind: AssetKind = "other"
    name: str = ""
    path: str = ""
    sha256: str = ""
    tags: list[str] = dataclasses.field(default_factory=list)
    metadata: dict = dataclasses.field(default_factory=dict)
    created_at: str = ""
```

**Description :** Représente un asset de production (modèle, texture, audio, etc.).

---

### 3.9 `domain/ue5.py`

Types de domaine pour les commandes Unreal Engine 5.

**Classes :**

### `UE5Command`

```python
@dataclasses.dataclass
class UE5Command:
    action: str = ""
    target: str = ""
    params: dict = dataclasses.field(default_factory=dict)
```

**Description :** Une commande individuelle pour Unreal Engine 5.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `action` | `str` | Type d'action (`"create_actor"`, `"set_material"`, `"add_light"`, etc.) |
| `target` | `str` | Cible de la commande (nom de l'acteur, material, etc.) |
| `params` | `dict` | Paramètres additionnels de la commande |

---

### `UE5Commands`

```python
@dataclasses.dataclass
class UE5Commands:
    commands: list[UE5Command] = dataclasses.field(default_factory=list)
    level_name: str = ""
    description: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Liste ordonnée de commandes UE5. Type de sortie du `UE5Agent`.

**Méthodes :**

- `to_mapping()` → `dict`
- `from_mapping(data: dict)` → `UE5Commands`

---

### 3.10 `domain/utils.py`

Utilitaires partagés du domaine.

**Fonctions :**

#### `new_id()`

```python
def new_id() -> str
```

**Description :** Génère un nouvel identifiant unique (UUID v4, hexadécimal tronqué à 16 caractères).

**Valeur de retour :** `str` — identifiant unique (ex: `"a1b2c3d4e5f6a7b8"`).

---

## 4. API (api/)

### 4.1 `api/__init__.py`

Module vide. Sert de namespace pour le package API.

---

### 4.2 `api/app.py`

Application FastAPI principale. Configure le serveur, les routes, le CORS et le streaming SSE.

**Imports :** `fastapi`, `fastapi.middleware.cors`, `starlette.responses`, `deepblender.api.*` (tous les modules API)

**Fonctions :**

#### `create_app()`

```python
def create_app() -> FastAPI
```

**Description :** Factory qui crée et configure l'application FastAPI. Installe le middleware CORS, enregistre toutes les routes, initialise la base de données.

**Valeur de retour :** `FastAPI` — l'application configurée.

**Routes enregistrées :**

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `POST` | `/register` | Inscription d'un nouvel utilisateur |
| `POST` | `/login` | Authentification et obtention de tokens |
| `GET` | `/me` | Informations sur l'utilisateur courant |
| `GET` | `/organizations` | Liste des organisations |
| `POST` | `/organizations` | Créer une organisation |
| `GET` | `/workspaces` | Liste des workspaces |
| `POST` | `/workspaces` | Créer un workspace |
| `GET` | `/projects/{project_id}` | Détails d'un projet |
| `POST` | `/projects` | Créer un projet |
| `GET` | `/productions/{production_id}` | Détails d'une production |
| `POST` | `/productions` | Créer une production |
| `GET` | `/productions/{production_id}/events` | SSE streaming des événements |
| `GET` | `/worker/status` | Statut du worker |
| `PUT` | `/shots/{shot_id}` | Mettre à jour un shot |
| `POST` | `/patches` | Créer un patch |
| `GET` | `/artifacts/{artifact_id}` | Récupérer un artifact |
| `POST` | `/pipelines/{production_id}/run` | Lancer le pipeline de production |
| `POST` | `/validate` | Valider du code |
| `GET` | `/scenes/{scene_id}` | Détails d'une scène |

---

### 4.3 `api/bus.py`

Bus d'événements asynchrone pour le streaming SSE.

**Classe :**

### `AsyncEventBus`

```python
class AsyncEventBus:
    def __init__(self):
        ...
```

**Description :** Bus d'événements pub/sub asynchrone. Permet aux producteurs (pipeline) de publier des événements et aux consommateurs (SSE) de s'y abonner. Supporte l'historique pour la reconnexion SSE.

**Méthodes :**

#### `subscribe()`

```python
async def subscribe(self) -> AsyncGenerator[dict, None]
```

**Description :** S'abonne au bus et retourne un générateur asynchrone d'événements. Joue d'abord l'historique, puis les événements en temps réel.

**Valeur de retour :** `AsyncGenerator[dict, None]` — générateur asynchrone d'événements JSON.

---

#### `unsubscribe()`

```python
def unsubscribe(self, queue: asyncio.Queue) -> None
```

**Description :** Désabonne une queue du bus.

---

#### `publish_nowait()`

```python
def publish_nowait(self, event: dict) -> None
```

**Description :** Publie un événement sans attendre. Ajoute à l'historique et distribue à tous les abonnés actifs.

---

#### `publish()`

```python
async def publish(self, event: dict) -> None
```

**Description :** Publie un événement de manière asynchrone.

---

### 4.4 `api/db.py`

Configuration de la base de données SQLAlchemy.

**Classes :**

### `Base`

```python
class Base(DeclarativeBase):
    pass
```

**Description :** Classe de base pour tous les modèles ORM SQLAlchemy.

---

**Fonctions :**

#### `create_engine_for()`

```python
def create_engine_for(url: str) -> Engine
```

**Description :** Crée un moteur SQLAlchemy pour l'URL de connexion donnée.

---

#### `create_session_factory()`

```python
def create_session_factory(engine: Engine) -> sessionmaker[Session]
```

**Description :** Crée une factory de sessions SQLAlchemy.

---

**Types :**

```python
DbSession = Session
```

**Description :** Type alias pour les sessions de base de données.

---

#### `_as_sqlalchemy_url()`

```python
def _as_sqlalchemy_url(url: str) -> str
```

**Description :** Convertit une URL de base de données en format SQLAlchemy compatible.

---

### 4.5 `api/deps.py`

Dépendances FastAPI pour l'authentification, la vérification des rôles et le scoped access.

**Constantes :**

| Nom | Valeur | Description |
|-----|--------|-------------|
| `ROLE_READ` | `"read"` | Rôle de lecture seule |
| `ROLE_WRITE` | `"write"` | Rôle d'écriture |
| `ROLE_MANAGE` | `"manage"` | Rôle d'administration |

---

**Types :**

```python
CurrentUser = User
```

**Description :** Type alias pour l'utilisateur authentifié.

---

**Fonctions :**

#### `get_token()`

```python
def get_token(authorization: str | None = Header(None)) -> str | None
```

**Description :** Extrait le token JWT du header Authorization.

---

#### `get_current_user()`

```python
def get_current_user(token: str = Depends(get_token), session: Session = Depends(...)) -> User
```

**Description :** Dépendance FastAPI qui retourne l'utilisateur authentifié à partir du token JWT.

---

#### `get_organization()`

```python
def get_organization(org_id: str, session: Session = Depends(...)) -> Organization
```

**Description :** Récupère une organisation par son ID.

---

#### `require_membership()`

```python
def require_membership(user: User, org: Organization, session: Session = Depends(...)) -> Membership
```

**Description :** Vérifie que l'utilisateur est membre de l'organisation.

---

#### `require_role()`

```python
def require_role(membership: Membership, role: str) -> bool
```

**Description :** Vérifie que le membre a le rôle requis (ou un rôle supérieur).

---

#### `scoped_workspace()`

```python
def scoped_workspace(workspace_id: str, user: User = Depends(get_current_user), ...) -> Workspace
```

**Description :** Récupère un workspace avec vérification d'accès.

---

#### `scoped_project()`

```python
def scoped_project(project_id: str, user: User = Depends(get_current_user), ...) -> Project
```

**Description :** Récupère un projet avec vérification d'accès.

---

#### `scoped_production()`

```python
def scoped_production(production_id: str, user: User = Depends(get_current_user), ...) -> Production
```

**Description :** Récupère une production avec vérification d'accès.

---

### 4.6 `api/models.py`

Modèles ORM SQLAlchemy pour la base de données.

**Constantes :**

| Nom | Description |
|-----|-------------|
| `_STATUSES` | Statuts possibles pour les productions (`draft`, `running`, `completed`, `failed`) |
| `_SHOT_STATUSES` | Statuts possibles pour les shots (`pending`, `in_progress`, `completed`, `review`) |
| `_ROLES` | Rôles possibles pour les membres (`read`, `write`, `manage`) |

---

**Classes (modèles ORM) :**

### `User`

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    full_name: Mapped[str | None]
    created_at: Mapped[datetime]
```

**Description :** Modèle d'utilisateur. Le mot de passe est stocké en hash PBKDF2.

---

### `Organization`

```python
class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str]
    name: Mapped[str]
    slug: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Organisation contenant des workspaces et des membres.

---

### `Membership`

```python
class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str]
    user_id: Mapped[str]
    organization_id: Mapped[str]
    role: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Lien entre un utilisateur et une organisation avec un rôle.

---

### `Workspace`

```python
class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str]
    organization_id: Mapped[str]
    name: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Espace de travail au sein d'une organisation.

---

### `Project`

```python
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str]
    workspace_id: Mapped[str]
    name: Mapped[str]
    brief: Mapped[str | None]  # JSON serialisé
    engine: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Projet de production.

---

### `Production`

```python
class Production(Base):
    __tablename__ = "productions"
    id: Mapped[str]
    project_id: Mapped[str]
    name: Mapped[str]
    status: Mapped[str]
    pipeline_state: Mapped[str | None]  # JSON serialisé
    created_at: Mapped[datetime]
```

**Description :** Instance de production (exécution du pipeline).

---

### `Sequence`

```python
class Sequence(Base):
    __tablename__ = "sequences"
    id: Mapped[str]
    production_id: Mapped[str]
    name: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Séquence de plans dans une production.

---

### `Scene`

```python
class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str]
    production_id: Mapped[str]
    name: Mapped[str]
    spec: Mapped[str | None]  # JSON serialisé (SceneSpec)
    engine: Mapped[str]
    created_at: Mapped[datetime]
```

**Description :** Scène 3D dans une production.

---

### `Shot`

```python
class Shot(Base):
    __tablename__ = "shots"
    id: Mapped[str]
    scene_id: Mapped[str]
    name: Mapped[str]
    status: Mapped[str]
    duration_sec: Mapped[float]
    spec: Mapped[str | None]  # JSON serialisé
    created_at: Mapped[datetime]
```

**Description :** Plan individuel dans une scène.

---

### `Patch`

```python
class Patch(Base):
    __tablename__ = "patches"
    id: Mapped[str]
    shot_id: Mapped[str]
    path: Mapped[str]  # JSON serialisé
    op: Mapped[str]
    value: Mapped[str | None]  # JSON serialisé
    applied: Mapped[bool]
    created_at: Mapped[datetime]
```

**Description :** Patch appliqué à un shot.

---

### `ArtifactRecord`

```python
class ArtifactRecord(Base):
    __tablename__ = "artifacts"
    id: Mapped[str]
    production_id: Mapped[str]
    kind: Mapped[str]
    path: Mapped[str]
    sha256: Mapped[str | None]
    metadata: Mapped[str | None]  # JSON serialisé
    created_at: Mapped[datetime]
```

**Description :** Enregistrement d'un artifact de production (rendu, script, etc.).

---

### `RefreshToken`

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str]
    user_id: Mapped[str]
    token_hash: Mapped[str]
    expires_at: Mapped[datetime]
    revoked: Mapped[bool]
    created_at: Mapped[datetime]
```

**Description :** Token de rafraîchissement pour l'authentification JWT.

---

### 4.7 `api/pipeline.py`

Module de pipeline de production — orchestre les agents et gère l'exécution.

**Types :**

```python
EventHook = Callable[[str, dict], Awaitable[None]]
```

**Description :** Type callback pour les hooks d'événements du pipeline.

---

**Constantes :**

#### `_STEP_COSTS`

```python
_STEP_COSTS: dict[str, int] = { ... }
```

**Description :** Coûts estimés (en tokens ou unités) pour chaque étape du pipeline.

| Étape | Coût |
|-------|------|
| `story` | (valeur) |
| `board` | (valeur) |
| `director` | (valeur) |
| `blender` | (valeur) |
| `qa` | (valeur) |

---

**Fonctions :**

#### `build_agents()`

```python
def build_agents(config: dict) -> dict[str, Agent]
```

**Description :** Instancie et configure tous les agents du pipeline à partir d'un dictionnaire de configuration.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `config` | `dict` | Configuration des modèles et des agents |

**Valeur de retour :** `dict[str, Agent]` — dictionnaire nom → agent instancié.

---

#### `run_production()`

```python
async def run_production(
    production_id: str,
    session_factory,
    event_hook: EventHook | None = None
) -> dict
```

**Description :** Exécute le pipeline complet de production pour un production_id donné. Orchestre séquentiellement les agents : Story → Storyboard → Director → Blender → QA.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `production_id` | `str` | Identifiant de la production |
| `session_factory` | — | Factory de sessions DB |
| `event_hook` | `EventHook \| None` | Callback optionnel pour les événements de progression |

**Valeur de retour :** `dict` — résultat de la production (statut, artifacts, métriques).

---

### 4.8 `api/schemas.py`

Schémas Pydantic pour la validation des entrées/sorties de l'API.

**Classes :**

### Authentification

| Classe | Description |
|--------|-------------|
| `RegisterRequest` | Données d'inscription (email, password, full_name) |
| `LoginRequest` | Données de connexion (email, password) |
| `TokenResponse` | Réponse de connexion (access_token, refresh_token, token_type) |

### Utilisateurs et organisations

| Classe | Description |
|--------|-------------|
| `UserOut` | Sortie utilisateur (id, email, full_name) |
| `MembershipOut` | Sortie membership (user_id, org_id, role) |
| `OrgCreate` | Création d'organisation (name, slug) |
| `OrgOut` | Sortie organisation |

### Workspaces et projets

| Classe | Description |
|--------|-------------|
| `WorkspaceCreate` | Création de workspace (name, org_id) |
| `WorkspaceOut` | Sortie workspace |
| `ProjectCreate` | Création de projet (name, workspace_id, brief, engine) |
| `ProjectOut` | Sortie projet |

### Productions

| Classe | Description |
|--------|-------------|
| `ProductionCreate` | Création de production (project_id, name) |
| `ProductionOut` | Sortie production |

### Shots et patches

| Classe | Description |
|--------|-------------|
| `ShotUpdate` | Mise à jour de shot |
| `PatchCreate` | Création de patch (shot_id, path, op, value) |

### QA et artifacts

| Classe | Description |
|--------|-------------|
| `QAReportOut` | Sortie rapport QA |

---

### 4.9 `api/security.py`

Module de sécurité : hachage de mots de passe, gestion des tokens JWT.

**Constantes :**

| Nom | Type | Valeur | Description |
|-----|------|--------|-------------|
| `_PBKDF2_ITERATIONS` | `int` | `600000` | Nombre d'itérations PBKDF2 |
| `_ALGORITHM` | `str` | `"HS256"` | Algorithme de signature JWT |
| `ACCESS_TOKEN_TTL_HOURS` | `int` | `24` | Durée de vie des access tokens (heures) |
| `REFRESH_TOKEN_TTL_DAYS` | `int` | `30` | Durée de vie des refresh tokens (jours) |

---

**Fonctions :**

#### `hash_password()`

```python
def hash_password(password: str) -> str
```

**Description :** Hache un mot de passe avec PBKDF2-SHA256 + sel aléatoire.

**Valeur de retour :** `str` — hash du mot de passe (format : `iterations:salt:hash`).

---

#### `verify_password()`

```python
def verify_password(password: str, password_hash: str) -> bool
```

**Description :** Vérifie un mot de passe contre son hash.

---

#### `create_token()`

```python
def create_token(payload: dict, secret: str, expires_delta: timedelta | None = None) -> str
```

**Description :** Crée un token JWT signé.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `payload` | `dict` | Données à encoder dans le token |
| `secret` | `str` | Clé secrète pour la signature |
| `expires_delta` | `timedelta \| None` | Durée de vie optionnelle |

**Valeur de retour :** `str` — token JWT encodé.

---

#### `create_refresh_token()`

```python
def create_refresh_token(user_id: str, session: Session, secret: str) -> str
```

**Description :** Crée un refresh token, le stocke en base de données et retourne le token JWT.

---

#### `decode_token_full()`

```python
def decode_token_full(token: str, secret: str) -> dict
```

**Description :** Décode et valide un token JWT, en vérifiant l'expiration.

---

#### `revoke_refresh_token()`

```python
def revoke_refresh_token(token_hash: str, session: Session) -> None
```

**Description :** Révoque un refresh token en base de données.

---

### 4.10 `api/seed.py`

Module de seeding — initialise la base de données avec les données par défaut.

**Constantes :**

| Nom | Valeur | Description |
|-----|--------|-------------|
| `DEFAULT_EMAIL` | `"admin@deepbl4nder.local"` | Email de l'administrateur par défaut |
| `DEFAULT_ORG` | `"DeepBl4nder"` | Nom de l'organisation par défaut |
| `DEFAULT_PROJECT` | `"default"` | Nom du projet par défaut |
| `MIN_PASSWORD_LENGTH` | `8` | Longueur minimale du mot de passe admin |

---

**Classes :**

### `SeedResult`

```python
@dataclasses.dataclass
class SeedResult:
    user_id: str = ""
    org_id: str = ""
    project_id: str = ""
    password: str = ""
```

**Description :** Résultat du seeding contenant les IDs créés et le mot de passe généré.

---

**Fonctions :**

#### `seed_admin()`

```python
def seed_admin(session: Session, secret_key: str) -> SeedResult
```

**Description :** Crée l'utilisateur admin, l'organisation par défaut, et le projet par défaut.

---

#### `main()`

```python
def main() -> None
```

**Description :** Point d'entrée du script de seeding. Initialise la base de données et exécute le seeding.

---

### 4.11 `api/state.py`

État global de l'application API.

**Classes :**

### `WorkerStatus`

```python
class WorkerStatus:
    def __init__(self):
        ...
```

**Description :** Gestionnaire d'état pour le worker de rendu. Gère le verrouillage, les statistiques et le heartbeat.

**Méthodes :**

#### `acquire()`

```python
def acquire(self) -> bool
```

**Description :** Tente d'acquérir le verrou du worker. Retourne `True` si succès.

---

#### `release()`

```python
def release(self) -> None
```

**Description :** Libère le verrou du worker.

---

#### `is_locked()`

```python
def is_locked(self) -> bool
```

**Description :** Vérifie si le worker est actuellement occupé.

---

#### `stats()`

```python
def stats(self) -> dict
```

**Description :** Retourne les statistiques du worker (jobs complétés, erreurs, uptime).

---

#### `heartbeat()`

```python
def heartbeat(self) -> None
```

**Description :** Met à jour le timestamp du dernier heartbeat.

---

**Fonctions module-level :**

#### `get_engine()`

```python
def get_engine() -> Engine
```

**Description :** Retourne le moteur SQLAlchemy global (singleton).

---

#### `get_session_factory()`

```python
def get_session_factory() -> sessionmaker
```

**Description :** Retourne la factory de sessions globale (singleton).

---

#### `get_secret_key()`

```python
def get_secret_key() -> str
```

**Description :** Retourne la clé secrète JWT (depuis `.env` ou générée aléatoirement).

---

#### `set_*()` (setters)

```python
def set_engine(engine: Engine) -> None
def set_session_factory(factory: sessionmaker) -> None
def set_secret_key(key: str) -> None
```

**Description :** Setters pour les singletons globaux de l'API.

---

## 5. Bridge (bridge/)

### 5.1 `bridge/__init__.py`

Module d'export pour le bridge.

**Exports :**

| Symbole | Module source |
|---------|---------------|
| `ProcessResult` | `bridge.worker` |
| `WorkerCommand` | `bridge.worker` |
| `WorkerProcess` | `bridge.worker` |
| `blender_version` | `bridge.worker` |

---

### 5.2 `bridge/worker.py`

Exécution de processus Blender en sous-processus isolé.

**Classes :**

### `ProcessResult`

```python
@dataclasses.dataclass
class ProcessResult:
    ok: bool = True
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_sec: float = 0.0
    output_path: str | None = None
```

**Description :** Résultat de l'exécution d'un processus Blender.

---

### `WorkerCommand`

```python
@dataclasses.dataclass
class WorkerCommand:
    script: str = ""
    blend_file: str | None = None
    output_path: str | None = None
    timeout: float = 300.0
    extra_args: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Commande à exécuter dans le worker Blender.

---

### `WorkerProcess`

```python
class WorkerProcess:
    def __init__(self, blender_path: str | None = None):
        ...
```

**Description :** Processus worker qui exécute des scripts Blender en sous-processus.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `blender_path` | `str \| None` | Chemin vers l'exécutable Blender (auto-détecté si None) |

**Méthodes :**

#### `run()`

```python
def run(self, command: WorkerCommand) -> ProcessResult
```

**Description :** Exécute une commande Blender en sous-processus.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `command` | `WorkerCommand` | La commande à exécuter |

**Valeur de retour :** `ProcessResult` — résultat de l'exécution.

---

**Fonctions module-level :**

#### `blender_version()`

```python
def blender_version(blender_path: str | None = None) -> str | None
```

**Description :** Détecte la version de Blender installée.

**Valeur de retour :** `str | None` — chaîne de version (ex: `"4.1.0"`) ou `None`.

---

#### `_coerce_output()`

```python
def _coerce_output(raw: str) -> str
```

**Description :** Nettoie la sortie brute d'un processus (supprime les caractères de contrôle, normalise l'encodage).

---

## 6. Bridges (bridges/)

### 6.1 `bridges/blender/bridge.py`

Bridge principal pour l'intégration avec Blender.

**Classes :**

### `BlenderNotFoundError`

```python
class BlenderNotFoundError(Exception):
    pass
```

**Description :** Exception levée quand Blender ne peut pas être trouvé sur le système.

---

### `BlenderBridge`

```python
class BlenderBridge:
    def __init__(self, blender_path: str | None = None):
        ...
```

**Description :** Interface de haut niveau pour interagir avec Blender. Fournit des méthodes pour exécuter des scripts, valider des scripts, et gérer des sessions de rendu.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `blender_path` | `str \| None` | Chemin vers Blender (auto-détecté si None) |

**Méthodes :**

#### `run_script()`

```python
def run_script(self, script: str, **kwargs) -> ProcessResult
```

**Description :** Exécute un script Python dans Blender.

---

#### `validate_and_run()`

```python
def validate_and_run(self, script: str, policy: CodePolicy | None = None) -> ProcessResult
```

**Description :** Valide un script contre les politiques de sécurité puis l'exécute dans Blender.

---

**Fonctions module-level :**

#### `_find_blender()`

```python
def _find_blender() -> str
```

**Description :** Détecte automatiquement le chemin de l'exécutable Blender. Cherche dans les emplacements standards (Windows, macOS, Linux).

---

#### `_detect_gpu()`

```python
def _detect_gpu() -> dict
```

**Description :** Détecte le GPU disponible pour le rendu.

**Valeur de retour :** `dict` — informations sur le GPU (nom, type, VRAM).

---

### 6.2 `bridges/blender/scheduler.py`

Ordonnanceur de workers Blender pour le rendu parallèle.

**Classes :**

### `WorkerInfo`

```python
@dataclasses.dataclass
class WorkerInfo:
    id: str = ""
    process: WorkerProcess | None = None
    busy: bool = False
    current_job: str | None = None
    completed: int = 0
    errors: int = 0
```

**Description :** Informations sur un worker Blender individuel.

---

### `WorkerScheduler`

```python
class WorkerScheduler:
    def __init__(self, max_workers: int = 1):
        ...
```

**Description :** Ordonnanceur qui distribue les travaux de rendu sur plusieurs workers Blender.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `max_workers` | `int` | Nombre maximum de workers simultanés |

**Méthodes :**

#### `submit()`

```python
def submit(self, command: WorkerCommand) -> Future[ProcessResult]
```

**Description :** Soumet un travail de rendu à l'ordonnanceur.

---

#### `add_workers()`

```python
def add_workers(self, count: int = 1) -> None
```

**Description :** Ajoute des workers à l'ordonnanceur.

---

#### `shutdown()`

```python
def shutdown(self, wait: bool = True) -> None
```

**Description :** Arrête proprement l'ordonnanceur et tous ses workers.

---

#### `active_count()`

```python
def active_count(self) -> int
```

**Description :** Retourne le nombre de workers actuellement actifs.

---

#### `worker_count()`

```python
def worker_count(self) -> int
```

**Description :** Retourne le nombre total de workers configurés.

---

### 6.3 `bridges/blender/worker.py`

Worker individuel pour l'exécution de rendu Blender.

**Enums :**

### `WorkerStatus`

```python
class WorkerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"
```

**Description :** États possibles d'un worker Blender.

---

**Classes :**

### `BlenderWorker`

```python
@dataclasses.dataclass
class BlenderWorker:
    id: str = ""
    blender_path: str = ""
    status: WorkerStatus = WorkerStatus.IDLE
    current_script: str | None = None
    artifacts: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Représente un worker Blender individuel avec son état et ses artifacts.

**Méthodes :**

#### `render()`

```python
def render(self, command: WorkerCommand) -> ProcessResult
```

**Description :** Exécute un travail de rendu.

---

#### `artifacts()`

```python
def artifacts(self) -> list[str]
```

**Description :** Retourne la liste des fichiers générés par ce worker.

---

#### `cleanup()`

```python
def cleanup(self) -> None
```

**Description :** Nettoie les fichiers temporaires du worker.

---

### 6.4 `bridges/ue5/bridge.py`

Bridge pour l'intégration avec Unreal Engine 5.

**Classes :**

### `UE5ConnectionError`

```python
class UE5ConnectionError(Exception):
    pass
```

**Description :** Exception levée en cas d'échec de connexion à UE5.

---

### `UE5CommandError`

```python
class UE5CommandError(Exception):
    pass
```

**Description :** Exception levée en cas d'erreur d'exécution d'une commande UE5.

---

### `UE5CommandResult`

```python
@dataclasses.dataclass
class UE5CommandResult:
    success: bool = True
    command: str = ""
    output: str = ""
    error: str | None = None
    duration_sec: float = 0.0
```

**Description :** Résultat de l'exécution d'une commande UE5.

---

### `UE5Bridge`

```python
class UE5Bridge:
    def __init__(self, host: str = "localhost", port: int = 8080, timeout: float = 30.0):
        ...
```

**Description :** Interface de communication avec Unreal Engine 5 via HTTP/WebSocket.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `host` | `str` | Adresse du serveur UE5 |
| `port` | `int` | Port de communication |
| `timeout` | `float` | Timeout des requêtes (secondes) |

**Méthodes :**

#### `health()`

```python
def health(self) -> bool
```

**Description :** Vérifie la connexion à UE5.

---

#### `send_command()`

```python
def send_command(self, command: UE5Command) -> UE5CommandResult
```

**Description :** Envoie une commande individuelle à UE5.

---

#### `send_commands()`

```python
def send_commands(self, commands: UE5Commands) -> list[UE5CommandResult]
```

**Description :** Envoie une séquence de commandes à UE5.

---

#### `create_level()`

```python
def create_level(self, name: str) -> UE5CommandResult
```

**Description :** Crée un nouveau level dans UE5.

---

#### `setup_material()`

```python
def setup_material(self, target: str, material_params: dict) -> UE5CommandResult
```

**Description :** Configure un matériau sur un acteur.

---

#### `setup_lighting()`

```python
def setup_lighting(self, lights: list[LightingSpec]) -> UE5CommandResult
```

**Description :** Configure l'éclairage de la scène.

---

#### `setup_animation()`

```python
def setup_animation(self, target: str, animation_params: dict) -> UE5CommandResult
```

**Description :** Configure l'animation d'un acteur.

---

#### `render_movie()`

```python
def render_movie(self, output_path: str, params: dict) -> UE5CommandResult
```

**Description :** Lance le rendu vidéo dans UE5.

---

## 7. Codegen (codegen/)

### 7.1 `codegen/__init__.py`

Module d'export pour le codegen.

**Exports :**

| Symbole | Module source |
|---------|---------------|
| `ALLOWED_IMPORTS` | `codegen.policy` |
| `FORBIDDEN_BUILTINS` | `codegen.policy` |
| `CodePolicyViolation` | `codegen.policy` |
| `CodePolicy` | `codegen.policy` |
| `ValidationReport` | `codegen.validator` |
| `ASTValidator` | `codegen.validator` |
| `validate_for_worker` | `codegen.validator` |

---

### 7.2 `codegen/policy.py`

Politiques de sécurité pour la validation de code généré.

**Constantes :**

#### `ALLOWED_IMPORTS`

```python
ALLOWED_IMPORTS: frozenset[str] = frozenset({
    "math", "random", "json", "os", "sys", "time", "datetime",
    "pathlib", "typing", "dataclasses", "collections",
    "itertools", "functools", "operator", "string", "re",
    "bpy", "bmesh", "mathutils", "gpu", "blf", "bgl",
    # ... autres modules autorisés
})
```

**Description :** Ensemble des modules Python autorisés à être importés par les scripts générés. Tout import hors de cette liste est considéré comme une violation de sécurité.

---

#### `FORBIDDEN_BUILTINS`

```python
FORBIDDEN_BUILTINS: frozenset[str] = frozenset({
    "eval", "exec", "compile", "__import__",
    "open", "input", "breakpoint", "exit", "quit",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr",
})
```

**Description :** Ensemble des builtins Python interdits dans le code généré. Ces fonctions peuvent compromettre la sécurité ou l'intégrité du système.

---

**Classes :**

### `CodePolicyViolation`

```python
class CodePolicyViolation(Exception):
    def __init__(self, message: str, violations: list[dict]):
        ...
```

**Description :** Exception levée lorsqu'un script viole les politiques de code.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `message` | `str` | Message d'erreur global |
| `violations` | `list[dict]` | Liste détaillée des violations détectées |

---

### `CodePolicy`

```python
@dataclasses.dataclass
class CodePolicy:
    allowed_imports: frozenset[str] = ALLOWED_IMPORTS
    forbidden_builtins: frozenset[str] = FORBIDDEN_BUILTINS
    max_lines: int = 5000
    allow_file_ops: bool = False
    allow_subprocess: bool = False
```

**Description :** Politique de sécurité complète pour la validation de code.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `allowed_imports` | `frozenset[str]` | Modules autorisés |
| `forbidden_builtins` | `frozenset[str]` | Builtins interdits |
| `max_lines` | `int` | Nombre maximum de lignes autorisées |
| `allow_file_ops` | `bool` | Autoriser les opérations fichier |
| `allow_subprocess` | `bool` | Autoriser l'exécution de sous-processus |

---

### 7.3 `codegen/validator.py`

Validateur AST (Abstract Syntax Tree) pour les scripts Python générés.

**Classes :**

### `ValidationReport`

```python
@dataclasses.dataclass
class ValidationReport:
    valid: bool = True
    violations: list[dict] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    stats: dict = dataclasses.field(default_factory=dict)
```

**Description :** Rapport de validation d'un script Python.

**Attributs :**

| Attribut | Type | Description |
|----------|------|-------------|
| `valid` | `bool` | `True` si le script passe toutes les vérifications |
| `violations` | `list[dict]` | Liste des violations détectées (type, message, ligne) |
| `warnings` | `list[str]` | Avertissements non bloquants |
| `stats` | `dict` | Statistiques (nombre de lignes, imports, fonctions, etc.) |

---

### `ASTValidator`

```python
class ASTValidator:
    def __init__(self, policy: CodePolicy | None = None):
        ...
```

**Description :** Validateur de code Python par analyse AST. Parse le code source et vérifie conformément à la politique de sécurité.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `policy` | `CodePolicy \| None` | Politique à utiliser (défaut : `CodePolicy()` par défaut) |

**Méthodes :**

#### `validate()`

```python
def validate(self, source: str) -> ValidationReport
```

**Description :** Valide un script Python complet.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Code source Python à valider |

**Valeur de retour :** `ValidationReport` — rapport de validation complet.

---

#### `_check_imports()`

```python
def _check_imports(self, tree: ast.Module) -> list[dict]
```

**Description :** Vérifie que tous les imports sont dans la liste autorisée.

---

#### `_check_builtins()`

```python
def _check_builtins(self, tree: ast.Module) -> list[dict]
```

**Description :** Vérifie qu'aucun builtin interdit n'est utilisé.

---

#### `_check_file_ops()`

```python
def _check_file_ops(self, tree: ast.Module) -> list[dict]
```

**Description :** Vérifie les opérations sur les fichiers (si interdites par la politique).

---

#### `_check_subprocess()`

```python
def _check_subprocess(self, tree: ast.Module) -> list[dict]
```

**Description :** Vérifie l'utilisation de sous-processus (si interdits par la politique).

---

#### `_check_semantic()`

```python
def _check_semantic(self, tree: ast.Module) -> list[dict]
```

**Description :** Vérifications sémantiques supplémentaires (complexité, patterns dangereux, etc.).

---

**Fonctions module-level :**

#### `validate_for_worker()`

```python
def validate_for_worker(source: str) -> ValidationReport
```

**Description :** Fonction de commodité qui valide un script avec la politique par défaut du worker.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Code source à valider |

**Valeur de retour :** `ValidationReport` — rapport de validation.

---

## 8. Skills (skills/)

### 8.1 `skills/registry.py`

Registre des skills (compétences) disponibles pour les agents.

**Classes :**

### `SkillInfo`

```python
@dataclasses.dataclass
class SkillInfo:
    name: str = ""
    description: str = ""
    path: str = ""
    version: str = ""
    author: str = ""
    tags: list[str] = dataclasses.field(default_factory=list)
```

**Description :** Métadonnées d'un skill.

---

### `SkillRegistry`

```python
class SkillRegistry:
    def __init__(self, base_dir: str | Path | None = None):
        ...
```

**Description :** Registre centralisé des skills. Découvre automatiquement les skills disponibles dans les répertoires configurés.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `base_dir` | `str \| Path \| None` | Répertoire de base pour la découverte des skills |

**Méthodes :**

#### `discover()`

```python
def discover(self) -> list[SkillInfo]
```

**Description :** Parcourt les répertoires de skills et retourne la liste de tous les skills disponibles.

**Valeur de retour :** `list[SkillInfo]` — liste des skills découverts.

---

#### `resolve()`

```python
def resolve(self, name: str) -> SkillInfo | None
```

**Description :** Résout un skill par son nom.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Nom du skill à résoudre |

**Valeur de retour :** `SkillInfo | None` — le skill trouvé ou `None`.

---

#### `resolve_all()`

```python
def resolve_all(self, names: list[str]) -> list[SkillInfo]
```

**Description :** Résout plusieurs skills par leurs noms.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `names` | `list[str]` | Noms des skills à résoudre |

**Valeur de retour :** `list[SkillInfo]` — skills trouvés (ignore ceux qui n'existent pas).

---

**Fonctions module-level :**

#### `get_default_registry()`

```python
def get_default_registry() -> SkillRegistry
```

**Description :** Retourne une instance du registre avec les répertoires par défaut.

**Valeur de retour :** `SkillRegistry` — le registre par défaut.

---

#### `_read_description()`

```python
def _read_description(path: Path) -> str
```

**Description :** Lit la description d'un skill depuis son fichier (première ligne ou champ de métadonnées).

---

## 9. QA (qa/)

### 9.1 `qa/visual.py`

Module de QA visuelle basé sur l'analyse de fichiers vidéo/image.

**Classes :**

### `VisualQAResult`

```python
@dataclasses.dataclass
class VisualQAResult:
    valid: bool = True
    duration_sec: float = 0.0
    resolution: tuple[int, int] = (0, 0)
    issues: list[str] = dataclasses.field(default_factory=list)
    black_detect: list[dict] = dataclasses.field(default_factory=list)
    metadata: dict = dataclasses.field(default_factory=dict)
```

**Description :** Résultat de l'analyse QA visuelle d'un fichier vidéo/image.

---

**Fonctions :**

#### `_run_ffprobe()`

```python
def _run_ffprobe(file_path: str) -> dict
```

**Description :** Exécute `ffprobe` pour extraire les métadonnées d'un fichier média.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Chemin vers le fichier média |

**Valeur de retour :** `dict` — métadonnées extraites (résolution, durée, codec, etc.).

---

#### `_run_blackdetect()`

```python
def _run_blackdetect(file_path: str) -> list[dict]
```

**Description :** Exécute le filtre `blackdetect` de FFmpeg pour détecter les segments noirs dans une vidéo.

**Valeur de retour :** `list[dict]` — liste des segments noirs détectés (start, end, duration).

---

#### `visual_qa()`

```python
def visual_qa(file_path: str) -> VisualQAResult
```

**Description :** Analyse QA visuelle complète d'un fichier vidéo ou image. Combine ffprobe et blackdetect.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Chemin vers le fichier à analyser |

**Valeur de retour :** `VisualQAResult` — résultat de l'analyse.

---

## 10. Assets (assets/)

### 10.1 `assets/characters.py`

Client pour la recherche et le téléchargement de personnages 3D gratuits.

**Constantes :**

| Nom | Valeur | Description |
|-----|--------|-------------|
| `QUATERNIUS_API` | `"https://api.quaternius.com"` | URL de l'API Quaternius |
| `POLYHAVEN_MODELS_API` | `"https://api.polyhaven.com/assets"` | URL de l'API PolyHaven (modèles) |

---

**Classes :**

### `CharacterAssetClient`

```python
class CharacterAssetClient:
    def __init__(self, cache_dir: str | Path | None = None):
        ...
```

**Description :** Client pour rechercher et télécharger des personnages 3D depuis des sources gratuites (Quaternius, PolyHaven).

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `cache_dir` | `str \| Path \| None` | Répertoire de cache local pour les téléchargements |

**Méthodes :**

#### `search()`

```python
def search(self, query: str, limit: int = 10) -> list[dict]
```

**Description :** Recherche des personnages par mot-clé sur toutes les sources configurées.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Requête de recherche |
| `limit` | `int` | Nombre maximum de résultats |

**Valeur de retour :** `list[dict]` — liste des résultats (nom, source, URL de téléchargement, tags).

---

#### `download()`

```python
def download(self, asset_url: str, destination: str | Path) -> Path
```

**Description :** Télécharge un asset vers le répertoire de destination.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `asset_url` | `str` | URL de téléchargement de l'asset |
| `destination` | `str \| Path` | Répertoire de destination |

**Valeur de retour :** `Path` — chemin du fichier téléchargé.

---

#### `_search_quaternius()`

```python
def _search_quaternius(self, query: str, limit: int) -> list[dict]
```

**Description :** Recherche sur l'API Quaternius.

---

#### `_search_polyhaven_models()`

```python
def _search_polyhaven_models(self, query: str, limit: int) -> list[dict]
```

**Description :** Recherche sur l'API PolyHaven (catégorie modèles).

---

#### `_download_file()`

```python
def _download_file(self, url: str, destination: Path) -> Path
```

**Description :** Télécharge un fichier depuis une URL avec gestion du cache.

---

### 10.2 `assets/polyhaven.py`

Client pour l'API PolyHaven (HDRIs, textures, modèles).

**Constantes :**

| Nom | Valeur | Description |
|-----|--------|-------------|
| `POLYHAVEN_API_BASE` | `"https://api.polyhaven.com"` | URL de base de l'API PolyHaven |

---

**Classes :**

### `PolyHavenClient`

```python
class PolyHavenClient:
    def __init__(self, cache_dir: str | Path | None = None):
        ...
```

**Description :** Client pour interagir avec l'API PolyHaven. Permet de rechercher et télécharger des HDRIs, textures et modèles 3D gratuits.

**Constructeur :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `cache_dir` | `str \| Path \| None` | Répertoire de cache local |

**Méthodes :**

#### `search()`

```python
def search(self, query: str, asset_type: str = "hdris", limit: int = 10) -> list[dict]
```

**Description :** Recherche des assets sur PolyHaven.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Requête de recherche |
| `asset_type` | `str` | Type d'asset (`"hdris"`, `"textures"`, `"models"`) |
| `limit` | `int` | Nombre maximum de résultats |

**Valeur de retour :** `list[dict]` — résultats de recherche.

---

#### `get_files()`

```python
def get_files(self, asset_name: str) -> dict
```

**Description :** Récupère les fichiers disponibles pour un asset donné.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `asset_name` | `str` | Nom de l'asset PolyHaven |

**Valeur de retour :** `dict` — dictionnaire des fichiers disponibles (résolution → URL).

---

#### `download_hdri()`

```python
def download_hdri(self, name: str, resolution: str = "2k", destination: str | Path | None = None) -> Path
```

**Description :** Télécharge un HDRI depuis PolyHaven.

**Paramètres :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Nom de l'HDRI |
| `resolution` | `str` | Résolution souhaitée (ex: `"1k"`, `"2k"`, `"4k"`) |
| `destination` | `str \| Path \| None` | Répertoire de destination (défaut : cache) |

**Valeur de retour :** `Path` — chemin du fichier téléchargé.

---

#### `download_texture()`

```python
def download_texture(self, name: str, resolution: str = "2k", destination: str | Path | None = None) -> Path
```

**Description :** Télécharge une texture depuis PolyHaven.

---

#### `_download_file()`

```python
def _download_file(self, url: str, destination: Path) -> Path
```

**Description :** Télécharge un fichier avec gestion du cache.

---

## Annexe : Vue d'ensemble de l'architecture

```
deepblender/
├── __init__.py          # Initialisation, shims Windows, .env
├── cli.py               # CLI (inspect, validate, serve, seed)
├── llm.py               # Routage LLM, fournisseurs, discovery
├── logging_setup.py     # Configuration logging
├── nooa_compat.py       # Monkeypatch NOOA
│
├── agents/              # 17 agents (tous héritent de BaseAgent)
│   ├── base.py          # BaseAgent, DefaultsMixin, postconditions
│   ├── story.py         # StoryAgent → StorySpec
│   ├── board.py         # StoryboardAgent → StoryboardSpec
│   ├── director.py      # DirectorAgent → SceneSpec
│   ├── blender.py       # BlenderAgent → BlenderScript (Reflexion)
│   ├── char.py          # CharacterDesignerAgent → CharacterDesignResult
│   ├── env.py           # EnvironmentArtistAgent → EnvironmentDesignResult
│   ├── animator.py      # AnimatorAgent → AnimationResult
│   ├── audio.py         # AudioAgent → AudioPlan
│   ├── comp.py          # CompositingAgent → CompositeSpec
│   ├── loc.py           # LocalizationAgent → LanguagePackage
│   ├── music.py         # MusicComposerAgent → MusicPlan
│   ├── sfx.py           # SoundDesignerAgent → SoundDesignPlan
│   ├── qa.py            # QAAgent → QAReport
│   ├── review.py        # ReviewAgent → ReviewReport
│   └── ue5.py           # UE5Agent → UE5Commands
│
├── domain/              # Types de domaine (dataclasses)
│   ├── scene.py         # SceneSpec, ShotSpec, CameraSpec, LightingSpec...
│   ├── narrative.py     # StorySpec, StoryboardSpec, Act, StoryBeat...
│   ├── media.py         # AnimationResult, AudioPlan, CompositeSpec...
│   ├── qa.py            # QAReport, QAStatus, Issue, IssueKind
│   ├── project.py       # Project, Brief, Sequence, Shot
│   ├── patch.py         # Patch, apply_patch, apply_patches
│   ├── asset.py         # Asset, AssetKind, sha256_of_file
│   ├── ue5.py           # UE5Command, UE5Commands
│   └── utils.py         # new_id()
│
├── api/                 # API FastAPI + SQLAlchemy
│   ├── app.py           # create_app(), toutes les routes
│   ├── bus.py           # AsyncEventBus (SSE)
│   ├── db.py            # Base, create_engine_for, create_session_factory
│   ├── deps.py          # Dépendances auth, rôles, scoped access
│   ├── models.py        # ORM: User, Organization, Project, Production...
│   ├── pipeline.py      # run_production(), build_agents()
│   ├── schemas.py       # Pydantic schemas (entrées/sorties API)
│   ├── security.py      # hash_password, create_token, JWT
│   ├── seed.py          # seed_admin(), DEFAULT_EMAIL/ORG/PROJECT
│   └── state.py         # WorkerStatus, get_engine, get_secret_key
│
├── bridge/              # Bridge processus Blender
│   └── worker.py        # WorkerProcess, WorkerCommand, ProcessResult
│
├── bridges/             # Bridges moteurs 3D
│   ├── blender/
│   │   ├── bridge.py    # BlenderBridge, _find_blender, _detect_gpu
│   │   ├── scheduler.py # WorkerScheduler, WorkerInfo
│   │   └── worker.py    # BlenderWorker, WorkerStatus
│   └── ue5/
│       └── bridge.py    # UE5Bridge (health, send_command, render_movie...)
│
├── codegen/             # Validation de code
│   ├── policy.py        # CodePolicy, ALLOWED_IMPORTS, FORBIDDEN_BUILTINS
│   └── validator.py     # ASTValidator, ValidationReport
│
├── skills/              # Registre des skills
│   └── registry.py      # SkillRegistry, SkillInfo, get_default_registry
│
├── qa/                  # QA visuelle
│   └── visual.py        # VisualQAResult, visual_qa, _run_ffprobe
│
└── assets/              # Client de téléchargement d'assets
    ├── characters.py    # CharacterAssetClient (Quaternius, PolyHaven)
    └── polyhaven.py     # PolyHavenClient (HDRIs, textures, modèles)
```

---

*Généré automatiquement pour DeepBl4nder v0.2.0*
