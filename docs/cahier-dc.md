DEEPBLENDER / NOOA — CAHIER DE CONCEPTION PRODUIT ET TECHNIQUE
Version de cadrage : 1.0
Date : 21 août 2026

============================================================
0. VISION
============================================================

Objectif :
Construire une plateforme professionnelle de production audiovisuelle pilotée par agents IA, capable de transformer une intention utilisateur en œuvre audiovisuelle exploitable : publicité, animation, court métrage, séquence cinématique, vidéo explicative, clip, contenu social, scène de manga/anime, visualisation produit ou autre format.

Principe directeur :
L'IA ne doit pas être considérée comme un unique générateur de vidéo. La plateforme doit reproduire, structurer puis améliorer le flux de travail d'une équipe de production : direction, scénario, storyboard, préproduction, conception visuelle, personnages, décors, animation, caméra, éclairage, audio, voix, montage, rendu, contrôle qualité et itération.

Le produit doit être :
- observable ;
- itératif ;
- traçable ;
- reproductible ;
- extensible ;
- commercialisable ;
- capable de fonctionner avec plusieurs fournisseurs de modèles ;
- capable de survivre au remplacement d'un LLM, d'un moteur 3D ou d'un fournisseur audio.

Idée fondamentale :
NE PAS construire « un agent qui génère une vidéo ».
Construire un « système de production audiovisuelle agentique » dont les agents produisent et contrôlent des artefacts.

============================================================
1. PRINCIPES NON NÉGOCIABLES
============================================================

1.1 Séparer intention, plan, artefacts et exécution.

Utilisateur :
  « Je veux une scène de guerre manga de 45 secondes, sombre, épique,
   avec deux personnages, pluie, explosions, musique originale et narration. »

Le système doit transformer cela en :
  Intent
    -> Creative Brief
    -> Production Plan
    -> Scene Graph / Shot List
    -> Asset Plan
    -> Animation Plan
    -> Audio Plan
    -> Render Plan
    -> QA
    -> Delivery

1.2 Les agents ne doivent jamais être la source unique de vérité.

La source de vérité est l'état persistant du projet :
- project;
- sequence;
- scene;
- shot;
- character;
- asset;
- script;
- animation;
- audio;
- render;
- review;
- version.

1.3 Chaque résultat important est un artefact versionné.

Exemples :
- script_v03;
- storyboard_v05;
- scene_07.blend;
- character_kael_v04.blend;
- animation_run_v02;
- voice_fr_v03.wav;
- music_v06.wav;
- shot_013_preview.mp4.

1.4 Aucun agent ne doit pouvoir détruire silencieusement le travail précédent.

Tout changement important doit produire une nouvelle version ou un patch.

1.5 Préférer les interfaces aux dépendances directes.

Un agent ne doit pas dépendre directement de « OpenAI », « Claude », « Blender » ou d'un fournisseur audio.
Il dépend d'une capacité :
- LLM;
- vision;
- code;
- image;
- TTS;
- music;
- SFX;
- renderer;
- editor.

============================================================
2. POSITIONNEMENT DU PRODUIT
============================================================

La différenciation ne doit pas être « nous avons plus de modèles IA ».

Elle doit être :

A. Production orientée projet
B. Cohérence des personnages et du monde
C. Timeline et shots comme primitives natives
D. Agents spécialisés
E. Répétabilité
F. Observabilité
G. Contrôle humain
H. Réutilisation d'assets
I. Audio synchronisé à l'image
J. Possibilité de modifier une scène sans régénérer tout le film
K. Historique et versions
L. Export professionnel
M. Architecture ouverte aux moteurs et modèles futurs

Promesse :
« Décris ce que tu veux produire. Le système construit, exécute, contrôle et te permet de diriger la production. »

============================================================
3. ARCHITECTURE GLOBALE
============================================================

                    USER
                      |
                Web Application
                      |
              Project / Timeline
                      |
                Creative Director
                      |
              Production Planner
                      |
        +-------------+-------------+
        |             |             |
   Visual Track   Audio Track   Narrative Track
        |             |             |
   Scene Agents    Audio Agents   Story Agents
        |             |             |
        +-------------+-------------+
                      |
                 QA / Critics
                      |
                 Render Manager
                      |
               Preview / Final
                      |
                  Delivery

Architecture logique :

Frontend
  -> API Gateway
  -> Project Service
  -> Agent Orchestrator
  -> Artifact Service
  -> Job Queue
  -> Execution Workers
  -> Render Workers
  -> Storage
  -> Observability

============================================================
4. NOOA COMME RUNTIME AGENTIQUE
============================================================

NOOA doit être utilisé comme couche d'agents et de contexte, pas comme base de données ni comme système complet de production.

Le dépôt NOOA expose notamment Agent, Context, DynamicContext, stratégie, Skills, événements, channels/queues, médias et LibraryManager.

Architecture recommandée :

NOOA
  |
  +-- Agent definitions
  +-- Skills
  +-- Context
  +-- Events
  +-- Agent communication
  +-- Reasoning / execution strategies
  |
  +-- external services
       +-- database
       +-- object storage
       +-- queue
       +-- Blender workers
       +-- audio workers
       +-- render farm

Principe :
NOOA orchestre le raisonnement.
Les workers exécutent les opérations lourdes.

============================================================
5. AGENTS PRINCIPAUX
============================================================

5.1 CreativeDirectorAgent

Responsabilité :
- comprendre l'intention ;
- identifier les objectifs ;
- définir style ;
- définir public ;
- définir contraintes ;
- détecter ambiguïtés ;
- produire le Creative Brief.

Ne doit PAS :
- coder Blender ;
- faire directement le rendu ;
- générer directement la musique.

5.2 ProductionPlannerAgent

Transforme le brief en plan de production.

Sortie :
ProductionPlan :
- duration;
- fps;
- resolution;
- aspect_ratio;
- scenes;
- shots;
- characters;
- environments;
- props;
- animation;
- audio;
- narration;
- render;
- delivery.

5.3 StoryAgent

Responsable :
- synopsis ;
- scénario ;
- dialogues ;
- narration ;
- rythme ;
- continuité narrative.

5.4 StoryboardAgent

Responsable :
- découpage en plans ;
- cadrage ;
- caméra ;
- durée ;
- action ;
- transitions.

5.5 WorldBuilderAgent

Responsable :
- règles du monde ;
- environnement ;
- architecture ;
- époque ;
- palette ;
- météo ;
- logique spatiale.

5.6 CharacterDirectorAgent

Responsable :
- identité ;
- silhouette ;
- vêtements ;
- personnalité ;
- rôle ;
- état ;
- cohérence inter-scènes.

5.7 CharacterAssetAgent

Responsable :
- création/modification des assets personnages ;
- rig ;
- matériaux ;
- expressions ;
- contrôleurs.

5.8 BlenderSceneAgent

Responsable :
- construire la scène ;
- objets ;
- collections ;
- matériaux ;
- caméra ;
- lumières ;
- paramètres de rendu.

Il travaille à partir d'un SceneSpec structuré et non d'un prompt libre uniquement.

5.9 BlenderAnimationAgent

Responsable :
- keyframes ;
- rigging ;
- contraintes ;
- actions ;
- synchronisation ;
- mouvement de caméra.

5.10 VFXAgent

Responsable :
- particules ;
- fumée ;
- feu ;
- pluie ;
- explosions ;
- poussière ;
- impacts ;
- effets stylisés.

5.11 CameraAgent

Responsable :
- composition ;
- focale ;
- profondeur ;
- mouvement ;
- continuité cinématographique.

5.12 LightingAgent

Responsable :
- éclairage ;
- ambiance ;
- contraste ;
- cohérence entre plans.

5.13 AudioDirectorAgent

Responsable :
- stratégie audio ;
- ambiance ;
- musique ;
- SFX ;
- silence ;
- dynamique.

5.14 MusicAgent

Génère ou pilote une génération musicale originale.

Doit recevoir :
- BPM ;
- durée ;
- tonalité si connue ;
- émotion ;
- instrumentation ;
- structure ;
- références stylistiques autorisées.

Ne jamais demander :
« copie cette chanson ».

Demander :
« composition originale avec caractéristiques musicales abstraites ».

5.15 SFXAgent

Responsable :
- pas ;
- coups ;
- explosions ;
- vent ;
- pluie ;
- armes fictives ;
- impacts ;
- ambiances.

5.16 VoiceAgent

Responsable :
- casting vocal ;
- TTS ;
- émotion ;
- rythme ;
- synchronisation dialogue.

5.17 LipSyncAgent

Responsable :
- synchronisation parole/personnage ;
- visèmes ;
- timing.

5.18 EditorAgent

Responsable :
- assemblage ;
- transitions ;
- timing ;
- mix ;
- sous-titres ;
- format final.

5.19 QAVisualAgent

Vérifie :
- objets manquants ;
- personnages incohérents ;
- caméra invalide ;
- clipping ;
- frames noires ;
- textures absentes ;
- animation cassée.

5.20 QAContinuityAgent

Vérifie :
- personnage A change-t-il de vêtement sans raison ?
- objet disparu ?
- lumière incohérente ?
- position incohérente ?
- dialogue incohérent ?
- chronologie incorrecte ?

5.21 QAAudioAgent

Vérifie :
- clipping ;
- silence inattendu ;
- niveau ;
- synchronisation ;
- voix ;
- musique ;
- SFX.

5.22 RenderAgent

Responsable :
- préparation ;
- rendu preview ;
- rendu final ;
- gestion des jobs ;
- retry ;
- récupération d'erreurs.

5.23 CriticAgent

Ne produit pas.
Il critique.

Il doit pouvoir dire :
- « le plan satisfait la spécification » ;
- « échec : caméra incohérente » ;
- « échec : personnage différent » ;
- « amélioration suggérée ».

Cette séparation est fondamentale.

============================================================
6. HIÉRARCHIE DES AGENTS
============================================================

Ne pas créer 50 agents qui s'appellent librement.

Architecture :

Director
  |
  +-- Planner
       |
       +-- Story
       +-- Visual Director
       |    +-- Character
       |    +-- Environment
       |    +-- Camera
       |    +-- Lighting
       |    +-- Animation
       |    +-- VFX
       |
       +-- Audio Director
       |    +-- Music
       |    +-- Voice
       |    +-- SFX
       |    +-- LipSync
       |
       +-- Editor
       |
       +-- QA
            +-- Visual QA
            +-- Continuity QA
            +-- Audio QA

Le Director ne doit pas être un « super-agent omniscient ».
Il coordonne.

============================================================
7. COMMENT UN AGENT APPELLE UN AUTRE
============================================================

Éviter :

Agent A -> appelle directement Agent B -> Agent B appelle C -> C appelle A.

Cela crée un graphe difficile à contrôler.

Préférer :

Agent
  -> crée Task
  -> Orchestrator
  -> sélectionne Worker/Agent
  -> exécute
  -> publie Artifact + Event
  -> Orchestrator décide de la suite.

Exemple :

CharacterDirector
  -> CharacterSpec
  -> event: character.spec.created
  -> CharacterAssetAgent
  -> CharacterAsset
  -> event: character.asset.ready
  -> QAVisualAgent
  -> QAResult

Les appels deviennent observables.

============================================================
8. WORKFLOW D'UNE PRODUCTION
============================================================

PHASE 0 — INTAKE
Utilisateur écrit son prompt.

PHASE 1 — UNDERSTANDING
CreativeDirector :
- interprétation ;
- contraintes ;
- questions uniquement si réellement nécessaires.

PHASE 2 — PREPRODUCTION
Story
Storyboard
World
Characters
Audio plan

PHASE 3 — APPROVAL
Le système montre :
- synopsis ;
- storyboard ;
- personnages ;
- style ;
- durée ;
- budget estimé.

L'utilisateur peut accepter ou modifier.

PHASE 4 — ASSET GENERATION
Création des assets.

PHASE 5 — SCENE BUILD
Blender/Unreal.

PHASE 6 — ANIMATION
Animation personnages/caméras/VFX.

PHASE 7 — AUDIO
Voix + musique + SFX + ambiance.

PHASE 8 — EDITING
Assemblage.

PHASE 9 — QA
Critiques automatiques.

PHASE 10 — PREVIEW
Rendu basse résolution.

PHASE 11 — ITERATION
Utilisateur :
« change seulement le mouvement de caméra du plan 04 ».

Le système ne régénère PAS tout.

PHASE 12 — FINAL RENDER
Rendu haute qualité.

PHASE 13 — DELIVERY
MP4/MOV + audio + sous-titres + éventuellement projet source.

============================================================
9. PRINCIPE CRUCIAL : PATCH-BASED GENERATION
============================================================

Une erreur fondamentale serait de régénérer la totalité de la vidéo à chaque modification.

Chaque modification doit être exprimée comme un patch.

Exemple :

User :
« rends la pluie plus intense dans le plan 7 ».

Patch :
scene_07.environment.weather.rain.intensity
old = 0.4
new = 0.8

Puis :
- recalcul uniquement des dépendances ;
- preview ;
- QA ;
- validation.

Cela réduit :
- coût ;
- temps ;
- appels LLM ;
- rendu ;
- frustration.

============================================================
10. SCENE GRAPH
============================================================

Créer un modèle indépendant du moteur :

SceneSpec

Scene
  id
  duration
  environment
  characters
  props
  camera
  lighting
  animation
  vfx
  audio
  constraints

Shot
  id
  start
  end
  camera
  actors
  action
  dialogue
  audio
  render_profile

Le SceneSpec est le contrat entre les agents et les moteurs.

============================================================
11. BLENDER COMME PREMIER MOTEUR
============================================================

Blender doit être le moteur principal initial.

Raisons :
- open source ;
- Python ;
- animation ;
- rigging ;
- rendering ;
- compositing ;
- VFX ;
- video editing ;
- API étendue.

La documentation Blender 4.5 LTS confirme que Python permet de piloter notamment animation, rendu, import/export, création d'objets et automatisation.

Le système doit appeler Blender en worker isolé.

Architecture :

Agent
 -> SceneSpec
 -> Blender Worker
 -> Python Script
 -> Blender
 -> .blend
 -> preview
 -> QA
 -> artifact

Le LLM ne doit jamais avoir un accès illimité au système de fichiers ou au shell de production.

============================================================
12. BLENDER CODE GENERATION
============================================================

Ne pas laisser le LLM générer uniquement un énorme script monolithique.

Créer une API interne :

scene.create()
scene.configure()
asset.import()
character.spawn()
camera.create()
light.create()
animation.apply()
vfx.create()
render.configure()

Le LLM produit un plan d'appel ou du code contrôlé.

Créer :
deepblender_runtime/

  scene/
  assets/
  characters/
  animation/
  camera/
  lighting/
  materials/
  vfx/
  audio/
  render/
  validation/

Objectif :
réduire les hallucinations API Blender.

============================================================
13. VALIDATION DU CODE BLENDER
============================================================

Pipeline :

LLM code
 -> static validation
 -> AST validation
 -> forbidden API check
 -> sandbox
 -> Blender execution
 -> scene validation
 -> preview render
 -> visual QA

Interdire par défaut :
- accès réseau ;
- suppression arbitraire ;
- accès hors workspace ;
- subprocess non autorisé ;
- modification de fichiers système.

============================================================
14. UNREAL ENGINE
============================================================

Unreal ne doit pas être intégré dès le premier produit comme deuxième moteur obligatoire.

Préparer une abstraction :

EngineAdapter

BlenderAdapter
UnrealAdapter
FutureEngineAdapter

Unreal est intéressant pour :
- temps réel ;
- environnements ;
- Niagara ;
- cinématiques ;
- virtual production ;
- grandes scènes ;
- rendu temps réel.

La documentation Unreal 5.6 expose les systèmes de rendu, Niagara, animation, audio, média, virtual production et scripting Python.

Mais l'introduction d'Unreal doit être une phase 2/3.

============================================================
15. COMFYUI / IMAGE / VIDEO MODELS
============================================================

Prévoir une couche ModelProvider.

ImageProvider
VideoProvider
LLMProvider
AudioProvider
TTSProvider
VisionProvider

ComfyUI peut servir de moteur de workflows pour certains modèles génératifs.

Important :
ne jamais coupler le projet à un seul modèle.

Exemple :

ProviderRegistry
  openai
  anthropic
  google
  openrouter
  local
  custom

============================================================
16. ROUTAGE LLM À PETIT BUDGET
============================================================

Le système doit fonctionner sans GPU local.

Architecture :

LLM Gateway
   |
   +-- Provider A
   +-- Provider B
   +-- Provider C
   +-- OpenRouter
   +-- compatible OpenAI
   +-- local later

Utiliser un routeur abstrait tel que LiteLLM ou une couche interne équivalente.

Le routeur décide selon :
- tâche ;
- qualité requise ;
- contexte ;
- latence ;
- coût ;
- disponibilité ;
- longueur ;
- criticité.

Exemple :

simple classification
 -> modèle économique

génération de code Blender
 -> modèle code performant

architecture
 -> modèle raisonnement puissant

QA
 -> modèle vision/raisonnement

============================================================
17. BUDGET / COST GOVERNANCE
============================================================

Chaque task possède :

estimated_cost
actual_cost
tokens
provider
latency
retry_count

Le Project Budget Manager doit pouvoir imposer :

max_cost_per_project
max_cost_per_scene
max_cost_per_task

Avant une opération coûteuse :

CostEstimator
 -> approval policy
 -> execute

Le système doit empêcher un agent de brûler le budget dans une boucle.

============================================================
18. AUDIO ET MUSIQUE
============================================================

Audio doit être une piste native du projet.

Timeline :

VIDEO
VOICE
DIALOGUE
MUSIC
SFX
AMBIENCE

Chaque élément possède :
- start;
- duration;
- gain;
- fade;
- source;
- version;
- license;
- provenance.

Musique :
génération originale ou bibliothèque sous licence compatible.

Conserver :
model;
prompt;
seed si disponible;
license;
generation_date;
provider;
artifact_hash.

Ne pas utiliser une musique protégée simplement parce que l'utilisateur demande une copie.

Le système doit permettre :
« inspire-toi d'une ambiance épique de bataille »
plutôt que :
« reproduis cette chanson ».

============================================================
19. VOIX
============================================================

VoiceProfile :

id
language
accent
gender/presentation if relevant
age_range
emotion
speaking_rate
pitch
provider
consent/license metadata

Ne jamais permettre implicitement l'imitation d'une personne réelle sans autorisation.

============================================================
20. CONNAISSANCES EXTERNES
============================================================

Créer KnowledgeService.

Sources :
- documentation officielle ;
- API references ;
- exemples ;
- internes ;
- assets ;
- règles du projet.

Pipeline :

Question
 -> Retriever
 -> sources
 -> relevance ranking
 -> context
 -> Agent

Pour Blender :
Blender Documentation
API reference
internal cookbook
tested snippets

Pour Unreal :
official docs
API
tested examples

Le LLM ne doit pas « inventer » l'API lorsqu'une documentation peut être récupérée.

============================================================
21. SKILLS
============================================================

Une skill doit être une capacité versionnée.

Exemples :

blender.create_scene
blender.import_asset
blender.create_camera
blender.animate_character
blender.render_preview
blender.validate_scene

audio.generate_music
audio.generate_sfx
audio.generate_voice
audio.mix

project.create_scene
project.create_shot
project.create_version
project.create_patch

qa.check_render
qa.check_continuity

Chaque skill doit définir :
- input schema ;
- output schema ;
- permissions ;
- cost ;
- timeout ;
- retry policy ;
- observability ;
- version.

============================================================
22. OBSERVABILITÉ
============================================================

L'utilisateur doit voir :

Production
  72%

Scene 04
  Building scene      ✓
  Characters          ✓
  Animation           ⟳
  Audio               ○
  QA                  ○
  Render              ○

Mais l'utilisateur professionnel doit également pouvoir ouvrir :

Task
Agent
Input
Reason
Tool calls
Artifact
Duration
Cost
Errors
Retries
Output

Créer un Event Ledger.

Exemples :

project.created
plan.created
scene.created
agent.started
agent.completed
skill.called
asset.created
render.started
render.completed
qa.failed
qa.passed
artifact.version.created
user.approval.required

============================================================
23. OBSERVABILITÉ INTERNE
============================================================

OpenTelemetry doit être utilisé comme standard.

Tracer :
- request;
- agent run;
- LLM call;
- tool call;
- render job;
- storage operation.

Métriques :
- generation_time;
- cost;
- tokens;
- render_time;
- error_rate;
- retry_rate;
- QA failure rate;
- user iteration count.

Logs structurés JSON.

============================================================
24. DATABASE
============================================================

PostgreSQL recommandé.

Entités principales :

User
Organization
Project
ProjectMember
Production
Sequence
Scene
Shot
Character
Asset
AssetVersion
SceneVersion
Script
Dialogue
AudioTrack
AudioAsset
RenderJob
RenderArtifact
AgentRun
Task
SkillExecution
Review
Comment
Patch
Provider
Model
UsageRecord
LicenseRecord
Event

Ne pas stocker les gros fichiers vidéo dans PostgreSQL.

Utiliser Object Storage :
S3-compatible.

PostgreSQL :
metadata.

Object Storage :
.blend
.mp4
.wav
.png
.fbx
.glb
.exr
etc.

============================================================
25. FILE SYSTEM / WORKSPACE
============================================================

Workspace logique :

projects/
  {project_id}/
    project.json
    brief/
    story/
    storyboard/
    sequences/
      seq_001/
        scenes/
          scene_001/
            scene.json
            shots/
              shot_001/
              shot_002/
            assets/
            renders/
            audio/
            versions/
    characters/
    environments/
    assets/
    audio/
    exports/
    logs/
    manifests/

Ne jamais laisser les agents écrire arbitrairement partout.

============================================================
26. STORAGE
============================================================

Séparer :

Metadata DB
Object Storage
Cache
Queue

Exemple :

PostgreSQL
Redis
S3/MinIO
Queue system
Worker filesystem

============================================================
27. QUEUE / EXECUTION
============================================================

Les opérations longues doivent être asynchrones.

API
 -> Job
 -> Queue
 -> Worker
 -> Event
 -> Artifact

Jobs :
- llm;
- image;
- audio;
- blender;
- render;
- ffmpeg;
- qa.

Ne jamais bloquer la requête HTTP pendant un rendu.

============================================================
28. RENDER FARM
============================================================

Préparer un RenderJob abstrait.

RenderJob :
id
project_id
scene_id
shot_id
engine
version
priority
status
worker
frames
resolution
samples
output
started_at
completed_at

Phase initiale :
un ou quelques workers.

Phase future :
Blender Flamenco / OpenCue / infrastructure cloud.

============================================================
29. API
============================================================

REST ou GraphQL pour le produit.

WebSocket/SSE pour événements temps réel.

Exemples :

POST /projects
POST /projects/{id}/productions
POST /productions/{id}/generate
GET /productions/{id}
GET /productions/{id}/timeline
POST /scenes
POST /scenes/{id}/iterate
POST /shots/{id}/patch
POST /renders
GET /jobs/{id}
GET /events
POST /reviews

============================================================
30. UX
============================================================

Ne pas faire une interface de chatbot avec un bouton « Generate ».

Faire une interface de studio.

Écrans :

1. Dashboard
2. Project Studio
3. Creative Brief
4. Storyboard
5. Timeline
6. Scene Viewer
7. Asset Library
8. Character Lab
9. Audio Studio
10. Agent Activity
11. Render Center
12. Review
13. Version History
14. Export

============================================================
31. INTERACTION UTILISATEUR
============================================================

L'utilisateur doit pouvoir intervenir à plusieurs niveaux.

Niveau 1 :
« Fais-moi une vidéo publicitaire. »

Niveau 2 :
« Change le style. »

Niveau 3 :
« Change le personnage. »

Niveau 4 :
« Change la scène 3. »

Niveau 5 :
« Change uniquement le plan 7. »

Niveau 6 :
« Change uniquement la caméra. »

Niveau 7 :
« Change uniquement la voix. »

Niveau 8 :
« Modifie les 3 secondes 12–15. »

La granularité d'édition est un avantage concurrentiel majeur.

============================================================
32. VERSIONING
============================================================

Utiliser un modèle proche du contrôle de version.

Project
  v1
  v2
  v3

Scene
  v1
  v2
  v3

Shot
  v1
  v2

Chaque version possède :
- parent;
- author/agent;
- timestamp;
- changes;
- artifacts;
- cost.

L'utilisateur peut :
- comparer ;
- restaurer ;
- dupliquer ;
- brancher une version.

============================================================
33. REPLAY
============================================================

Chaque génération importante doit être reproductible autant que possible.

Conserver :
- prompt;
- context;
- model;
- provider;
- parameters;
- seed;
- tool versions;
- skill versions;
- input hashes;
- output hashes.

Cela permet :
debug;
audit;
reproduction;
comparaison.

============================================================
34. SECURITY
============================================================

Les agents sont du code non fiable.

Créer un Agent Sandbox.

Permissions explicites :

filesystem.read
filesystem.write
blender.execute
network.none
network.allowlist
shell.none
render.execute

Chaque skill possède ses permissions.

Secrets :
- jamais dans les prompts ;
- jamais dans les logs ;
- vault/secrets manager.

============================================================
35. LICENCES ET PROVENANCE
============================================================

Chaque asset externe doit avoir :

source
provider
license
attribution
commercial_use
restrictions

Chaque génération doit conserver sa provenance.

Créer un ProvenanceGraph :

Artifact
 -> generated_by
 -> model
 -> provider
 -> source assets
 -> prompts
 -> transformations

Cela devient une fonctionnalité commerciale importante.

============================================================
36. ARCHITECTURE DOSSIERS DU REPOSITORY
============================================================

deepblender/
  apps/
    web/
    api/

  packages/
    domain/
    contracts/
    agent-runtime/
    orchestration/
    skills/
    knowledge/
    providers/
    observability/
    security/

  agents/
    creative_director/
    planner/
    story/
    storyboard/
    world/
    character/
    blender_scene/
    animation/
    camera/
    lighting/
    vfx/
    audio/
    music/
    voice/
    lipsync/
    editor/
    qa/

  workers/
    blender/
    audio/
    render/
    media/
    qa/

  engines/
    blender/
    unreal/

  infrastructure/
    docker/
    terraform/
    monitoring/

  docs/
    architecture/
    api/
    agents/
    skills/
    workflows/

  tests/
    unit/
    integration/
    contract/
    e2e/
    visual/

  scripts/

============================================================
37. CONTRATS DE DONNÉES
============================================================

Tous les agents doivent communiquer via schemas versionnés.

Exemple :

SceneSpec v1

{
  id,
  duration,
  environment,
  characters,
  props,
  camera,
  lighting,
  animation,
  vfx,
  audio,
  constraints
}

Les agents ne doivent pas dépendre de texte libre lorsqu'un schema est possible.

============================================================
38. TESTS
============================================================

Tests obligatoires :

Unit tests
Integration tests
Contract tests
Agent tests
Skill tests
Blender execution tests
Render smoke tests
Visual regression tests
End-to-end production tests

Créer des projets de référence :

TEST_001_SIMPLE_ROOM
TEST_002_TWO_CHARACTERS
TEST_003_DIALOGUE
TEST_004_FIGHT
TEST_005_RAIN
TEST_006_MUSIC
TEST_007_FULL_SHORT

Chaque release doit réussir ces scénarios.

============================================================
39. EVALUATION DES AGENTS
============================================================

Créer un benchmark interne.

Mesures :

Plan correctness
Scene correctness
Character consistency
Camera quality
Animation validity
Audio synchronization
Continuity
Cost
Latency
Retry rate
Human correction rate

Un agent ne doit pas être jugé uniquement sur son texte.

Il doit être jugé sur l'artefact final.

============================================================
40. ARCHITECTURE DE DÉPLOIEMENT
============================================================

Phase initiale commerciale :

Frontend
Backend
PostgreSQL
Redis
Object Storage
Agent Runtime
Blender Worker
Audio Worker
Render Worker
Observability

Docker partout où cela simplifie la reproductibilité.

CI/CD :
- lint;
- typecheck;
- tests;
- build;
- security scan;
- deploy.

============================================================
41. TECHNOLOGIES À PRIVILÉGIER
============================================================

Frontend :
Next.js / React / TypeScript

Backend :
Python + FastAPI

Agent Runtime :
NOOA

Database :
PostgreSQL

Cache / queue :
Redis

Object storage :
S3-compatible / MinIO

Realtime :
WebSocket ou SSE

Observability :
OpenTelemetry + Grafana/Prometheus/Loki ou équivalent

Media :
FFmpeg

3D :
Blender 4.5 LTS initialement

Second engine :
Unreal Engine dans une phase ultérieure

Workflow image/video :
ComfyUI ou adapters spécialisés

Render management :
Blender Flamenco puis éventuellement OpenCue/cloud

Timeline interchange :
OpenTimelineIO peut servir de format d'interchange lorsque pertinent.

============================================================
42. STRATÉGIE OPEN SOURCE
============================================================

Ne pas intégrer une bibliothèque uniquement parce qu'elle est populaire.

Pour chaque dépendance :

- licence ;
- activité ;
- sécurité ;
- maintenance ;
- compatibilité ;
- API stability ;
- coût ;
- communauté ;
- possibilité de remplacement.

Créer un registre :

TechnologyRegistry

name
version
license
purpose
adapter
status
replacement_strategy

============================================================
43. COMMERCIALISATION
============================================================

Créer dès le début :

Organizations
Users
Roles
Projects
Quotas
Usage
Billing hooks
Audit logs
API keys
Provider configuration

RBAC :

Owner
Admin
Director
Artist
Reviewer
Viewer

Possibilité future :
team workspaces.

============================================================
44. MODÈLE ÉCONOMIQUE
============================================================

Ne pas vendre simplement « des tokens ».

Vendre une capacité de production.

Exemples :
Starter
Creator
Professional
Studio

Limiter selon :
- minutes rendues ;
- stockage ;
- crédits ;
- résolution ;
- nombre de productions simultanées ;
- collaboration.

============================================================
45. PRODUCT ANALYTICS
============================================================

Mesurer :

time_to_first_preview
time_to_final
iterations_per_scene
failed_generations
agent_failure_rate
human_intervention_rate
cost_per_minute
render_cost
retention
export_rate

Objectif :
comprendre où les utilisateurs abandonnent.

============================================================
46. PSYCHOLOGIE UX
============================================================

L'utilisateur ne veut pas « gérer des agents ».

Il veut créer.

Donc :
- agents invisibles par défaut ;
- progression visible ;
- résultats concrets ;
- possibilité d'ouvrir les détails ;
- pas de jargon obligatoire ;
- contrôle lorsqu'il le souhaite.

L'interface doit donner :
CONFIANCE + CONTRÔLE + SURPRISE CRÉATIVE.

Ne pas afficher :
« Agent 7 failed because tool invocation... »

Afficher :
« Le plan 08 n'a pas passé le contrôle de continuité. Le personnage changeait de tenue. Correction automatique en cours. »

Puis permettre :
« Voir le diagnostic ».

============================================================
47. AGENT ACTIVITY UI
============================================================

Créer une timeline d'activité :

16:42 Creative Director
    Brief created

16:43 Story Agent
    Script v2 created

16:44 Character Agent
    Kael v3 created

16:46 Blender Agent
    Scene 04 built

16:47 QA
    Camera issue detected

16:48 Blender Agent
    Patch applied

16:49 QA
    Passed

Cette interface peut devenir une signature du produit.

============================================================
48. « DIRECTOR MODE »
============================================================

Fonctionnalité stratégique.

L'utilisateur peut diriger la production comme un réalisateur.

Commandes :

« rends cette scène plus sombre »
« caméra plus proche »
« accélère le combat »
« donne plus de personnalité au personnage »
« supprime le plan 6 »
« ajoute 4 secondes »
« garde exactement le personnage actuel »
« ne change rien sauf la lumière »

Le système traduit chaque commande en patchs structurés.

============================================================
49. COHÉRENCE DES PERSONNAGES
============================================================

Character Identity Lock.

Une identité de personnage devient un artefact persistant.

CharacterIdentity :
- geometry;
- rig;
- materials;
- clothing;
- facial characteristics;
- style;
- reference images;
- constraints.

Toute nouvelle scène reçoit cette identité.

Objectif :
éviter le « nouveau personnage » à chaque génération.

============================================================
50. COHÉRENCE DU MONDE
============================================================

World Bible.

Contient :
- géographie ;
- architecture ;
- règles ;
- palette ;
- époque ;
- technologie ;
- météo ;
- personnages ;
- objets ;
- vocabulaire.

Le World Bible devient une source de contexte commune.

============================================================
51. MÉMOIRE
============================================================

Trois niveaux :

Short-term:
contexte de task.

Project memory:
monde, personnages, décisions.

System knowledge:
documentation, skills, recettes, standards.

Ne pas mettre tout dans le prompt.

Utiliser récupération ciblée.

============================================================
52. KNOWLEDGE + SKILL + TOOL
============================================================

Distinction stricte :

Knowledge :
« comment fonctionne Blender ? »

Skill :
« créer une caméra Blender ».

Tool :
« exécuter bpy ».

Agent :
« décider quand et pourquoi créer la caméra ».

Cette séparation évite les agents gigantesques.

============================================================
53. SELF-REPAIR
============================================================

Un agent de génération ne doit pas immédiatement demander de l'aide.

Pipeline :

generate
 -> execute
 -> observe
 -> diagnose
 -> patch
 -> execute
 -> validate

Limiter :
max_retries = 2 ou 3.

Après échec :
human intervention.

============================================================
54. HUMAN-IN-THE-LOOP
============================================================

Points d'approbation :

Avant :
- production très coûteuse ;
- suppression importante ;
- export final ;
- utilisation d'un asset à licence incertaine.

Après :
- génération importante ;
- QA échouée ;
- ambiguïté créative.

L'utilisateur doit pouvoir désactiver certaines approbations pour les productions automatisées.

============================================================
55. « ONE PROMPT » NE DOIT PAS ÊTRE L'OBJECTIF TECHNIQUE
============================================================

L'expérience peut être :

« Je veux une vidéo... »

Mais le système interne doit être structuré.

L'utilisateur voit la simplicité.
L'architecture conserve la complexité.

C'est la différence entre une démo et un produit.

============================================================
56. ROADMAP RÉALISTE
============================================================

PHASE A — FOUNDATION
- monorepo ;
- auth ;
- users ;
- organizations ;
- projects ;
- PostgreSQL ;
- object storage ;
- job queue ;
- events ;
- observability ;
- NOOA integration.

PHASE B — CREATIVE PIPELINE
- CreativeDirector ;
- Planner ;
- Story ;
- Storyboard ;
- SceneSpec ;
- project timeline.

PHASE C — BLENDER
- Blender Worker ;
- Blender Runtime ;
- Scene Agent ;
- Camera Agent ;
- Lighting Agent ;
- Animation Agent ;
- render preview.

PHASE D — ASSETS
- characters ;
- environments ;
- asset registry ;
- versioning.

PHASE E — AUDIO
- TTS ;
- SFX ;
- music ;
- mixer ;
- timeline synchronization.

PHASE F — QA
- visual QA ;
- continuity QA ;
- audio QA ;
- self-repair.

PHASE G — ITERATION
- patch system ;
- version graph ;
- scene-level regeneration ;
- shot-level regeneration.

PHASE H — COMMERCIAL
- RBAC ;
- quotas ;
- usage;
- billing integration ;
- audit ;
- team collaboration.

PHASE I — MULTI-ENGINE
- Unreal adapter ;
- additional rendering backends.

============================================================
57. DÉFINITION DU PRODUIT « FINI »
============================================================

Le produit ne doit pas être considéré terminé lorsque :
« l'agent peut générer une vidéo ».

Il est terminé lorsque :

[ ] utilisateur peut créer un compte
[ ] créer un projet
[ ] écrire un brief
[ ] obtenir un plan
[ ] accepter/modifier le plan
[ ] générer scènes
[ ] visualiser previews
[ ] modifier un shot
[ ] conserver les versions
[ ] générer audio
[ ] synchroniser audio
[ ] lancer QA
[ ] corriger les erreurs
[ ] suivre les agents
[ ] suivre les coûts
[ ] relancer une tâche
[ ] exporter
[ ] retrouver son projet
[ ] travailler en équipe
[ ] contrôler les permissions
[ ] comprendre les erreurs
[ ] récupérer ses artefacts

============================================================
58. ARCHITECTURE CIBLE
============================================================

                  ┌──────────────────────┐
                  │       WEB APP        │
                  │ Studio / Timeline    │
                  └──────────┬───────────┘
                             │
                       API / Realtime
                             │
                  ┌──────────▼───────────┐
                  │   PROJECT SERVICE    │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │  NOOA ORCHESTRATOR   │
                  └──────────┬───────────┘
                             │
          ┌──────────────────┼───────────────────┐
          │                  │                   │
      Creative            Visual              Audio
       Agents             Agents              Agents
          │                  │                   │
          └──────────────────┼───────────────────┘
                             │
                    ┌────────▼────────┐
                    │   TASK QUEUE    │
                    └────────┬────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
 Blender Worker          Audio Worker         Media Worker
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                       Render Worker
                             │
                    ┌────────▼────────┐
                    │   QA / CRITICS  │
                    └────────┬────────┘
                             │
                       Artifact Store
                             │
                    ┌────────▼────────┐
                    │   USER REVIEW   │
                    └─────────────────┘

============================================================
59. DÉCISION ARCHITECTURALE MAJEURE
============================================================

Le cœur du produit n'est ni Blender, ni NOOA, ni le LLM.

Le cœur est le modèle de production :

Project
 -> Production
 -> Sequence
 -> Scene
 -> Shot
 -> Asset
 -> Version
 -> Task
 -> Artifact
 -> Review
 -> Patch

NOOA orchestre les décisions.
Les Skills exécutent les capacités.
Les Workers exécutent les opérations lourdes.
Les moteurs réalisent la production.
Les artefacts constituent la vérité.
La base de données conserve l'état.
L'interface rend l'ensemble contrôlable.

============================================================
60. RISQUES À ÉVITER
============================================================

1. Super-agent unique.
2. Prompt géant.
3. Tout régénérer à chaque modification.
4. Agents sans contrats.
5. Agent ayant accès complet au système.
6. LLM directement responsable de toutes les décisions.
7. Pas de versioning.
8. Pas de QA.
9. Pas de budget.
10. Couplage à un fournisseur.
11. Couplage à Blender dans tout le domaine métier.
12. Stocker les vidéos dans PostgreSQL.
13. Interface uniquement conversationnelle.
14. Absence de provenance.
15. Ajouter Unreal trop tôt.
16. Ajouter 40 agents avant d'avoir un workflow stable.
17. Considérer une génération réussie parce que le code s'est exécuté.
18. Confondre texte produit par l'agent et résultat artistique.
19. Utiliser des contenus protégés sans vérifier les droits.
20. Laisser les boucles d'agents consommer le budget.

============================================================
61. CRITÈRE DE QUALITÉ FINAL
============================================================

Une production doit être jugée sur cinq dimensions :

CREATIVE
La vidéo correspond-elle à l'intention ?

TECHNICAL
La scène est-elle valide ?

CONSISTENCY
Le monde et les personnages restent-ils cohérents ?

AUDIOVISUAL
Image, animation, voix, musique et SFX fonctionnent-ils ensemble ?

CONTROL
L'utilisateur peut-il comprendre, modifier, versionner et reprendre la production ?

============================================================
62. CONCLUSION
============================================================

La vision doit évoluer de :

« une IA qui crée des vidéos »

vers :

« un studio audiovisuel agentique programmable ».

La plateforme doit reproduire le travail d'une équipe professionnelle sans reproduire ses lenteurs.

Elle doit transformer :
- brief -> production plan ;
- production plan -> artefacts ;
- artefacts -> scènes ;
- scènes -> shots ;
- shots -> animation ;
- animation -> audio ;
- audio + image -> montage ;
- montage -> QA ;
- QA -> correction ;
- correction -> final.

Le caractère unique du produit ne viendra pas d'un modèle magique.

Il viendra de la combinaison :

AGENTS
+ WORKFLOWS
+ SCENE GRAPH
+ ASSET MEMORY
+ VERSIONING
+ PATCHES
+ OBSERVABILITY
+ QA
+ MULTI-MODEL ROUTING
+ MULTI-ENGINE ABSTRACTION
+ PROFESSIONAL UX
+ PROVENANCE
+ HUMAN CONTROL

C'est cette architecture qui permet de passer d'une démonstration IA à une véritable plateforme de production.

============================================================
63. RÈGLE POUR L'AGENT DE CODAGE
============================================================

L'agent chargé d'implémenter ce projet doit respecter les règles suivantes :

- ne pas inventer une architecture lorsqu'un contrat existe ;
- ne pas ajouter une abstraction sans besoin concret ;
- ne pas dupliquer une capacité existante ;
- rechercher d'abord les composants existants du repository ;
- réutiliser les services et skills ;
- respecter les schemas ;
- écrire les tests avant ou avec les fonctionnalités critiques ;
- ne jamais supprimer un artefact utilisateur ;
- ne jamais exposer les secrets ;
- ne jamais contourner les permissions ;
- ne jamais ajouter une dépendance sans justification ;
- ne jamais coupler le domaine métier à un fournisseur ;
- préférer les interfaces/adapters ;
- conserver la simplicité ;
- produire du code lisible ;
- documenter les décisions importantes ;
- vérifier l'exécution réelle plutôt que déclarer une fonctionnalité terminée ;
- lancer les tests pertinents après chaque changement ;
- traiter les erreurs comme des états observables ;
- limiter les retries ;
- respecter les budgets ;
- préserver la compatibilité des versions ;
- ne pas transformer une petite tâche en refactorisation globale.

Règle ultime :

« Construire le système le plus simple capable de satisfaire le contrat, et ne jamais confondre sophistication avec qualité. »

============================================================
FIN DU CAHIER DE CONCEPTION
============================================================
