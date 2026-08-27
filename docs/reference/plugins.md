# Référence Complète des Plugins DeepBl4nder

## Table des matières

- [Vue d'ensemble de l'architecture](#vue-densemble-de-larchitecture)
- [Module racine : `deepblender/plugins/__init__.py`](#module-racine--deepblenderplugins__init__py)
- [Fondations](#fondations)
  - [base.py — Classe abstraite Plugin](#basepy--classe-abstraite-plugin)
  - [registry.py — PluginRegistry](#registrypy--pluginregistry)
  - [tools.py — ToolRegistry](#toolspy--toolregistry)
- [Plugins Média](#plugins-média)
  - [media/\_\_init\_\_.py](#media__init__py)
  - [media/audio.py — AudioPlugin](#mediaaudiopy--audioplugin)
  - [media/tts.py — TTSPlugin](#mediattspy--ttsplugin)
  - [media/music.py — MusicPlugin](#mediamusicpy--musicplugin)
  - [media/lipsync.py — LipSyncPlugin](#medialipsyncpy--lipsyncplugin)
  - [media/subtitle.py — SubtitlePlugin](#mediasubtitlepy--subtitleplugin)
- [Plugins Rendu](#plugins-rendu)
  - [rendering/\_\_init\_\_.py](#rendering__init__py)
  - [rendering/blender.py — BlenderPlugin](#renderingblenderpy--blenderplugin)
  - [rendering/ffmpeg.py — FFmpegPlugin](#renderingffmpegpy--ffmpegplugin)
  - [rendering/render_farm.py — RenderFarmPlugin](#renderingrender_farmpy--renderfarmplugin)
- [Plugins Stockage](#plugins-stockage)
  - [storage/\_\_init\_\_.py](#storage__init__py)
  - [storage/storage.py — StoragePlugin](#storagestoragepy--storageplugin)
  - [storage/git.py — GitPlugin](#storagegitpy--gitplugin)
  - [storage/cache.py — CachePlugin](#storagecachepy--cacheplugin)
- [Plugins Connaissance](#plugins-connaissance)
  - [knowledge/\_\_init\_\_.py](#knowledge__init__py)
  - [knowledge/knowledge_graph.py — KnowledgeGraphPlugin](#knowledgeknowledge_graphpy--knowledgegraphplugin)
  - [knowledge/asset_library.py — AssetLibraryPlugin](#knowledgeasset_librarypy--assetlibraryplugin)
  - [knowledge/observability.py — ObservabilityPlugin](#knowledgeobservabilitypy--observabilityplugin)
- [Plugins Intégrations](#plugins-intégrations)
  - [integrations/\_\_init\_\_.py](#integrations__init__py)
  - [integrations/billing.py — BillingPlugin](#integrationsbillingpy--billingplugin)
- [Annexe : Constantes et configurations](#annexe--constantes-et-configurations)
- [Annexe : Variables d'environnement](#annexe--variables-denvironnement)
- [Annexe : Dépendances inter-modules](#annexe--dépendances-inter-modules)

---

## Vue d'ensemble de l'architecture

L'architecture plugins de DeepBl4nder suit un modèle **frontière externe** : chaque plugin est une passerelle vers un système externe (Blender, FFmpeg, TTS, Redis, Stripe…). Les agents NOOA restent le runtime agnostique ; ils interagissent avec les plugins via des **tools** ou du Python généré.

```
deepblender/plugins/
├── __init__.py              # Exports publics (TOUTES les classes)
├── base.py                  # Plugin (ABC) + PluginError
├── registry.py              # PluginRegistry (registre central, 10 builtins)
├── tools.py                 # Tool + ToolRegistry (8 tools canoniques)
│
├── media/                   # Plugins média
│   ├── __init__.py          # Exports: AudioPlugin, TTSPlugin, MusicPlugin, LipSyncPlugin, SubtitlePlugin, SubtitleEntry
│   ├── audio.py             # AudioPlugin (wave stdlib, ton, silence, ambience)
│   ├── tts.py               # TTSPlugin (Bark, Piper, fallback)
│   ├── music.py             # MusicPlugin (ACE-Step, MusicGen, fallback)
│   ├── lipsync.py           # LipSyncPlugin (Whisper, Rhubarb, RMS)
│   └── subtitle.py          # SubtitlePlugin + SubtitleEntry (SRT)
│
├── rendering/               # Plugins rendu
│   ├── __init__.py          # Exports: BlenderPlugin, FFmpegPlugin, RenderFarmPlugin + presets/functions
│   ├── blender.py           # BlenderPlugin (BlenderBridge, bpy headless)
│   ├── ffmpeg.py            # FFmpegPlugin + ColorGradePreset + ExportPreset + presets + fonctions level
│   └── render_farm.py       # RenderFarmPlugin (WorkerScheduler)
│
├── storage/                 # Plugins stockage
│   ├── __init__.py          # Exports: StoragePlugin, GitPlugin, CachePlugin
│   ├── storage.py           # StoragePlugin (filesystem, clé=path relatif)
│   ├── git.py               # GitPlugin (git CLI via WorkerProcess)
│   └── cache.py             # CachePlugin (Redis + fallback in-memory)
│
├── knowledge/               # Plugins connaissance
│   ├── __init__.py          # Exports: KnowledgeGraphPlugin, AssetLibraryPlugin, ObservabilityPlugin
│   ├── knowledge_graph.py   # KnowledgeGraphPlugin (JSON graph, nodes/edges)
│   ├── asset_library.py     # AssetLibraryPlugin (index JSON, hash SHA-256)
│   └── observability.py     # ObservabilityPlugin (Langfuse + JSONL)
│
└── integrations/            # Plugins intégrations externes
    ├── __init__.py          # Exports: BillingPlugin
    └── billing.py           # BillingPlugin (Stripe, plans, credits)
```

### Principes fondamentaux

1. **Plugin ≠ Agent** : Un plugin n'est pas un runtime agentique, c'est une frontière vers un système externe.
2. **Fail-closed** : Les opérations critiques passent par validation AST avant exécution.
3. **Fallback déterministe** : Chaque plugin média (TTS, music, lipsync) possède un fallback stdlib lorsque les modèles ne sont pas disponibles.
4. **Pas de micro-tools** : `move_object`, `rotate_object` etc. n'existent pas ; ces actions résultent du Code-as-Action généré.
5. **Tools canoniques (8)** : `inspect_scene`, `load_asset`, `save_blend`, `render`, `inspect_render`, `create_audio`, `compose`, `export`.

---

## Module racine : `deepblender/plugins/__init__.py`

**Fichier** : `deepblender/plugins/__init__.py`

### Rôle

Point d'entrée public du package. Ré-exporte **toutes** les classes et constants des sous-packages vers le namespace `deepblender.plugins`.

### Imports et exports

```python
# Base
from DeepBl4nder.plugins.base import Plugin, PluginError
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.plugins.tools import Tool, ToolRegistry

# Media
from DeepBl4nder.plugins.media import AudioPlugin, TTSPlugin, SubtitlePlugin, SubtitleEntry

# Rendering
from DeepBl4nder.plugins.rendering import BlenderPlugin, FFmpegPlugin, RenderFarmPlugin

# Storage
from DeepBl4nder.plugins.storage import StoragePlugin, GitPlugin

# Knowledge
from DeepBl4nder.plugins.knowledge import KnowledgeGraphPlugin, AssetLibraryPlugin
```

### `__all__`

```python
__all__ = [
    "Plugin", "PluginError", "PluginRegistry", "Tool", "ToolRegistry",
    "AudioPlugin", "TTSPlugin", "SubtitlePlugin", "SubtitleEntry",
    "BlenderPlugin", "FFmpegPlugin", "RenderFarmPlugin",
    "StoragePlugin", "GitPlugin",
    "KnowledgeGraphPlugin", "AssetLibraryPlugin",
]
```

> **Note** : `MusicPlugin`, `LipSyncPlugin`, `CachePlugin`, `ObservabilityPlugin` et `BillingPlugin` ne figurent pas dans `__all__` du module racine mais sont exportés par leurs sous-packages respectifs.

### Connexion au système

Tous les autres modules du projet importent les plugins via ce point d'entrée ou directement via les sous-packages.

---

## Fondations

---

### base.py — Classe abstraite Plugin

**Fichier** : `deepblender/plugins/base.py` (29 lignes)

#### Rôle

Définit le contrat minimal que tout plugin doit respecter. C'est une interface de frontière externe, pas un agent.

#### Classes

##### `PluginError(RuntimeError)`

| Propriété | Valeur |
|---|---|
| Hérite de | `RuntimeError` |
| Rôle | Exception levée lors d'un échec de plugin ou de tool |

Aucune méthode spécifique. Utilisé comme type d'erreur générique dans tous les plugins.

##### `Plugin(ABC)`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `""` | Identifiant unique du plugin |
| `description` | `str` | `""` | Description textuelle |

###### Méthodes

| Méthode | Paramètres | Type retour | Abstraite | Description |
|---|---|---|---|---|
| `available()` | — | `bool` | **Oui** | Vérifie si le système externe est joignable depuis cet hôte |
| `info()` | — | `dict[str, object]` | Non | Retourne `{"name": ..., "description": ..., "available": ...}` |

#### Connexion au système

- Est la base de **tous** les 14 plugins du système.
- Importé par `registry.py`, `tools.py`, et chaque module plugin.

---

### registry.py — PluginRegistry

**Fichier** : `deepblender/plugins/registry.py` (68 lignes)

#### Rôle

Registre central qui découvre, instancie et expose tous les plugins. Tous les plugins builtins sont instanciés à la création du registre.

#### Constante module

```python
_BUILTINS: dict[str, type[Plugin]] = {
    "blender":        BlenderPlugin,
    "ffmpeg":         FFmpegPlugin,
    "audio":          AudioPlugin,
    "tts":            TTSPlugin,
    "storage":        StoragePlugin,
    "asset-library":  AssetLibraryPlugin,
    "subtitle":       SubtitlePlugin,
    "git":            GitPlugin,
    "knowledge-graph": KnowledgeGraphPlugin,
    "render-farm":    RenderFarmPlugin,
}
```

> **Note** : `MusicPlugin`, `LipSyncPlugin`, `CachePlugin`, `ObservabilityPlugin` et `BillingPlugin` ne sont **pas** dans `_BUILTINS`. Ils doivent être enregistrés manuellement.

#### Classe `PluginRegistry`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `plugins` | `dict[str, Plugin]` | `{}` | Map `nom → instance` |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `__post_init__()` | — | `None` | Instancie tous les `_BUILTINS`. `RenderFarmPlugin` reçoit `plugins=self`. |
| `register(plugin)` | `plugin: Plugin` | `None` | Ajoute un plugin externe. Lève `ValueError` si `plugin.name` est vide. |
| `get(name)` | `name: str` | `Plugin` | Récupère un plugin par nom. Lève `KeyError` si introuvable. |
| `get_or_create(name)` | `name: str` | `Plugin` | Alias de `get()` (compatibilité). |
| `all_plugins()` | — | `list[Plugin]` | Tous les plugins instanciés. |
| `discover()` | — | `list[dict[str, object]]` | Appelle `info()` sur chaque plugin. |
| `available()` | — | `list[str]` | Noms des plugins dont `available() == True`. |

#### Connexion au système

- Importé par `tools.py` (pour accéder aux plugins et créer les tools).
- Importé par `render_farm.py` (pour accéder à `BlenderPlugin`).
- Importé par l'orchestrateur principal pour initialiser le registre.

---

### tools.py — ToolRegistry

**Fichier** : `deepblender/plugins/tools.py` (62 lignes)

#### Rôle

Définit les 8 **tools canoniques** (primitives d'action importantes) qui constituent l'API que les agents NOOA utilisent pour interagir avec les plugins.

#### Classe `Tool`

`@dataclass(frozen=True)` — Immutable

| Propriété | Type | Description |
|---|---|---|
| `name` | `str` | Identifiant du tool |
| `description` | `str` | Description textuelle |
| `run` | `Callable[..., Any]` | Fonction d'exécution (liée au plugin) |

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `execute(*args, **kwargs)` | `*args: Any, **kwargs: Any` | `Any` | Délègue à `self.run()` |

#### Classe `ToolRegistry`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `plugins` | `PluginRegistry` | `PluginRegistry()` | Registre de plugins partagé |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `tools()` | — | `list[Tool]` | Retourne les 8 tools canoniques |
| `names()` | — | `list[str]` | Noms des tools |
| `get(name)` | `name: str` | `Tool` | Récupère un tool par nom. Lève `KeyError` si introuvable. |

##### Les 8 tools canoniques

| # | Nom | Description | Plugin source | Méthode |
|---|---|---|---|---|
| 1 | `inspect_scene` | Inspecte les objets de la scène Blender | `blender` | `BlenderPlugin.inspect_scene` |
| 2 | `load_asset` | Append un asset dans la scène Blender | `blender` | `BlenderPlugin.load_asset` |
| 3 | `save_blend` | Sauvegarde la scène Blender | `blender` | `BlenderPlugin.save_scene` |
| 4 | `render` | Lance un rendu de la scène Blender | `blender` | `BlenderPlugin.render` |
| 5 | `inspect_render` | Vérifie un rendu produit (image / QA) | `blender` | `BlenderPlugin.inspect_render` |
| 6 | `create_audio` | Génère une piste audio (ambiance / ton) | `audio` | `AudioPlugin.generate_ambience` |
| 7 | `compose` | Assemble une vidéo et une piste audio (mux) | `ffmpeg` | `FFmpegPlugin.mux` |
| 8 | `export` | Transcode la séquence vers un codec cible | `ffmpeg` | `FFmpegPlugin.transcode` |

#### Connexion au système

- Importé par le module racine `__init__.py`.
- Utilisé par les agents NOOA pour découvrir et appeler les primitives d'action.

---

## Plugins Média

---

### media/\_\_init\_\_.py

**Fichier** : `deepblender/plugins/media/__init__.py` (12 lignes)

#### Rôle

Point d'entrée du sous-package `media`. Ré-exporte toutes les classes des modules média.

#### Exports

```python
__all__ = [
    "AudioPlugin", "TTSPlugin", "MusicPlugin", "LipSyncPlugin",
    "SubtitlePlugin", "SubtitleEntry",
]
```

---

### media/audio.py — AudioPlugin

**Fichier** : `deepblender/plugins/media/audio.py` (63 lignes)

#### Rôle

Synthèse et inspection audio **déterministes** utilisant uniquement la stdlib Python (`wave`, `struct`, `math`, `random`). Pas de dépendances externes.

#### Constante module

```python
_RATE = 44100  # Fréquence d'échantillonnage (Hz)
```

#### Classe `AudioPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"audio"` | Identifiant |
| `description` | `str` | `"Synthèse et inspection audio déterministes (stdlib wave)."` | Description |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` (stdlib uniquement) |
| `generate_tone(frequency, duration, out_path, amplitude)` | `frequency: float, duration: float, out_path: Path, amplitude: float = 0.25` | `Path` | Génère un ton sinusoïdal simple |
| `generate_silence(duration, out_path)` | `duration: float, out_path: Path` | `Path` | Génère un fichier silencieux |
| `generate_ambience(duration, out_path, seed)` | `duration: float, out_path: Path, seed: int = 0` | `Path` | Bruit blanc doux déterministe (seed fixe) |
| `inspect(path)` | `path: Path` | `dict[str, float]` | Retourne `{channels, sample_rate, sample_width, duration}`. Lève `PluginError` si fichier introuvable. |

#### Fonctions module

| Fonction | Paramètres | Type retour | Description |
|---|---|---|---|
| `_pcm16(samples)` | `samples: list[int]` | `bytes` | Convertit une liste d'entiers en PCM 16-bit little-endian, clippé à [-32768, 32767] |
| `_write_wav(path, frames, rate)` | `path: Path, frames: bytes, rate: int` | `Path` | Écrit un fichier WAV mono 16-bit |

#### Connexion au système

- Utilisé par `ToolRegistry` pour le tool `create_audio` (via `generate_ambience`).
- Les files WAV générées sont consommées par `FFmpegPlugin.mux()` et `FFmpegPlugin.mix_audio_tracks()`.

---

### media/tts.py — TTSPlugin

**Fichier** `deepblender/plugins/media/tts.py` (204 lignes)

#### Rôle

Synthèse vocale (Text-to-Speech) avec fallback en cascade : Bark (HuggingFace) → Piper TTS (binaire local) → fallback déterministe (ton sinusoïdal).

#### Constante module

```python
_RATE = 24000  # Fréquence d'échantillonnage TTS (Hz)
```

#### Classe `TTSPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"tts"` | Identifiant |
| `description` | `str` | `"Synthese vocale : Bark (local), CosyVoice, fallback wave."` | Description |

##### Méthodes publiques

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | `True` si au moins un de `BARK_MODEL_PATH`, `COSYVOICE_MODEL_PATH`, `TTS_BINARY` est défini |
| `generate_voice(text, out_path, language, emotion, speaker)` | `text: str, out_path: Path, language: str = "fr", emotion: str = "neutral", speaker: str \| None = None` | `Path` | Génère un fichier WAV. Cascade : Bark → Piper → fallback. |
| `mix_tracks(tracks, out_path, sample_rate)` | `tracks: list[tuple[Path, float]], out_path: Path, sample_rate: int = 44100` | `Path` | Mixe plusieurs pistes WAV avec volumes donnés (0.0–1.0) |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_generate_bark(text, out_path, language, emotion, speaker)` | Génération via Bark (HuggingFace). Convertit numpy → WAV int16. |
| `_generate_piper(text, out_path, language)` | Génération via Piper TTS (binaire local, subprocess). Mapping langues : `fr→fr_FR-siwis-medium`, `en→en_US-lessac-medium`, `es→es_ES-sharvard-medium`, `de→de_DE-karlsson-medium`, `ja→ja_JP-jsmedium` |
| `_generate_fallback(text, out_path)` | Fallback : tone pulse basé sur `len(text) * 0.05` secondes (clamp 0.5–10s), fréquence 200Hz |
| `_bark_history_prompt(language, emotion, speaker)` | Construit le prompt d'historique Bark : `v2/{lang}/{speaker}{emotion_suffix}` |
| `_generate_silence(duration, out_path)` | Génère un fichier silencieux |

##### Mapping des langues Bark

```python
lang_map = {"fr": "v2/fr", "en": "v2/en", "de": "v2/de", "es": "v2/es"}
```

##### Mapping des émotions Bark

```python
emotion_map = {
    "happy": "_happy", "sad": "_sad", "angry": "_angry",
    "fearful": "_fearful", "surprised": "_surprised",
}
# Default (neutral) → suffixe vide
```

#### Connexion au système

- Enregistré dans `_BUILTINS` du `PluginRegistry` sous la clé `"tts"`.
- N'est pas exposé comme tool canonique (utilisé directement via `generate_voice` ou via du Python généré).

---

### media/music.py — MusicPlugin

**Fichier** : `deepblender/plugins/media/music.py` (182 lignes)

#### Rôle

Génération musicale originale avec fallback en cascade : ACE-Step (local CUDA) → MusicGen (Meta) → fallback déterministe (arpèges/armoniques).

#### Constante module

```python
_RATE = 44100  # Fréquence d'échantillonnage (Hz)
```

#### Classe `MusicPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"music"` | Identifiant |
| `description` | `str` | `"Generation musicale originale : ACE-Step, MusicGen, synthese."` | Description |

##### Méthodes publiques

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` (fallback déterministe) |
| `generate_music(description, duration, out_path, mood, tempo, key, genre)` | `description: str, duration: float, out_path: Path, mood: str = "neutral", tempo: int = 120, key: str = "C", genre: str = ""` | `Path` | Cascade : ACE-Step → MusicGen → fallback |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_generate_ace_step(description, duration, out_path, mood, tempo)` | Génération via ACE-Step (CUDA, modèle `ACE-Step/ACE-Step-1.5B`, 100 steps, guidance_scale=7.5) |
| `_generate_musicgen(description, duration, out_path, mood)` | Génération via MusicGen (`facebook/musicgen-small`, sample rate 32000) |
| `_generate_deterministic(description, duration, out_path, mood, tempo, key)` | Synthèse déterministe : arpèges, accords, percussions (voir config ci-dessous) |

##### Configuration des moods (synthèse déterministe)

| Mood | `base_freq` | `scale` (intervalles en demi-tons) | `energy` |
|---|---|---|---|
| `happy` | 440.0 | `[0, 2, 4, 5, 7, 9, 11]` (majeur) | 0.3 |
| `sad` | 220.0 | `[0, 2, 3, 5, 7, 8, 10]` (mineur) | 0.15 |
| `epic` | 330.0 | `[0, 2, 4, 5, 7, 9, 11]` (majeur) | 0.35 |
| `dark` | 185.0 | `[0, 1, 3, 5, 6, 8, 10]` (locrien) | 0.2 |
| `neutral` | 261.6 | `[0, 2, 4, 5, 7, 9, 11]` (majeur) | 0.2 |

##### Offset des touches

```python
key_offsets = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
```

#### Connexion au système

- **Non** dans `_BUILTINS` du `PluginRegistry`. Doit être enregistré manuellement.
- Les WAV générés peuvent être mixés via `TTSPlugin.mix_tracks` ou `FFmpegPlugin.mix_audio_tracks`.

---

### media/lipsync.py — LipSyncPlugin

**Fichier** : `deepblender/plugins/media/lipsync.py` (285 lignes)

#### Rôle

Synchronisation lèvres avancée : extraction de phonèmes → génération de blendshapes/morph targets pour animation faciale.

#### Constantes module

```python
PHONEME_BLENDSHAPES: dict[str, dict[str, float]]
```

Mapping phonème → poids de blendshape. Phonèmes supportés :

| Phonème | Description | Blendshapes principaux |
|---|---|---|
| `sil` | Silence | (aucun) |
| `PP` | Bilabiale (p, b, m) | mouthFunnel=0.8, mouthPucker=0.2 |
| `FF` | Labio-dentale (f, v) | mouthFunnel=0.3, jawOpen=0.3 |
| `TH` | Dentale (th) | jawOpen=0.4, mouthFunnel=0.2 |
| `DD` | Alvéolaire (d, t) | jawOpen=0.3, mouthLeft=0.1, mouthRight=0.1 |
| `kk` | Vélaire (g, k, h) | jawOpen=0.2, mouthFunnel=0.4 |
| `CH` | Affriquée (j, ch) | jawOpen=0.15, mouthPucker=0.3, mouthLeft=0.2 |
| `SS` | Sifflante (s, z) | jawOpen=0.1, mouthLeft=0.1, mouthRight=0.1 |
| `nn` | Nasale (n, l) | jawOpen=0.05 |
| `RR` | Rhotique (r) | jawOpen=0.15, mouthFunnel=0.3 |
| `aa` | Voyelle ouverte (a) | jawOpen=0.8, mouthFunnel=0.3 |
| `E` | Moyenne antérieure (é, e) | jawOpen=0.5, mouthLeft=0.3, mouthRight=0.3 |
| `ih` | Basse antérieure (i) | jawOpen=0.3, mouthLeft=0.2, mouthRight=0.2 |
| `oh` | Moyenne postérieure (o) | jawOpen=0.6, mouthFunnel=0.5, mouthPucker=0.3 |
| `ou` | Basse postérieure (ou) | jawOpen=0.4, mouthFunnel=0.7, mouthPucker=0.5 |

#### Classes

##### `PhonemeTiming`

`@dataclass(frozen=False)`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `phoneme` | `str` | — | Identifiant du phonème |
| `start_time` | `float` | — | Début en secondes |
| `end_time` | `float` | — | Fin en secondes |
| `confidence` | `float` | `1.0` | Confiance (0.0–1.0) |

##### `LipSyncFrame`

`@dataclass`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `time` | `float` | — | Timestamp en secondes |
| `jawOpen` | `float` | `0.0` | Ouverture mâchoire |
| `mouthFunnel` | `float` | `0.0` | Forme entonnoir |
| `mouthPucker` | `float` | `0.0` | Forme purse |
| `mouthLeft` | `float` | `0.0` | Décalage gauche |
| `mouthRight` | `float` | `0.0` | Décalage droit |
| `mouthClose` | `float` | `0.0` | Fermeture |

| Méthode | Retour | Description |
|---|---|---|
| `to_dict()` | `dict[str, float]` | Sérialisation en dictionnaire plat |

##### `LipSyncPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"lipsync"` | Identifiant |
| `description` | `str` | `"Synchronisation levres : Whisper, Rhubarb, fallback RMS."` | Description |

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` (fallback RMS) |
| `extract_phonemes(audio_path)` | `audio_path: Path` | `list[PhonemeTiming]` | Cascade : Whisper → Rhubarb → RMS |
| `generate_blendshapes(phonemes, fps)` | `phonemes: list[PhonemeTiming], fps: float = 24.0` | `list[LipSyncFrame]` | Convertit les phonèmes en frames de blendshape avec lissage |
| `export_json(frames, out_path)` | `frames: list[LipSyncFrame], out_path: Path` | `Path` | Exporte les blendshapes en JSON pour Blender/UE5 |

##### Mapping caractère → phonème (`_char_to_phoneme`)

```python
{
    "a": "aa", "e": "E", "i": "ih", "o": "oh", "u": "ou",
    "b": "PP", "p": "PP", "m": "PP",
    "f": "FF", "v": "FF",
    "d": "DD", "t": "DD", "n": "nn", "l": "nn",
    "g": "kk", "k": "kk", "h": "kk",
    "j": "CH", "ch": "CH", "s": "SS", "z": "SS",
    "r": "RR",
}
```

##### Thresholds RMS pour détection de phonèmes (`_extract_rms`)

| RMS | Phonème |
|---|---|
| < 0.02 | `sil` |
| < 0.08 | `nn` |
| < 0.15 | `aa` |
| < 0.25 | `E` |
| ≥ 0.25 | `oh` |

##### Lissage

Fenêtre glissante de 3 frames par défaut, moyenne arithmétique sur chaque blendshape.

#### Connexion au système

- **Non** dans `_BUILTINS` du `PluginRegistry`. Doit être enregistré manuellement.
- Output JSON exportable pour Blender (Shape Keys) ou Unreal Engine 5 (Morph Targets).

---

### media/subtitle.py — SubtitlePlugin

**Fichier** : `deepblender/plugins/media/subtitle.py` (64 lignes)

#### Rôle

Génération et parsing de sous-titres au format SRT.

#### Constante module

```python
_BLOCK = re.compile(
    r"(\d+)\s*\n"
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n"
    r"(.*?)(?=\n\n|\Z)", re.S
)
```

Regex de parsing SRT : capture index, timestamps start/end, et texte.

#### Classes

##### `SubtitleEntry`

`@dataclass(frozen=True)`

| Propriété | Type | Description |
|---|---|---|
| `index` | `int` | Numéro d'ordre |
| `start` | `float` | Début en secondes |
| `end` | `float` | Fin en secondes |
| `text` | `str` | Texte du sous-titre |

##### `SubtitlePlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"subtitle"` | Identifiant |
| `description` | `str` | `"Génération et parsing de sous-titres (SRT / VTT)."` | Description |

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` |
| `generate(entries, path)` | `entries: list[SubtitleEntry], path: Path` | `Path` | Écrit un fichier SRT |
| `parse(path)` | `path: Path` | `list[SubtitleEntry]` | Parse un fichier SRT. Lève `PluginError` si introuvable. |

#### Fonctions module

| Fonction | Paramètres | Retour | Description |
|---|---|---|---|
| `_fmt(seconds)` | `seconds: float` | `str` | Formate `float → "HH:MM:SS,mmm"` |
| `_parse_ts(ts)` | `ts: str` | `float` | Parse `"HH:MM:SS,mmm" → float secondes` |

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"subtitle"`.
- Les entrées `SubtitleEntry` sont typiquement produites par les agents NOOA à partir de scripts ou de transcription TTS.

---

## Plugins Rendu

---

### rendering/\_\_init\_\_.py

**Fichier** : `deepblender/plugins/rendering/__init__.py` (21 lignes)

#### Exports

```python
__all__ = [
    "BlenderPlugin", "FFmpegPlugin", "RenderFarmPlugin",
    "ColorGradePreset", "ExportPreset",
    "EXPORT_PRESETS", "COLOR_GRADE_PRESETS",
    "apply_color_grading", "export_video", "mix_audio_tracks",
]
```

Inclut les classes plugin, les classes preset, les dictionnaires de presets prédéfinis, et les fonctions de commodité au niveau module.

---

### rendering/blender.py — BlenderPlugin

**Fichier** : `deepblender/plugins/rendering/blender.py` (72 lignes)

#### Rôle

Frontière d'intégration vers Blender headless. Toutes les opérations passent par le bridge (`blender -b -P`) avec validation AST fail-closed.

#### Constantes module

```python
_INSPECT_TEMPLATE = (
    "import bpy\n"
    "for obj in bpy.context.scene.objects:\n"
    "    print(obj.name)\n"
)

_RENDER_TEMPLATE = (
    "import bpy\n"
    "scene = bpy.context.scene\n"
    "scene.render.image_settings.file_format = 'PNG'\n"
    "scene.render.filepath = 'render_0001.png'\n"
    "bpy.ops.render.render(write_still=True)\n"
)
```

#### Classe `BlenderPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"blender"` | Identifiant |
| `description` | `str` | `"Inspect, execute, render, save et load sur Blender headless."` | Description |
| `bridge` | `BlenderBridge` | `BlenderBridge()` | Instance du bridge Blender |
| `workdir` | `Path` | `Path.cwd()` | Répertoire de travail |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Délègue à `self.bridge.available()` |
| `execute_python(script)` | `script: BlenderScript` | `ProcessResult` | Exécute un script bpy généré (validé AST puis lancé) |
| `inspect_scene(scene_name)` | `scene_name: str = "scene"` | `ProcessResult` | Liste les objets de la scène |
| `render(scene_name)` | `scene_name: str = "scene"` | `ProcessResult` | Lance un rendu PNG |
| `inspect_render(render_path)` | `render_path: Path` | `dict[str, object]` | Vérifie existence et taille du rendu. Retourne `{exists, bytes, ok}`. |
| `save_scene(scene_name, path)` | `scene_name: str, path: Path` | `ProcessResult` | Sauvegarde le fichier .blend |
| `load_asset(scene_name, path)` | `scene_name: str, path: Path` | `ProcessResult` | Append un asset dans la scène via `bpy.ops.wm.append` |

#### Dépendances internes

- `DeepBl4nder.bridges.blender.bridge.BlenderBridge`
- `DeepBl4nder.bridge.worker.ProcessResult`
- `DeepBl4nder.domain.scene.BlenderScript`

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"blender"`.
- Fournit 5 des 8 tools canoniques (`inspect_scene`, `load_asset`, `save_blend`, `render`, `inspect_render`).
- Le `bridge` est partagé avec `RenderFarmPlugin`.

---

### rendering/ffmpeg.py — FFmpegPlugin

**Fichier** : `deepblender/plugins/rendering/ffmpeg.py` (259 lignes)

#### Rôle

Frontière d'intégration FFmpeg : transcodage, color grading, export vidéo, et mixage audio. Inclut des presets prédéfinis et des fonctions de commodité au niveau module.

#### Classe `ColorGradePreset`

`@dataclass`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | — | Nom du preset |
| `lut` | `str` | `""` | Chemin vers un fichier LUT 3D |
| `brightness` | `float` | `0.0` | Luminosité (-1.0 à 1.0) |
| `contrast` | `float` | `1.0` | Contraste |
| `saturation` | `float` | `1.0` | Saturation |
| `gamma` | `float` | `1.0` | Gamma |
| `temperature` | `float` | `0.0` | Température couleur (kelvins) |
| `film_grain` | `float` | `0.0` | Intensité du grain film (0.0–1.0) |
| `vignette` | `float` | `0.0` | Intensité du vignettage (0.0–1.0) |

| Méthode | Retour | Description |
|---|---|---|
| `to_filter_string()` | `str` | Génère la chaîne de filtres FFmpeg correspondante |

**Filtres FFmpeg générés** :
- `eq=brightness=...:contrast=...:saturation=...:gamma=...` (si modifié)
- `colortemperature=temperature=...` (si ≠ 0)
- `noise=alls=...:allf=t` (si film_grain > 0)
- `vignette=angle=PI/...` (si vignette > 0)
- `lut3d=file='...'` (si LUT fourni)
- `colorbalance=...` (uniquement pour les presets `cinematic`, `warm`, `cold`)

**Colorbalance par preset** :
| Preset | Valeur |
|---|---|
| `cinematic` | `rs=0.05:gs=0.02:bs=-0.03:rm=0.03:gm=0.01:bm=-0.02` |
| `warm` | `rs=0.1:gs=0.05:bs=-0.05` |
| `cold` | `rs=-0.05:gs=0.0:bs=0.1` |

#### Classe `ExportPreset`

`@dataclass`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | — | Nom du preset |
| `codec` | `str` | `"libx264"` | Codec vidéo |
| `pixel_format` | `str` | `"yuv420p"` | Format pixel |
| `crf` | `int` | `18` | Qualité (CRF) |
| `bitrate` | `str` | `""` | Bitrate fixe (si défini, ignores CRF) |
| `extra_args` | `list[str] \| None` | `None` | Arguments FFmpeg supplémentaires |

| Méthode | Retour | Description |
|---|---|---|
| `to_ffmpeg_args()` | `list[str]` | Convertit en liste d'arguments FFmpeg |

#### Dictionnaires de presets

##### `EXPORT_PRESETS`

| Clé | Nom | Codec | Pixel Format | CRF/Bitrate | Extra |
|---|---|---|---|---|---|
| `h264_1080p` | H.264 1080p | libx264 | yuv420p | crf=18 | — |
| `h264_4k` | H.264 4K | libx264 | yuv420p | crf=16 | `-s 3840x2160` |
| `prores_422` | ProRes 422 | prores_ks | yuv422p10le | — | `-profile:v 2 -vendor apl0` |
| `prores_4444` | ProRes 4444 | prores_ks | yuva444p10le | — | `-profile:v 4 -vendor apl0` |
| `dnxhd` | DNxHD | dnxhd | yuv422p | bitrate=185M | — |
| `webm_vp9` | WebM VP9 | libvpx-vp9 | yuv420p | bitrate=0, crf=30 | — |
| `gif` | GIF | gif | rgb24 | — | `-vf fps=15,scale=480:-1:flags=lanczos` |

##### `COLOR_GRADE_PRESETS`

| Clé | Nom | Contrast | Saturation | Température | Autres |
|---|---|---|---|---|---|
| `cinematic` | Cinema | 1.2 | 0.85 | 200 | — |
| `warm` | Chaud | — | 1.1 | 400 | brightness=0.02 |
| `cold` | Froid | — | 0.9 | -300 | — |
| `vintage` | Vintage | 1.1 | 0.7 | — | film_grain=0.3, vignette=0.5 |
| `noir` | Noir & Blanc | 1.3 | 0.0 | — | — |
| `vivid` | Vif | 1.1 | 1.4 | — | brightness=0.03 |
| `flat` | Plat | 0.8 | 0.9 | — | gamma=1.1 |

#### Classe `FFmpegPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"ffmpeg"` | Identifiant |
| `description` | `str` | `"Transcodage, color grading, export et mixage audio via ffmpeg."` | Description |
| `ffmpeg_exe` | `str \| None` | `None` | Chemin binaire FFmpeg (sinon `FFMPEG_EXE` env) |
| `timeout` | `float` | `600.0` | Timeout par opération (secondes) |

Champ privé initialisé dans `__post_init__` :

| Champ | Type | Description |
|---|---|---|
| `_exe` | `str` | Binaire FFmpeg résolu (`ffmpeg_exe` → `FFMPEG_EXE` → `"ffmpeg"`) |
| `_worker` | `WorkerProcess` | Instance de worker pour exécuter les commandes |

##### Méthodes publiques

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | `True` si `ffmpeg` trouvé dans PATH |
| `transcode(source, destination, codec, crf)` | `source: Path, destination: Path, codec: str = "libx264", crf: str = "23"` | `Path` | Transcode une source vers un codec |
| `mux(video, audio, destination)` | `video: Path, audio: Path, destination: Path` | `Path` | Mixe vidéo + audio (copy video, AAC audio) |
| `extract_audio(source, destination, codec)` | `source: Path, destination: Path, codec: str = "pcm_s16le"` | `Path` | Extrait la piste audio |
| `color_grade(input_path, output_path, preset, custom)` | `input_path: Path, output_path: Path, preset: str = "cinematic", custom: ColorGradePreset \| None = None` | `Path` | Applique le color grading |
| `export_video(input_path, output_path, preset, custom_preset, audio_codec, audio_bitrate)` | Tous les paramètres avec defaults | `Path` | Exporte la vidéo avec preset |
| `mix_audio_tracks(tracks, output_path, duration, sample_rate, normalize_lufs, target_lufs)` | `tracks: list[tuple[Path, float]], output_path: Path, duration: float \| None = None, sample_rate: int = 44100, normalize_lufs: bool = True, target_lufs: float = -14.0` | `Path` | Mixe N pistes audio avec volumes, normalisation LUFS |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_run(*args)` | Exécute ffmpeg via `WorkerProcess`. Lève `PluginError` si non disponible ou en erreur. |
| `_run_path(*args)` | Exécute et retourne le dernier argument comme `Path`. |

##### Paramètres `mix_audio_tracks`

| Paramètre | Type | Default | Description |
|---|---|---|---|
| `tracks` | `list[tuple[Path, float]]` | — | Liste `(chemin_wav, volume_0_1)` |
| `output_path` | `Path` | — | Fichier de sortie |
| `duration` | `float \| None` | `None` | Durée max (None = durée de la première piste) |
| `sample_rate` | `int` | `44100` | Fréquence d'échantillonnage |
| `normalize_lufs` | `bool` | `True` | Activer la normalisation LUFS |
| `target_lufs` | `float` | `-14.0` | Niveau cible LUFS |

**Filtre FFmpeg LUFS** : `loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=summary`

#### Fonctions module (backward compat)

| Fonction | Signature | Description |
|---|---|---|
| `apply_color_grading(input_path, output_path, preset, custom)` | Identique à `FFmpegPlugin.color_grade` | Singleton FFmpegPlugin |
| `export_video(input_path, output_path, preset, custom_preset, audio_codec, audio_bitrate)` | Identique à `FFmpegPlugin.export_video` | Singleton FFmpegPlugin |
| `mix_audio_tracks(tracks, output_path, duration, sample_rate, normalize_lufs, target_lufs)` | Identique à `FFmpegPlugin.mix_audio_tracks` | Singleton FFmpegPlugin |

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"ffmpeg"`.
- Fournit 2 tools canoniques (`compose` via `mux`, `export` via `transcode`).
- Les fonctions module permettent un usage sans instanciation explicite.

---

### rendering/render_farm.py — RenderFarmPlugin

**Fichier** : `deepblender/plugins/rendering/render_farm.py` (58 lignes)

#### Rôle

Distribution des rendus sur un pool de workers CPU/GPU via `WorkerScheduler`.

#### Classe `RenderFarmPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"render-farm"` | Identifiant |
| `description` | `str` | `"Soumission et répartition des rendus sur le pool de workers."` | Description |
| `plugins` | `PluginRegistry \| None` | `None` | Registre partagé (pour accéder à BlenderPlugin) |
| `_scheduler` | `WorkerScheduler \| None` | `None` | (privé) Scheduler de workers |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | `True` si `scheduler.worker_count >= 1` |
| `submit(script, workdir)` | `script: BlenderScript, workdir: Path` | `Future[ProcessResult]` | Soumet un rendu au pool (asynchrone) |
| `worker_count()` | — | `int` | Nombre de workers disponibles |
| `gpu_count()` | — | `int` | Nombre de GPUs disponibles |
| `add_workers(count, kind)` | `count: int, kind: str = "cpu"` | `None` | Ajoute des workers au pool |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_get_scheduler()` | Lazy-init du `WorkerScheduler` |
| `_get_bridge()` | Récupère le `BlenderBridge` depuis `BlenderPlugin` dans le registre |

#### Dépendances internes

- `DeepBl4nder.bridges.blender.scheduler.WorkerScheduler`
- `DeepBl4nder.bridges.blender.bridge.BlenderBridge`
- `DeepBl4nder.bridge.worker.ProcessResult`
- `DeepBl4nder.domain.scene.BlenderScript`

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"render-farm"`.
- Reçoit le `PluginRegistry` au moment de l'instanciation (dans `PluginRegistry.__post_init__`).
- Le `BlenderPlugin.bridge` est partagé via le registre pour éviter les doublons.

---

## Plugins Stockage

---

### storage/\_\_init\_\_.py

**Fichier** : `deepblender/plugins/storage/__init__.py` (7 lignes)

#### Exports

```python
__all__ = ["StoragePlugin", "GitPlugin", "CachePlugin"]
```

---

### storage/storage.py — StoragePlugin

**Fichier** : `deepblender/plugins/storage/storage.py` (43 lignes)

#### Rôle

Persistance et récupération des artifacts dans un répertoire racine du filesystem. Sécurisé contre les chemins relatifs qui échappent la racine.

#### Classe `StoragePlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"storage"` | Identifiant |
| `description` | `str` | `"Persistance et récupération des artifacts (filesystem)."` | Description |
| `root` | `Path` | `Path.cwd() / "artifacts"` | Répertoire racine de stockage |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` |
| `store(artifact, key)` | `artifact: Path, key: str` | `Path` | Copie un fichier vers `root/key`. Lève `PluginError` si clé échappe la racine. |
| `retrieve(key)` | `key: str` | `Path` | Récupère un fichier. Lève `PluginError` si introuvable ou clé échappe. |
| `keys(prefix)` | `prefix: str = ""` | `list[str]` | Liste les clés (chemins relatifs POSIX) filtrées par préfixe. |

#### Sécurité

Vérification de containment : `str(destination).startswith(str(self.root.resolve()))` pour chaque opération. Rejet avec `PluginError` si la clé tente d'échapper la racine (path traversal).

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"storage"`.
- Les artifacts stockés incluent les rendus, les sous-titres, les exports audio, etc.

---

### storage/git.py — GitPlugin

**Fichier** : `deepblender/plugins/storage/git.py` (48 lignes)

#### Rôle

Frontière d'intégration Git pour versionner la production (artifacts, specs, scènes).

#### Classe `GitPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"git"` | Identifiant |
| `description` | `str` | `"Versionning de la production (git)."` | Description |
| `git_exe` | `str \| None` | `None` | Chemin binaire git (sinon `GIT_EXE` env) |

Champ privé :

| Champ | Type | Description |
|---|---|---|
| `_exe` | `str` | Binaire résolu (`git_exe` → `GIT_EXE` → `"git"`) |
| `_worker` | `WorkerProcess` | Worker pour exécuter les commandes git |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | `True` si `git` trouvé dans PATH |
| `commit(repo, message)` | `repo: Path, message: str` | `str` | `git add -A && git commit -m "..."` |
| `tag(repo, name)` | `repo: Path, name: str` | `str` | `git tag <name>` |
| `status(repo)` | `repo: Path` | `str` | `git status --short` |
| `head(repo)` | `repo: Path` | `str` | `git rev-parse --short HEAD` |

#### Dépendances internes

- `DeepBl4nder.bridge.worker.WorkerCommand`
- `DeepBl4nder.bridge.worker.WorkerProcess`

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"git"`.
- Utilisé pour versionner les milestones de production.

---

### storage/cache.py — CachePlugin

**Fichier** : `deepblender/plugins/storage/cache.py` (143 lignes)

#### Rôle

Cache distribué Redis avec fallback in-memory. Supporte les opérations clé-valeur, le pub/sub, et les files de tâches.

#### Classe `CachePlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"cache"` | Identifiant |
| `description` | `str` | `"Cache distribue Redis avec fallback in-memory."` | Description |
| `_redis_client` | `Any` | `None` | Client Redis (privé) |
| `_memory_cache` | `dict[str, tuple[Any, float]]` | `{}` | Cache in-memory `{clé: (valeur, expiry_timestamp)}` |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` (fallback in-memory) |
| `get(key)` | `key: str` | `Any \| None` | Récupère une valeur (TTL respecté) |
| `set(key, value, ttl)` | `key: str, value: Any, ttl: int = 3600` | `None` | Stocke avec TTL (défaut 1h) |
| `delete(key)` | `key: str` | `None` | Supprime une entrée |
| `invalidate_prefix(prefix)` | `prefix: str` | `int` | Supprime toutes les clés avec le préfixe. Retourne le nombre supprimé. |
| `publish(channel, message)` | `channel: str, message: dict[str, Any]` | `None` | Publie sur un canal Redis (pub/sub) |
| `subscribe(channel)` | `channel: str` | `Any` | S'abonne à un canal Redis. Retourne l'objet pubsub. |
| `queue_task(queue, task)` | `queue: str, task: dict[str, Any]` | `None` | Ajoute une tâche à une file (RPUSH) |
| `dequeue_task(queue, timeout)` | `queue: str, timeout: int = 0` | `dict[str, Any] \| None` | Retire une tâche d'une file (BLPOP) |

#### Initialisation Redis

```python
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
```

Clés Redis préfixées par `db:cache:` pour les opérations clé-valeur, `db:queue:` pour les files.

#### Connexion au système

- **Non** dans `_BUILTINS` du `PluginRegistry`. Doit être enregistré manuellement.
- Utilisé pour cacher les appels LLM et les résultats intermédiaires.

---

## Plugins Connaissance

---

### knowledge/\_\_init\_\_.py

**Fichier** : `deepblender/plugins/knowledge/__init__.py` (7 lignes)

#### Exports

```python
__all__ = ["KnowledgeGraphPlugin", "AssetLibraryPlugin", "ObservabilityPlugin"]
```

---

### knowledge/knowledge_graph.py — KnowledgeGraphPlugin

**Fichier** : `deepblender/plugins/knowledge/knowledge_graph.py` (67 lignes)

#### Rôle

Graphe de connaissances de la production : relie les entités (scènes, plans, assets, décisions) dans un fichier JSON persistant.

#### Classe `KnowledgeGraphPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"knowledge-graph"` | Identifiant |
| `description` | `str` | `"Graphe de connaissances de la production (JSON)."` | Description |
| `path` | `Path` | `Path.cwd() / "production" / "kg.json"` | Chemin du fichier JSON |

**Structure du JSON** :
```json
{
  "nodes": {
    "<node_id>": {
      "label": "...",
      "props": {},
      "updated_at": 1234567890.0
    }
  },
  "edges": [
    {"source": "...", "target": "...", "relation": "..."}
  ]
}
```

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` |
| `add_node(node_id, label, props)` | `node_id: str, label: str, props: dict[str, Any] \| None = None` | `None` | Ajoute un nœud avec label et propriétés |
| `add_edge(source, target, relation)` | `source: str, target: str, relation: str` | `None` | Ajoute une arête. Lève `PluginError` si un nœud est inconnu. |
| `query(center, depth)` | `center: str, depth: int = 1` | `list[dict[str, str]]` | Recherche en largeur jusqu'à `depth` niveaux. Retourne `{source, relation, target}`. |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_read()` | Lit le fichier JSON. Retourne `{nodes: {}, edges: []}` en cas d'erreur. |
| `_write(graph)` | Écrit le graphe en JSON indenté (UTF-8) |

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"knowledge-graph"`.
- Utilisé par les agents NOOA pour tracer les dépendances entre scènes, plans et décisions.

---

### knowledge/asset_library.py — AssetLibraryPlugin

**Fichier** : `deepblender/plugins/knowledge/asset_library.py` (81 lignes)

#### Rôle

Catalogue local des assets : enregistrement, recherche et import avec hash de provenance SHA-256.

#### Classe `AssetLibraryPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"asset-library"` | Identifiant |
| `description` | `str` | `"Catalogue local des assets (index JSON)."` | Description |
| `index_path` | `Path` | `Path.cwd() / "asset-library" / "index.json"` | Chemin de l'index |

**Structure d'une entrée d'index** :
```json
{
  "id": "a1b2c3d4e5",
  "type": "mesh",
  "tags": ["character", "hero"],
  "path": "/path/to/asset.blend",
  "hash": "sha256...",
  "registered_at": 1234567890.0
}
```

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` |
| `register(path, asset_type, tags)` | `path: Path, asset_type: str, tags: list[str] \| None = None` | `dict[str, Any]` | Enregistre un asset avec hash SHA-256. Lève `PluginError` si fichier introuvable. |
| `find(query)` | `query: str = ""` | `list[dict[str, Any]]` | Recherche par type, tags ou chemin (case-insensitive). Requête vide = tous. |
| `import_into(asset_id, destination)` | `asset_id: str, destination: Path` | `Path` | Copie l'asset vers la destination. Lève `PluginError` si asset ou source introuvable. |

##### Méthodes privées

| Méthode | Description |
|---|---|
| `_read()` | Lit l'index JSON. Retourne `[]` en cas d'erreur. |
| `_write(entries)` | Écrit l'index JSON indenté (UTF-8) |

#### Connexion au système

- Dans `_BUILTINS` sous la clé `"asset-library"`.
- Les assets enregistrés sont les meshes, textures, matériaux importés dans les scènes Blender.

---

### knowledge/observability.py — ObservabilityPlugin

**Fichier** : `deepblender/plugins/knowledge/observability.py` (194 lignes)

#### Rôle

Tracing des appels LLM via Langfuse (self-hosted) et/ou JSONL local. Enregistre coût, latence, tokens, modèle pour chaque appel.

#### Classe `LLMSpan`

`@dataclass`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `trace_id` | `str` | — | Identifiant de trace |
| `agent` | `str` | — | Nom de l'agent |
| `step` | `str` | — | Étape du pipeline |
| `model` | `str` | — | Modèle LLM utilisé |
| `provider` | `str` | — | Fournisseur (OpenAI, Anthropic, etc.) |
| `input_tokens` | `int` | `0` | Tokens en entrée |
| `output_tokens` | `int` | `0` | Tokens en sortie |
| `latency_ms` | `float` | `0.0` | Latence en millisecondes |
| `cost_usd` | `float` | `0.0` | Coût en USD |
| `success` | `bool` | `True` | Succès de l'appel |
| `cache_hit` | `bool` | `False` | Si le résultat venait du cache |
| `error` | `str` | `""` | Message d'erreur |
| `timestamp` | `float` | `time.time()` | Horodatage Unix |

| Méthode | Retour | Description |
|---|---|---|
| `to_dict()` | `dict[str, Any]` | Sérialisation complète |

#### Classe `ObservabilityPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"observability"` | Identifiant |
| `description` | `str` | `"Observabilite LLM : Langfuse, OpenTelemetry, JSONL."` | Description |
| `_langfuse_client` | `Any` | `None` | Client Langfuse (privé) |
| `_span_file` | `Any` | `None` | Fichier JSONL ouvert (privé) |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | Toujours `True` |
| `trace_llm_call(span)` | `span: LLMSpan` | `None` | Trace un appel LLM (JSONL + Langfuse si configuré) |
| `get_spans(limit)` | `limit: int = 100` | `list[dict[str, Any]]` | Lit les derniers spans depuis le fichier JSONL |
| `get_stats()` | — | `dict[str, Any]` | Statistiques agrégées (voir ci-dessous) |
| `flush()` | — | `None` | Vide les buffers Langfuse |

##### Sortie de `get_stats()`

```python
{
    "total_calls": int,
    "total_cost_usd": float,
    "total_tokens": int,
    "avg_latency_ms": float,
    "success_rate": float,      # 0.0–1.0
    "cache_hit_rate": float,    # 0.0–1.0
    "by_model": dict[str, int], # nombre d'appels par modèle
}
```

##### Initialisation

**Langfuse** :
```python
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")
```

**Fichier JSONL** :
```python
span_path = Path(os.environ.get("DeepBl4nder_DATA_DIR", "data")) / "logs" / "llm_spans.jsonl"
```

#### Connexion au système

- **Non** dans `_BUILTINS` du `PluginRegistry`. Doit être enregistré manuellement.
- Utilisé par l'orchestrateur pour tracer chaque appel LLM effectué par les agents NOOA.
- Les métriques alimentent le dashboard d'observabilité.

---

## Plugins Intégrations

---

### integrations/\_\_init\_\_.py

**Fichier** : `deepblender/plugins/integrations/__init__.py` (5 lignes)

#### Exports

```python
__all__ = ["BillingPlugin"]
```

---

### integrations/billing.py — BillingPlugin

**Fichier** : `deepblender/plugins/integrations/billing.py` (141 lignes)

#### Rôle

Gestion de la facturation via Stripe : abonnements, crédits, plans, sessions de paiement.

#### Classe `BillingPlan`

`@dataclass`

| Propriété | Type | Description |
|---|---|---|
| `name` | `str` | Nom du plan |
| `price_usd` | `float` | Prix mensuel en USD |
| `credits_per_month` | `int` | Crédits mensuels alloués |
| `max_concurrent_renders` | `int` | Rendus simultanés max |
| `max_duration_seconds` | `int` | Durée max par rendu (secondes) |
| `features` | `list[str]` | Fonctionnalités incluses |

#### Constante `BUILTIN_PLANS`

| Clé | Nom | Prix | Credits/mois | Rendus max | Durée max | Features |
|---|---|---|---|---|---|---|
| `free` | Gratuit | $0 | 50 | 1 | 30s | `basic_render` |
| `pro` | Pro | $29 | 500 | 3 | 120s | `basic_render`, `music_gen`, `tts`, `color_grading` |
| `studio` | Studio | $99 | 2000 | 10 | 600s | `basic_render`, `music_gen`, `tts`, `color_grading`, `batch_render`, `priority_queue`, `custom_agents` |

#### Classe `BillingPlugin`

`@dataclass` — Hérite de `Plugin`

| Propriété | Type | Valeur par défaut | Description |
|---|---|---|---|
| `name` | `str` | `"billing"` | Identifiant |
| `description` | `str` | `"Facturation Stripe : abonnements, credits, plans."` | Description |
| `_stripe_client` | `Any` | `None` | Module stripe (privé) |

##### Méthodes

| Méthode | Paramètres | Type retour | Description |
|---|---|---|---|
| `available()` | — | `bool` | `True` si `stripe` configuré et importé |
| `get_plans()` | — | `dict[str, BillingPlan]` | Retourne `BUILTIN_PLANS` |
| `create_checkout_session(user_id, plan_id, success_url, cancel_url)` | `user_id: str, plan_id: str, success_url: str, cancel_url: str` | `str \| None` | Crée une session Stripe Checkout. Retourne l'URL. |
| `check_credits(user_id, plan_id, credits_used)` | `user_id: str, plan_id: str, credits_used: int` | `bool` | Vérifie si les crédits restent suffisants |
| `get_usage(user_id)` | `user_id: str` | `dict[str, Any]` | Retourne l'utilisation actuelle |

##### Sortie de `get_usage()`

```python
{
    "user_id": str,
    "credits_used": int,       # toujours 0 (placeholder)
    "credits_limit": int,      # toujours 50 (placeholder)
    "concurrent_renders": int, # toujours 0
    "renders_this_month": int, # toujours 0
}
```

##### Initialisation Stripe

```python
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
```

#### Connexion au système

- **Non** dans `_BUILTINS` du `PluginRegistry`. Doit être enregistré manuellement.
- Utilisé par le frontend/API pour gérer les abonnements et vérifier les quotas avant exécution de rendus.

---

## Annexe : Constantes et configurations

### `_RATE` par plugin

| Plugin | Valeur | Contexte |
|---|---|---|
| `AudioPlugin` | 44100 Hz | WAV standard |
| `TTSPlugin` | 24000 Hz | TTS Bark/Piper |
| `MusicPlugin` | 44100 Hz | WAV standard |

### Presets intégrés

| Catégorie | Nombre | Exemples |
|---|---|---|
| Export vidéo | 7 | `h264_1080p`, `h264_4k`, `prores_422`, `prores_4444`, `dnxhd`, `webm_vp9`, `gif` |
| Color grading | 7 | `cinematic`, `warm`, `cold`, `vintage`, `noir`, `vivid`, `flat` |
| Plans billing | 3 | `free`, `pro`, `studio` |
| Moods musicaux | 5 | `happy`, `sad`, `epic`, `dark`, `neutral` |
| Phonèmes lipsync | 15 | `sil`, `PP`, `FF`, `TH`, `DD`, `kk`, `CH`, `SS`, `nn`, `RR`, `aa`, `E`, `ih`, `oh`, `ou` |

---

## Annexe : Variables d'environnement

| Variable | Plugin | Default | Description |
|---|---|---|---|
| `BARK_MODEL_PATH` | TTS | `""` | Chemin modèle Bark (HuggingFace) |
| `COSYVOICE_MODEL_PATH` | TTS | `""` | Chemin modèle CosyVoice |
| `TTS_BINARY` | TTS | `""` | Chemin binaire Piper TTS |
| `WHISPER_MODEL_PATH` | LipSync | `""` | Chemin modèle Whisper |
| `RHUBARB_BINARY` | LipSync | `""` | Chemin binaire Rhubarb Lip Sync |
| `ACE_STEP_MODEL_PATH` | Music | `""` | Chemin modèle ACE-Step |
| `MUSICGEN_MODEL_PATH` | Music | `""` | Chemin modèle MusicGen |
| `FFMPEG_EXE` | FFmpeg | `"ffmpeg"` | Chemin binaire FFmpeg |
| `GIT_EXE` | Git | `"git"` | Chemin binaire Git |
| `REDIS_URL` | Cache | `"redis://localhost:6379/0"` | URL connexion Redis |
| `LANGFUSE_SECRET_KEY` | Observability | `""` | Clé secrète Langfuse |
| `LANGFUSE_PUBLIC_KEY` | Observability | `""` | Clé publique Langfuse |
| `LANGFUSE_HOST` | Observability | `"http://localhost:3001"` | Host Langfuse |
| `DeepBl4nder_DATA_DIR` | Observability | `"data"` | Répertoire de données (logs JSONL) |
| `STRIPE_SECRET_KEY` | Billing | `""` | Clé secrète Stripe |

---

## Annexe : Dépendances inter-modules

### Dépendances externes (bridges)

| Plugin | Module bridge | Classe utilisée |
|---|---|---|
| `BlenderPlugin` | `DeepBl4nder.bridges.blender.bridge` | `BlenderBridge` |
| `BlenderPlugin` | `DeepBl4nder.bridge.worker` | `ProcessResult` |
| `BlenderPlugin` | `DeepBl4nder.domain.scene` | `BlenderScript` |
| `FFmpegPlugin` | `DeepBl4nder.bridge.worker` | `WorkerCommand`, `WorkerProcess` |
| `RenderFarmPlugin` | `DeepBl4nder.bridges.blender.scheduler` | `WorkerScheduler` |
| `RenderFarmPlugin` | `DeepBl4nder.bridges.blender.bridge` | `BlenderBridge` |
| `GitPlugin` | `DeepBl4nder.bridge.worker` | `WorkerCommand`, `WorkerProcess` |

### Dépendances inter-plugins

| Plugin | Dépend de | Relation |
|---|---|---|
| `ToolRegistry` | `PluginRegistry` | Utilise pour accéder à `BlenderPlugin`, `AudioPlugin`, `FFmpegPlugin` |
| `ToolRegistry` | `BlenderPlugin` | 5 tools (`inspect_scene`, `load_asset`, `save_blend`, `render`, `inspect_render`) |
| `ToolRegistry` | `AudioPlugin` | 1 tool (`create_audio`) |
| `ToolRegistry` | `FFmpegPlugin` | 2 tools (`compose`, `export`) |
| `RenderFarmPlugin` | `PluginRegistry` | Partagé pour accéder au `BlenderBridge` |
| `RenderFarmPlugin` | `BlenderPlugin` | Utilise `BlenderPlugin.bridge` |
| `PluginRegistry` | `RenderFarmPlugin` | Passe `plugins=self` à l'instanciation |

### Graphe de flux des données

```
Agents NOOA
    │
    ├──→ ToolRegistry.tools() ──→ BlenderPlugin ──→ BlenderBridge ──→ Blender (-b -P)
    │                     ├──→ AudioPlugin ──→ WAV files ──→ FFmpegPlugin.mux()
    │                     └──→ FFmpegPlugin ──→ WorkerProcess ──→ ffmpeg CLI
    │
    ├──→ PluginRegistry.get("tts") ──→ TTSPlugin ──→ Bark/Piper/fallback ──→ WAV
    ├──→ PluginRegistry.get("music") ──→ MusicPlugin ──→ ACE-Step/MusicGen/fallback ──→ WAV
    ├──→ PluginRegistry.get("lipsync") ──→ LipSyncPlugin ──→ Whisper/Rhubarb/RMS ──→ JSON blendshapes
    ├──→ PluginRegistry.get("subtitle") ──→ SubtitlePlugin ──→ SRT files
    ├──→ PluginRegistry.get("storage") ──→ StoragePlugin ──→ filesystem
    ├──→ PluginRegistry.get("git") ──→ GitPlugin ──→ git CLI
    ├──→ PluginRegistry.get("knowledge-graph") ──→ KnowledgeGraphPlugin ──→ JSON graph
    ├──→ PluginRegistry.get("asset-library") ──→ AssetLibraryPlugin ──→ JSON index
    ├──→ PluginRegistry.get("render-farm") ──→ RenderFarmPlugin ──→ WorkerScheduler ──→ N workers
    │
    └──→ (manually registered)
         ├──→ CachePlugin ──→ Redis / in-memory
         ├──→ ObservabilityPlugin ──→ Langfuse / JSONL
         └──→ BillingPlugin ──→ Stripe
```
