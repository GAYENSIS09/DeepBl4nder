"""Fallbacks déterministes pour les étapes Storyboard et Blender.

Ces fonctions produisent des sorties structurellement valides quand les
générations LLM échouent deux fois de suite. Elles n'utilisent que des
types du domaine (pas de dépendance au runner).
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

from DeepBl4nder.domain.scene import BlenderScript, SceneSpec
from DeepBl4nder.domain.narrative import StorySpec, StoryboardShot, StoryboardSpec

logger = logging.getLogger("DeepBl4nder.pipeline")

_SHOT_ANGLE_CYCLE = ("wide", "medium", "closeup")
_MAX_SYNTH_SHOTS = 12


def synthesize_storyboard(story_spec: StorySpec) -> StoryboardSpec:
    """Filet ultime du storyboard : un plan par beat de l'histoire.

    Déclenché après l'échec de DEUX générations sur l'invariant « shots
    non vide » (modèle de secours récalcitrant). Transformation
    mécanique du contenu EXISTANT (beats) — aucune invention narrative.
    Qualité plate mais structurellement valide ; le repli est tracé en
    WARNING et via les événements pour revue humaine.
    """
    shots: list[StoryboardShot] = []
    for act in getattr(story_spec, "acts", None) or []:
        beats = getattr(act, "beats", None) or []
        for beat in beats:
            description = (
                beat.get("description", "")
                if isinstance(beat, dict)
                else getattr(beat, "description", "")
            ).strip()
            if not description:
                continue
            raw_duration = (
                beat.get("duration_estimate", 5.0)
                if isinstance(beat, dict)
                else getattr(beat, "duration_estimate", 5.0)
            )
            try:
                duration = float(raw_duration)
            except (TypeError, ValueError):
                duration = 5.0
            i = len(shots)
            shots.append(
                StoryboardShot(
                    index=i,
                    description=description,
                    duration=min(max(duration if duration > 0 else 5.0, 2.0), 12.0),
                    camera_angle=_SHOT_ANGLE_CYCLE[i % len(_SHOT_ANGLE_CYCLE)],
                    characters=list(
                        beat.get("characters", [])
                        if isinstance(beat, dict)
                        else getattr(beat, "characters", [])
                        or []
                    ),
                )
            )
            if len(shots) >= _MAX_SYNTH_SHOTS:
                break
        if len(shots) >= _MAX_SYNTH_SHOTS:
            break

    if not shots:
        # Histoire elle-même vide (modèle faible) : plan d'exposition unique.
        seed = (story_spec.synopsis or story_spec.logline or "Scène d'exposition").strip()
        first_sentence = re.split(r"(?<=[.!?])\s+|\n+", seed, maxsplit=1)[0].strip()
        shots.append(
            StoryboardShot(
                index=0,
                description=first_sentence[:200] or "Plan d'exposition",
                duration=5.0,
                camera_angle="wide",
            )
        )

    spec = StoryboardSpec(
        shots=shots,
        total_duration=sum(s.duration for s in shots),
    )
    logger.warning(
        "étape storyboard : 2 générations invalides → storyboard SYNTHÉTISÉ "
        "déterministement depuis les beats (%d plans). Qualité dégradée, "
        "revue humaine recommandée.",
        len(shots),
    )
    return spec


def synthesize_blender_script(scene: SceneSpec, workdir: Path) -> BlenderScript:
    """Filet ultime de l'étape blender : script bpy déterministe.

    Déclenché après l'échec de DEUX générations (log 22:49 : le modèle
    de secours recopie l'enveloppe d'appel au lieu du résultat). Scène
    minimale mais réelle — sol, éclairage d'ambiance selon ``lighting_mood``,
    caméra animée sur la durée totale des plans, repères pour les
    personnages, volumétrie si pluie — construite uniquement depuis les
    champs EXISTANTS de la SceneSpec. Qualité plate ; tracé en WARNING
    et via les événements pour revue humaine.
    """
    env = scene.environment
    render = scene.render
    shots = scene.shots or []
    fps = max(int(render.fps) or 24, 1)
    res_x, res_y = (int(render.resolution[0]), int(render.resolution[1]))
    total_frames = sum(s.frame_count() for s in shots) or 5 * fps
    # Sortie ABSOLUE dans le dossier scanné par _run_render (log 00:45 :
    # un filepath relatif '//' atterrit hors du workdir de rendu).
    render_dir = workdir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = str((render_dir / "render_synthetisee_").resolve()).replace("\\", "/")

    mood = str(env.lighting_mood or "").strip().lower()
    mood_world_color = {
        "sombre": (0.008, 0.010, 0.016),
        "dark": (0.008, 0.010, 0.016),
        "neutral": (0.050, 0.050, 0.055),
        "jour": (0.350, 0.380, 0.450),
        "day": (0.350, 0.380, 0.450),
    }.get(mood, (0.050, 0.050, 0.055))

    characters = [c.name for c in scene.characters if getattr(c, "name", "")]

    lines: list[str] = [
        "import math",
        "",
        "import bpy",
        "",
        "# Script SYNTHÉTISÉ déterministement par DeepBl4nder (fallback :",
        "# deux générations LLM invalides). Qualité dégradée, revue humaine",
        "# recommandée avant tout rendu définitif.",
        "bpy.ops.wm.read_factory_settings(use_empty=True)",
        "scene = bpy.context.scene",
        f"scene.render.resolution_x = {res_x}",
        f"scene.render.resolution_y = {res_y}",
        f"scene.render.fps = {fps}",
        "scene.frame_start = 0",
        "scene.frame_end = " + str(total_frames),
        "",
        "# --- Sol ---",
        "bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))",
        "ground = bpy.context.active_object",
        "ground.name = 'SynthGround'",
        "",
        "# --- Éclairage ---",
        "world = bpy.data.worlds.new('SynthWorld')",
        "scene.world = world",
        "world.use_nodes = True",
        "bg = world.node_tree.nodes['Background']",
        "bg.inputs[0].default_value = "
        f"({mood_world_color[0]}, {mood_world_color[1]}, {mood_world_color[2]}, 1.0)",
        "bg.inputs[1].default_value = 1.0",
        "bpy.ops.object.light_add(type='SUN', location=(6.0, -4.0, 12.0))",
        "sun = bpy.context.active_object",
        "sun.name = 'SynthSun'",
        "sun.data.energy = 2.0",
        "bpy.ops.object.light_add(type='AREA', location=(0.0, -6.0, 4.0))",
        "key_light = bpy.context.active_object",
        "key_light.name = 'SynthKeyLight'",
        "key_light.data.energy = 400.0",
        "key_light.rotation_euler = (0.9, 0.0, 0.0)",
        "",
    ]

    if env.rain:
        lines += [
            "# --- Volumétrie pluie/brume ---",
            "volume = world.node_tree.nodes.new('ShaderNodeVolumeScatter')",
            "volume.inputs['Density'].default_value = 0.08",
            "world.node_tree.links.new(",
            "    volume.outputs[0], world.node_tree.nodes['World Output'].inputs['Volume'])",
            "",
        ]

    for i, name in enumerate(characters[:8]):
        angle = 2.0 * math.pi * i / max(len(characters[:8]), 1)
        x = round(2.5 * math.cos(angle), 3)
        y = round(2.5 * math.sin(angle), 3)
        safe = re.sub(r"[^A-Za-z0-9_]", "_", name)[:24] or f"Perso{i}"
        lines += [
            f"# --- Repère personnage : {name} ---",
            f"bpy.ops.mesh.primitive_cube_add(size=1.7, location=({x}, {y}, 0.85))",
            f"bpy.context.active_object.name = 'Marker_{safe}'",
            "",
        ]

    lines += [
        "# --- Caméra animée sur les plans ---",
        "bpy.ops.object.camera_add(location=(0.0, -8.0, 2.0))",
        "camera = bpy.context.active_object",
        "camera.name = 'SynthCamera'",
        "scene.camera = camera",
        "camera.data.lens = 35.0",
        f"segments = {max(len(shots), 1)}",
        "for i in range(segments):",
        "    t0 = i / segments",
        "    t1 = (i + 1) / segments",
        "    f0 = int(round(t0 * scene.frame_end))",
        "    f1 = int(round(t1 * scene.frame_end))",
        "    angle = math.radians(30.0 + 120.0 * t0)",
        "    radius = 9.0 - 3.0 * t0",
        "    camera.location = (radius * math.sin(angle), -radius * math.cos(angle), 2.0 + 1.2 * t0)",
        "    camera.rotation_euler = (math.radians(82.0), 0.0, angle)",
        "    if i == segments - 1:",
        "        camera.keyframe_insert(data_path='location', frame=f1)",
        "        camera.keyframe_insert(data_path='rotation_euler', frame=f1)",
        "    else:",
        "        camera.keyframe_insert(data_path='location', frame=max(f1 - 1, f0))",
        "        camera.keyframe_insert(data_path='rotation_euler', frame=max(f1 - 1, f0))",
        "",
        "# --- Sortie : moteur rapide (nom variable selon la version),",
        "# repli Cycles échantillonné bas ---",
        "for _engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):",
        "    try:",
        "        scene.render.engine = _engine",
        "        break",
        "    except Exception:",
        "        continue",
        "else:",
        "    scene.render.engine = 'CYCLES'",
        "    try:",
        "        scene.cycles.samples = 32",
        "    except Exception:",
        "        pass",
        "scene.render.image_settings.file_format = 'FFMPEG'",
        "scene.render.ffmpeg.format = 'MPEG4'",
        "scene.render.ffmpeg.codec = 'H264'",
        f"scene.render.filepath = r'{output_prefix}'",
        "# Rendu EFFECTIF de l'animation — sans cet appel, aucun média",
        "# n'est produit et l'étape render échoue (log 00:45).",
        "bpy.ops.render.render(animation=True)",
    ]
    code = "\n".join(lines) + "\n"

    slug_source = (scene.brief or env.description or "scene").strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug_source).strip("_").lower()[:32]
    scene_name = f"scene_synthetisee_{slug or 'sans_titre'}"

    logger.warning(
        "étape blender : 2 générations invalides → script bpy SYNTHÉTISÉ "
        "déterministement depuis la SceneSpec (%d caractères). Qualité "
        "dégradée, revue humaine recommandée.",
        len(code),
    )
    return BlenderScript(code=code, scene_name=scene_name)
