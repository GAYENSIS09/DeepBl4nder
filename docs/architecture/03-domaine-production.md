# 03 — Domaine de production (objets métier et pipeline)

> Consolidation de : Roadmap A §5-6/§18, B §11, C §3/§8/§20.

## Objets métier : objets Python vivants, pas des DTO sérialisés

Les agents NOOA manipulent des objets Python typés **par référence** :

```python
scene = agent.scene
shot = project.shots["shot_01"]
plan = await agent.plan_shot(shot)
scene.camera = plan.camera
```

Objets de premier niveau : `Project`, `Sequence`, `Shot`, `Scene`, `Asset`, `Character`,
`Camera`, `Material`, `Animation`, `Audio`, `Render`, `QAReport`, `Revision`, `Artifact`.

Chaque objet conserve références, état, types, relations, méthodes et contexte.

## Specs structurées (pas « brief → énorme script Python »)

```text
Brief → SceneSpec → ShotSpec → AnimationSpec → LightingSpec → Python Blender
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

Cela sépare intention, structure et implémentation.

## Pipeline audiovisuel (18 étapes)

1. **Intention & briefing** → `BriefSpec` (DirectorAgent)
2. **Scénario** → `StorySpec`, `SceneNarrative`, `CharacterArc`, `DialogueSpec`
3. **Storyboard** → `Storyboard`, `ShotPlan[]`
4. **Prévis / Animatic** → `Animatic`, `TimingSpec`, `CameraPreview` (+ bande-son de référence `AudioReference`), (décision NOOA / rendu DeepBl4nder)
5. **Faisabilité** → `FeasibilityReport` (durée, complexité, assets, GPU, budget, risques)
6. **Assets** → Search/Generate/Import → Validate → Register → Version (characters, props, env, textures, HDRI, audio)
7. **UV / Texturing / Shading** → `MaterialSpec`, `TextureSet`, `LookDev`
8. **Rigging** → `RigSpec`, `WeightReport`, `PoseLibrary`
9. **Layout** → `LayoutScene`
10. **Animation / Caméra / Lumière / Simulation** → `AnimatedScene`, `CameraPass`, `LightingPass`, `SimulationCache`
11. **Pre-render** → Preview Artifact → Technical QA
12. **QA / Révisions** → `QAReport` ; FAIL → `RevisionSpec` → étape affectée (jamais toute la production)
13. **Final Render** (local / worker pool / render farm — scheduler DeepBl4nder)
14. **Compositing** → `CompositeArtifact`
15. **Audio** → `AudioPlan` → génération/import → mix → `AudioMaster` (sound design, music, voice)
16. **Langues** → translation → voice/dubbing → subtitles → `LanguagePackage` (dialogues, sous-titres, métadonnées, interface)
17. **Final QA** (visual, technique, audio, continuité, langue, codec, couleur, framerate, résolution, metadata)
18. **Export** → master, web, preview, sous-titres, stems, archive projet

## Production state

DeepBl4nder conserve la vérité du projet :

```text
Project
 ├── Sequences → Shots → Specs / Assets / Scene versions / Render versions / QA reports / Revisions
 └── Contraintes globales
```

NOOA state et production state sont **corrélés** mais ne sont pas la même chose.

## Transition Worker → Artifact

Worker → exécution → output → registration artifact → hash → version → provenance → production state.
