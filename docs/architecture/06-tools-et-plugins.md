# 06 — Tools et plugins

> Consolidation de : Roadmap A §15-16, B §8, C §11-12.

## Tools

Un tool est une **primitive d'action importante** :

```text
inspect_scene, load_asset, save_blend, render, inspect_render,
create_audio, compose, export
```

**Ne pas créer** de micro-tools (`move_object`, `rotate_object`, `scale_object`,
`set_location`, `set_rotation`, …) quand le même résultat est obtenu naturellement via
Python / Code-as-Action.

## Plugins

Un plugin est une **frontière d'intégration** avec un système externe. Il ne devient pas un
deuxième runtime agentique.

```text
Agent → Tool / Python → Plugin → Système externe
```

Plugins prévus : `blender`, `ue5`, `godot`, `ai-video`, `render-farm`, `ffmpeg`, `audio`, `tts`, `storage`,
`asset-library`, `subtitle`, `git`, `knowledge-graph`.

Exemple — `BlenderPlugin` : `inspect_scene()`, `execute_python()`, `render()`,
`save_scene()`, `load_asset()`.

Exemple — `UE5Plugin` : `create_level()`, `import_asset()`, `create_material()`,
`setup_lighting()`, `start_render()`.

Exemple — `GodotPlugin` : `create_scene()`, `create_mesh()`, `create_material()`,
`setup_lighting()`, `export_webgl()`.

Exemple — `AIVideoPlugin` : `generate_t2v()`, `generate_i2v()`, `get_cache_stats()`.

## Statut d'implémentation

- `DeepBl4nder/plugins/` : `Plugin` (ABC), `PluginRegistry` (13 plugins : blender,
  ue5, godot, ai-video, render-farm, ffmpeg, audio, tts, storage, asset-library, subtitle, git,
  knowledge-graph), `BlenderPlugin` (inspect / execute / render / save / load,
  fail-closed via le validateur AST) ;
- `DeepBl4nder/bridges/` : `BlenderBridge`, `UE5Bridge`, `GodotBridge`, `AIVideoBridge`
  — clients REST pour les moteurs externes ;
- `DeepBl4nder/agents/` : `BlenderAgent`, `UE5Agent`, `GodotAgent`, `AIVideoAgent`
  — agents NOOA pour chaque moteur ;
- `DeepBl4nder/plugins/tools.py` : `Tool` + `ToolRegistry`, liste canonique des
  8 tools importants, tous fonctionnels (branchés sur Blender, audio, ffmpeg) ;
- exposés par la gateway (`/plugins`, `/tools`, `/skills`, `/workers`, `/status`)
  et le CLI `inspect`.
- Les frontières dépendant d'un binaire externe (ffmpeg, git, TTS, Blender, UE5, Godot)
  sont prêtes : `available()` reflète la présence du binaire et les opérations
  échouent explicitement (`PluginError`) s'il manque à l'exécution.
- Les serveurs REST (UE5, Godot, AI Video) sont optionnels et configurable via
  des profils Docker (`profiles: ["ue5"]`, `profiles: ["godot"]`, `profiles: ["ai-video"]`).

