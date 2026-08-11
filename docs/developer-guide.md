# Guide du développeur

Ce guide décrit comment contribuer au paquet `deepblender`. L'architecture est
détaillée dans [`docs/architecture/`](architecture/README.md).

## Structure du paquet

```text
deepblender/
├── agents/          # Sous-classes de nooa.Agent (director, blender, qa)
├── domain/          # Objets métier typés (Project, SceneSpec, QAReport, …)
├── skills/          # Mécanique de skills (registry) + SKILL.md embarqués
├── blender/         # Bridge, worker et scheduler Blender
├── codegen/         # Génération/validation AST et politique de code
├── artifacts/       # Registry, versioning et provenance
├── production/      # ProductionRun, budget
├── bridge/          # Frontière de processus isolée (workers)
├── api/             # Gateway HTTP minimale (stdlib)
└── cli.py           # Point d'entrée `deepblender`
```

## Règle de séparation NOOA ↔ domaine

- **Les agents** héritent de `nooa.Agent` : méthodes `async def ...` = capacités
  agentiques, corps Python normal = logique déterministe (P1-P3).
- **Le domaine, le codegen, les artifacts, la production, le bridge et l'API
  n'importent JAMAIS `nooa`** : testé par `tests/test_decoupling.py`.
  NOOA n'est encapsulé que derrière les agents et le mécanisme de skills.

> Si un besoin ressemble à `GenericAgentRuntime`, `GenericEventBus`, etc. :
> c'est que NOOA sait déjà le faire — utiliser NOOA (voir `02-principes.md`).

## Ajouter un agent

1. Créer `deepblender/agents/mon_agent.py` :
   ```python
   from nooa import Agent

   class MonAgent(Agent):
       """You are … (docstring = prompt système)."""

       def helper_deterministe(self, x: int) -> int:
           return x * 2

       async def action_agentique(self, spec: MySpec) -> MyResult:
           """Description de l'action."""
           ...
   ```
2. Exporter dans `deepblender/agents/__init__.py`.
3. Ajouter un test dans `tests/test_decoupling.py` (sous-classe de `nooa.Agent`,
   méthode agentique en coroutine, corps déterministes purs).
4. L'instanciation en test nécessite un LLM : `FakeLLMClient()` de NOOA.

## Ajouter un skill

1. Créer `deepblender/skills/<nom>/SKILL.md` avec frontmatter
   `name:` / `description:` puis les règles. `SkillRegistry` le découvre
   automatiquement ; `TextSkill` (NOOA) gère le chargement.
2. La description est injectée à bas coût (progressive disclosure) ;
   le contenu complet n'est chargé qu'à la résolution.

## Ajouter un objet métier

Créer un dataclass typé dans `deepblender/domain/`, l'exporter dans
`__init__.py`, et l'utiliser comme type de retour d'une capacité agentique
(contrat de sortie).

## Exécuter un script Blender (frontière isolée)

```python
from deepblender.blender.bridge import BlenderBridge
from deepblender.domain.scene import BlenderScript

bridge = BlenderBridge()                     # binaire via BLENDER_EXE
result = bridge.run_script(script, workdir)  # blender -b -P <script>
```

Le script doit d'abord passer `ASTValidator` (imports autorisés, pas de
`exec`/`eval`/`subprocess`/`os.system`, pas d'accès réseau).

## Comptes, rôles et seed de développement

Il n'existe **aucun compte pré-créé** : la base (`deepblender.db` par défaut)
est créée vide au premier démarrage. Chaque inscription (`/api/auth/register`
ou l'écran d'inscription) crée un utilisateur **`owner`** d'une nouvelle
organisation avec un workspace `Default`.

### Modèle de rôles (RBAC par organisation)

| Rôle | Lecture | Écriture | Gestion (membres, suppression projet) |
|---|---|---|---|
| `owner` | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ |
| `editor` | ✅ | ✅ | ❌ |
| `viewer` | ✅ | ❌ | ❌ |

L'`owner` attribue un rôle à un membre via `POST /api/organizations/{id}/members`
(`role` : `owner`/`admin`/`editor`/`viewer`). Il n'y a pas de « super-admin »
global.

### Seed de développement (compte admin)

Pour disposer d'un compte `admin` + org/projet de démo prêt à l'emploi,
idempotent (ne crée que ce qui manque) :

```bash
python -m deepblender.api.seed --email admin@deepblender.local --password admin-dev-123
```

Ou via la CLI globale :

```bash
deepblender seed --email admin@deepblender.local --password admin-dev-123
```

Options : `--db` (URL ou fichier SQLite), `--email`, `--password`, `--org`
(défaut `DeepBlender Dev`), `--project` (défaut `Démo`). Elles se passent
aussi par l'environnement (`DEEPBLENDER_SEED_EMAIL`, `DEEPBLENDER_SEED_PASSWORD`,
`DEEPBLENDER_SEED_ORG`, `DEEPBLENDER_SEED_PROJECT`).

> **Sécurité** : aucun mot de passe n'est en dur dans le code ni ce guide.
> Sans `--password`/`DEEPBLENDER_SEED_PASSWORD`, un mot de passe aléatoire est
> généré et affiché une seule fois en sortie. Le mot de passe doit faire au
> moins 8 caractères.

## Vérifications

```bash
python -m ruff check deepblender tests
python -m mypy deepblender tests
python -m pytest -q
python -m pytest tests/test_decoupling.py -q   # découplage NOOA ↔ legacy
```

## Déploiement

`Dockerfile` : python 3.12-slim + Blender + ffmpeg + `pip install .` (avec NOOA).
`docker-compose.yml` : gateway HTTP + worker jetable + ollama (LLM local via
`LLM_BASE_URL` / `LLM_API_KEY`).
