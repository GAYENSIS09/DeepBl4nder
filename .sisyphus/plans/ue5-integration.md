# Plan : Intégration Unreal Engine 5

## Contexte

DeepBlender a un pipeline fonctionnel avec Blender. L'architecture retenue (Option C) garde BlenderAgent intact et ajoute des agents séparés pour chaque moteur. UE5 est le premier moteur à intégrer après Blender.

UE5 est fondamentalement différent de Blender :
- **Pas de script Python** : UE5 s'exécute comme un serveur avec REST API
- **Lumen** : Global illumination temps réel (pas de Cycles)
- **Nanite** : Géométrie virtualisée (pas de mesh traditionnel)
- **MRQ** : Movie Render Queue pour le rendu haute qualité
- **Sequencer** : Animation par tracks (pas de keyframes bpy)

## Architecture

```
SceneSpec (commun)
  ├── Renderer="BLENDER" → BlenderAgent → BlenderBridge → blender -b -P
  └── Renderer="UE5"     → UE5Agent    → UE5Bridge    → REST API → UE5 Server
```

---

## Étape 1 : Domaine — Étendre RenderSpec

**Fichier** : `deepblender/domain/scene.py`

### 1a. Ajouter les moteurs supportés

```python
@dataclass
class RenderSpec:
    # ... existant ...
    engine: str = "CYCLES"  # CYCLES | EEVEE | BLENDER | UE5 | GODOT | AI_VIDEO
```

Le champ `engine` existant accepte déjà `"CYCLES"` et `"EEVEE"`. Étendre pour :
- `"BLENDER"` — alias pour CYCLES (rétrocompatibilité)
- `"UE5"` — Unreal Engine 5 via REST API
- `"GODOT"` — Godot 4 headless
- `"AI_VIDEO"` — CogVideoX / Wan2.1

### 1b. Ajouter les settings UE5

```python
@dataclass
class UE5RenderSpec:
    """Settings spécifiques à UE5."""
    use_lumen: bool = True
    use_nanite: bool = True
    use_ray_tracing: bool = False
    quality_preset: str = "cinematic"  # epic | cinematic
    console_variables: dict[str, float] = field(default_factory=dict)
```

Ajouter `ue5_settings: UE5RenderSpec | None = None` à `RenderSpec`.

**Fichiers modifiés** : `scene.py`

---

## Étape 2 : UE5Bridge — Client REST pour UE5

**Fichier à créer** : `deepblender/bridges/ue5/bridge.py`

### 2a. Classe UE5Bridge

```python
class UE5Bridge:
    """Client REST pour communiquer avec un serveur UE5."""

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 60.0):
        self._base_url = base_url
        self._timeout = timeout
        self._session = requests.Session()

    def available(self) -> bool:
        """Vérifie si le serveur UE5 est accessible."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def create_level(self, name: str, template: str = "empty") -> dict:
        """Crée un niveau dans UE5."""
        return self._command("level/create", {"name": name, "template": template})

    def import_asset(self, asset_path: str, destination: str) -> dict:
        """Importe un asset (.fbx, .gltf, .uasset) dans UE5."""
        return self._command("asset/import", {
            "source": asset_path,
            "destination": destination,
        })

    def create_material(self, name: str, properties: dict) -> dict:
        """Crée un matériau Lumen dans UE5."""
        return self._command("material/create", {"name": name, **properties})

    def setup_lighting(self, lights: list[dict]) -> dict:
        """Configure l'éclairage Lumen."""
        return self._command("lighting/setup", {"lights": lights})

    def setup_sequencer(self, sequence: dict) -> dict:
        """Configure le Sequencer pour l'animation."""
        return self._command("sequencer/setup", sequence)

    def render(self, output_path: str, settings: dict) -> dict:
        """Lance le rendu via MRQ (Movie Render Queue)."""
        return self._command("render/start", {
            "output": output_path,
            **settings,
        })

    def _command(self, endpoint: str, payload: dict) -> dict:
        resp = self._session.post(
            f"{self._base_url}/{endpoint}",
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()
```

### 2b. UE5 Render Pipeline (côté UE5)

Le serveur UE5 doit avoir un plugin Python qui écoute les commandes REST. C'est un code C++/Python qui s'exécute DANS UE5 :

```
UE5 Server (port 8080)
  ├── /health → status
  ├── /level/create → crée un Level
  ├── /asset/import → importe un .fbx/.gltf
  ├── /material/create → crée un matériau Lumen
  ├── /lighting/setup → place les lights
  ├── /sequencer/setup → configure l'animation
  └── /render/start → MRQ render
```

**Fichiers créés** :
- `deepblender/bridges/ue5/__init__.py`
- `deepblender/bridges/ue5/bridge.py`

---

## Étape 3 : UE5Agent — Agent NOOA pour UE5

**Fichier à créer** : `deepblender/agents/ue5.py`

### 3a. Classe UE5Agent

```python
class UE5Agent(BaseAgent, DefaultsMixin):
    """Agent NOOA pour Unreal Engine 5.

    Transforme une SceneSpec en commandes REST pour UE5.
    Utilise les skills : unreal-engine.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bridge: UE5Bridge | None = None

    @strategy(CodeActStrategy(config=CodeActConfig(
        postconditions=[ue5_commands_postcondition],
        max_tokens=16384,
    )))
    async def build_commands(self, spec: SceneSpec) -> UE5Commands:
        """Génère les commandes REST pour créer la scène dans UE5.

        Steps:
        1. Load unreal-engine skill
        2. Analyze SceneSpec
        3. Generate REST commands:
           - level/create
           - asset/import (characters, HDRI)
           - material/create (Lumen PBR)
           - lighting/setup (3-point + Lumen)
           - sequencer/setup (camera tracks, animation)
           - render/start (MRQ settings)
        4. Return UE5Commands
        """
        self._load_core_skills()
        self._load_skill("unreal-engine")
        ...
```

### 3b. UE5Commands (domain model)

```python
@dataclass
class UE5Commands:
    """Séquence de commandes REST pour UE5."""
    level_name: str
    commands: list[dict]  # [{"endpoint": "level/create", "payload": {...}}, ...]
    version: int = 1
```

### 3c. Postcondition

```python
def ue5_commands_postcondition(agent, result, call):
    if not isinstance(result, UE5Commands):
        return
    if not result.commands:
        raise InvariantError("UE5Commands doit contenir au moins une commande")
```

**Fichiers créés** :
- `deepblender/agents/ue5.py`
- `deepblender/domain/ue5.py` (UE5Commands, UE5RenderSpec)

---

## Étape 4 : Wiring dans le Runner

**Fichier** : `deepblender/production/runner.py`

### 4a. Ajouter l'agent UE5

Dans `PipelineRunner.__init__()` :
```python
self.ue5 = UE5Agent(...)
```

### 4b. Modifier `_build()` pour le routing

```python
async def _build(self, scene: SceneSpec) -> tuple[Any, Path]:
    engine = scene.render.engine.upper()

    if engine in ("CYCLES", "EEVEE", "BLENDER", ""):
        # Blender (default)
        return await self._build_blender(scene)
    elif engine == "UE5":
        return await self._build_ue5(scene)
    elif engine == "GODOT":
        return await self._build_godot(scene)
    elif engine == "AI_VIDEO":
        return await self._build_ai_video(scene)
    else:
        raise ValueError(f"Unknown render engine: {engine}")
```

### 4c. Méthode `_build_ue5()`

```python
async def _build_ue5(self, scene: SceneSpec) -> tuple[UE5Commands, Path]:
    """Génère et exécute les commandes UE5."""
    commands = await self.ue5.build_commands(scene)

    # Exécuter les commandes via UE5Bridge
    if self.ue5_bridge and self.ue5_bridge.available():
        for cmd in commands.commands:
            self.ue5_bridge._command(cmd["endpoint"], cmd["payload"])

    # Sauvegarder les commandes
    path = self.workdir / "ue5_commands.json"
    path.write_text(json.dumps(asdict(commands)), encoding="utf-8")

    return commands, path
```

**Fichiers modifiés** : `runner.py`

---

## Étape 5 : Skills UE5 (déjà existants)

**Fichier** : `deepblender/skills/unreal-engine/SKILL.md`

Le skill existe déjà avec 134 lignes de documentation sur :
- Level creation
- Materials (Lumen)
- Lighting
- MRQ rendering
- Sequencer animation

**Action** : Enrichir le skill avec des exemples concrets de commandes REST.

---

## Étape 6 : Tests

**Fichiers à créer** :
- `tests/test_ue5_bridge.py` — tests du client REST
- `tests/test_ue5_agent.py` — tests de génération de commandes
- `tests/test_runner_engine_routing.py` — tests du routing multi-engine

**Tests à modifier** :
- `tests/test_decoupling.py` — ajouter UE5Agent aux exports
- `tests/test_runner.py` — ajouter test pour engine="UE5"

---

## Résumé des fichiers

| Fichier | Action |
|---------|--------|
| `deepblender/domain/scene.py` | MODIFIER — ajouter UE5RenderSpec, étendre engine |
| `deepblender/domain/ue5.py` | CRÉER — UE5Commands |
| `deepblender/bridges/ue5/__init__.py` | CRÉER |
| `deepblender/bridges/ue5/bridge.py` | CRÉER — UE5Bridge |
| `deepblender/agents/ue5.py` | CRÉER — UE5Agent |
| `deepblender/production/runner.py` | MODIFIER — routing engine |
| `deepblender/skills/unreal-engine/SKILL.md` | ENRICHIR |
| `tests/test_ue5_bridge.py` | CRÉER |
| `tests/test_ue5_agent.py` | CRÉER |
| `tests/test_runner_engine_routing.py` | CRÉER |

## Dépendances UE5 (côté serveur)

Pour que UE5Bridge fonctionne, il faut un serveur UE5 avec :
- Plugin Python pour UE5 (unreal module)
- Serveur REST (Flask/FastAPI) qui écoute sur :8080
- MRQ configuré pour le rendu headless

C'est un projet séparé (UE5 C++ plugin) qui sera documenté dans `docs/ue5-server/`.

## Risques

- **UE5 doit tourner** : le bridge ne fonctionne que si un serveur UE5 est accessible
- **Pas de fallback** : si UE5 n'est pas disponible, le pipeline échoue (pas de script déterministe comme Blender)
- **Latence** : les appels REST sont plus lents que l'exécution locale
- **MRQ licensing** : UE5 a une licence pour le rendu commercial
