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

Plugins prévus : `blender`, `render-farm`, `ffmpeg`, `audio`, `tts`, `storage`,
`asset-library`, `subtitle`, `git`, `knowledge-graph`.

Exemple — `BlenderPlugin` : `inspect_scene()`, `execute_python()`, `render()`,
`save_scene()`, `load_asset()`.

## Statut d'implémentation

- `DeepBl4nder/plugins/` : `Plugin` (ABC), `PluginRegistry` (10 plugins : blender,
  render-farm, ffmpeg, audio, tts, storage, asset-library, subtitle, git,
  knowledge-graph), `BlenderPlugin` (inspect / execute / render / save / load,
  fail-closed via le validateur AST) ;
- `DeepBl4nder/plugins/tools.py` : `Tool` + `ToolRegistry`, liste canonique des
  8 tools importants, tous fonctionnels (branchés sur Blender, audio, ffmpeg) ;
- exposés par la gateway (`/plugins`, `/tools`, `/skills`, `/workers`, `/status`)
  et le CLI `inspect`.
- Les frontières dépendant d'un binaire externe (ffmpeg, git, TTS, Blender)
  sont prêtes : `available()` reflète la présence du binaire et les opérations
  échouent explicitement (`PluginError`) s'il manque à l'exécution.

