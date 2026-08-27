# Plan : Amélioration Qualité Vidéo DeepBlender

## Contexte

Le pipeline DeepBlender fonctionne end-to-end (story → storyboard → director → blender → render → post-prod) mais la qualité de sortie est au niveau "proof of concept" :
- Personnages = primitives Blender (cylindres + sphères)
- Matériaux = couleurs plates (Principled BSDF sans textures)
- Pas de compositing nodes dans les scripts générés
- 32 samples Cycles (preview quality)
- Scripts parallèles par plan = incohérence visuelle
- Pas d'intégration asset library (PolyHaven existe mais n'est jamais appelé)

L'objectif est d'élever la qualité vers un niveau "prosumer" utilisable pour du contenu social media / présentation.

---

## Étape 1 : Asset Library Integration — Characters & Environnements

**Fichier principal** : `deepblender/assets/polyhaven.py` (existe, 138 lignes)
**Fichier à créer** : `deepblender/assets/characters.py`

### 1a. Client Quaternius/Mixamo pour characters rigged

Créer `deepblender/assets/characters.py` :
- `CharacterAssetClient` avec :
  - `search(query, category)` — recherche sur Quaternius (gratuit, CC0) et fallback Mixamo
  - `download(asset_id, format="glb")` — téléchargement avec cache local
  - `get_rigged(character_name)` — retourne le chemin .glb/.fbx d'un personnage riggé
- Sources : Quaternius.com (API REST publique), Mixamo (fallback)
- Cache : `deepblender_cache/characters/`

### 1b. Câbler PolyHaven dans BlenderAgent

Modifier `deepblender/agents/blender.py` :
- Dans `build_script()`, avant de générer le code, charger automatiquement :
  - 1 HDRI adapté au `lighting_mood` de la scène (via `PolyHavenClient.search_hdris()`)
  - 2-3 textures PBR si `environment.description` contient des mots-clés (métal, bois, pierre, etc.)
- Injecter les chemins locaux des assets téléchargés dans le contexte LLM (`asset_paths` dict)
- Le LLM génère alors du code qui importe ces .glb/.exr/.png au lieu de créer des primitives

### 1c. Intégrer les characters dans CharacterSpec

Ajouter à `CharacterSpec` dans `deepblender/domain/scene.py` :
- `asset_id: str = ""` — identifiant de l'asset (ex: "quaternius__animated_woman")
- `asset_source: str = ""` — "quaternius", "mixamo", "polyhaven", "custom"

**Fichiers modifiés** :
- `deepblender/assets/polyhaven.py` — pas de changement
- `deepblender/assets/characters.py` — NOUVEAU
- `deepblender/domain/scene.py` — ajouter `asset_id`, `asset_source` à `CharacterSpec`
- `deepblender/agents/blender.py` — charger assets avant génération

**Validation** :
- Tests unitaires pour `CharacterAssetClient`
- Test d'intégration que `build_script()` reçoit les `asset_paths` dans le contexte

---

## Étape 2 : Compositing Nodes dans les Scripts Générés

**Fichiers principaux** :
- `deepblender/skills/compositing/SKILL.md` — déjà complet (222 lignes)
- `deepblender/agents/blender.py` — modifier le prompt du LLM

### 2a. Forcer les compositing nodes

Modifier `deepblender/agents/blender.py` :
- Dans le prompt de `build_script()`, ajouter une section **CRITICAL: Compositing** :
  ```
  ## CRITICAL: Compositing nodes
  You MUST set up compositing nodes for every render:
  1. Render Layers node (input)
  2. Glare node (bloom/fog_glow, quality=high, threshold=0.8)
  3. Color Balance node (lift/gamma/gain based on lighting_mood)
  4. Lens Distortion (dispersion=0.01 for cinematic feel)
  5. Composite node (output)
  6. File Output node (save EXR with render passes)
  Enable render passes: Combined, Depth, Normal, Mist, AO
  ```

### 2b. Activer les render passes par défaut

Dans le prompt du LLM,forcer :
```python
scene.render.layers["RenderLayer"].use_pass_combined = True
scene.render.layers["RenderLayer"].use_pass_z = True
scene.render.layers["RenderLayer"].use_pass_normal = True
scene.render.layers["RenderLayer"].use_pass_mist = True
scene.render.layers["RenderLayer"].use_pass_ao = True
scene.render.filepath = render_dir + "/frame_"  # EXR multi-layer
scene.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
```

### 2c. Post-processing FFmpeg amélioré

Modifier `deepblender/plugins/rendering/ffmpeg_advanced.py` :
- Ajouter filtre `curves` (3-way color correction) dans `ColorGradePreset.to_filter_string()`
- Ajouter filtre `colorbalance` pour lift/gamma/gain
- Ajouter audio loudness normalization (`loudnorm=I=-14:TP=-1:LRA=11`)
- Stereo output au lieu de mono (`-ac 2`)

**Fichiers modifiés** :
- `deepblender/agents/blender.py` — prompt compositing
- `deepblender/plugins/rendering/ffmpeg_advanced.py` — filtres avancés

---

## Étape 3 : Script Unique par Scène (pas par plan)

**Fichier principal** : `deepblender/production/rendering.py`

### 3a. Abandonner le mode parallel_shots avec scripts séparés

Le mode `run_render_parallel_shots()` génère un script par plan = incohérence visuelle. Le remplacer par :

**Nouveau comportement** : `run_render()` reçoit la `SceneSpec` complète avec tous les plans. Le LLM génère UN SEUL script qui :
1. Crée la scène complète (environnement, personnages)
2. Pour chaque shot : définit la caméra, anime les personnages, rend le plan
3. Utilise `bpy.context.scene.frame_set()` pour commuter entre plans
4. Utilise un seul material/environment cohérent

### 3b. Modifier `build_script()` pour accepter multi-shot

Dans `deepblender/agents/blender.py` :
- Le prompt doit décrire comment gérer les transitions entre plans
- Exemple de pattern :
  ```python
  # Shot 1: frames 0-120
  cam.location = (0, -5, 1.5)
  scene.frame_set(0)
  bpy.ops.render.render(animation=True)
  # Shot 2: frames 120-240
  cam.location = (3, -2, 2.0)
  scene.frame_set(120)
  bpy.ops.render.render(animation=True)
  ```

### 3c. Simplifier le merge ffmpeg

Puisque le script produit une seule vidéo, `merge_shot_videos()` n'est plus nécessaire en mode standard. Le garder comme fallback.

**Fichiers modifiés** :
- `deepblender/production/rendering.py` — mode single-script
- `deepblender/agents/blender.py` — prompt multi-shot

---

## Étape 4 : Templates d'Animation

**Fichier à créer** : `deepblender/assets/animations.py`

### 4a. Bibliothèque de templates d'animation

Créer `deepblender/assets/animations.py` :
- `AnimationTemplateLibrary` avec :
  - `walk_cycle(frames=48)` — keypoints de marche standardisés
  - `idle_breathing(frames=60)` — respiration naturelle
  - `gesture_reach(frames=30)` — tendre la main
  - `gesture_point(frames=20)` — pointer
  - `sitting(frames=60)` — assis
  - `running(frames=36)` — course
- Chaque template retourne une liste de `(frame, location, rotation)` keyframes
- Intégrable dans les scripts Blender générés

### 4b. Injecter les templates dans BlenderAgent

Dans `deepblender/agents/blender.py` :
- Lorsque `animation.description` contient des mots-clés ("marche", "walking", "idle", etc.), charger le template correspondant
- Injecter les keyframes dans le contexte LLM pour que le script les utilise

**Fichiers créés** :
- `deepblender/assets/animations.py` — NOUVEAU

---

## Étape 5 : Qualité de Rendu

### 5a. Settings par défaut améliorés

Modifier `deepblender/domain/scene.py` `RenderSpec` :
- `samples: int = 256` (au lieu de 64) — qualité production
- `engine: str = "CYCLES"` — garder
- Ajouter `denoise: bool = True` — Active OIDN denoiser
- Ajouter `use_gpu: bool = True` — Préfère GPU si disponible

### 5b. Force GPU dans BlenderBridge

Modifier `deepblender/blender/bridge.py` :
- Détecter CUDA/OptiX au lancement de Blender
- Ajouter `--factory-startup` pour éviter les configs utilisateur
- Ajouter `cycles_device = 'GPU'` dans les scripts générés

### 5c. Render passes obligatoires

Dans le prompt du LLM, exiger :
- `use_pass_combined = True`
- `use_pass_z = True` (depth)
- `use_pass_normal = True`
- `use_pass_mist = True`
- Sortie EXR multi-layer pour le compositing

**Fichiers modifiés** :
- `deepblender/domain/scene.py` — RenderSpec amélioré
- `deepblender/agents/blender.py` — prompt render settings
- `deepblender/blender/bridge.py` — GPU detection

---

## Étape 6 : Validation Visuelle Améliorée

### 6a. Validator de qualité de script

Modifier `deepblender/codegen/validator.py` :
- Ajouter des checks sémantiques (pas juste AST) :
  - Vérifier que `scene.render.filepath` est un chemin absolu
  - Vérifier que `scene.render.engine` est défini
  - Vérifier que le script contient au moins 1 material
  - Vérifier que le script contient au moins 1 camera
  - Vérifier que les render passes sont activées
  - Avertir si `samples < 128`

### 6b. Visual QA amélioré

Modifier `deepblender/agents/qa.py` :
- Ajouter des checks de qualité d'image :
  - Ne pas accepter des images entièrement noires/blanches
  - Vérifier la diversité de luminosité (histogramme)
  - Vérifier la présence de mouvement (différence entre frames)

**Fichiers modifiés** :
- `deepblender/codegen/validator.py` — checks sémantiques
- `deepblender/agents/qa.py` — visual QA

---

## Résumé des Fichiers

| Fichier | Action | Étape |
|---------|--------|-------|
| `deepblender/assets/characters.py` | CRÉER | 1 |
| `deepblender/assets/animations.py` | CRÉER | 4 |
| `deepblender/domain/scene.py` | MODIFIER | 1, 5 |
| `deepblender/agents/blender.py` | MODIFIER | 1, 2, 3, 4, 5 |
| `deepblender/production/rendering.py` | MODIFIER | 3 |
| `deepblender/plugins/rendering/ffmpeg_advanced.py` | MODIFIER | 2 |
| `deepblender/blender/bridge.py` | MODIFIER | 5 |
| `deepblender/codegen/validator.py` | MODIFIER | 6 |
| `deepblender/agents/qa.py` | MODIFIER | 6 |

## Tests

- `tests/test_asset_characters.py` — tests pour CharacterAssetClient
- `tests/test_asset_animations.py` — tests pour AnimationTemplateLibrary
- `tests/test_rendering_single_script.py` — test mode single-script
- `tests/test_compositing_prompt.py` — vérifie que le prompt contient les instructions compositing
- Mettre à jour `tests/test_runner.py` et `tests/test_decoupling.py` si nécessaire

## Risques

- **Quaternius API** : peut nécessiter un User-Agent spécifique, rate limiting
- **Qualité LLM** : même avec un meilleur prompt, la qualité dépend du modèle (GPT-4o vs GPT-3.5)
- **Blender timeout** : 256 samples + compositing nodes = plus de temps de rendu (augmenter timeout à 600s)
- **Tokens** : le prompt du LLM grossit avec les templates d'animation (gérer via truncation)
