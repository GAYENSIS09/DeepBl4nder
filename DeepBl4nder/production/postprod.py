"""PostProductionRunner : etapes de post-production du pipeline.

Extrait de PipelineRunner pour decomposer le runner principal.
Gere : audio, musique, sound design, compositing, review, merge final, localization.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Callable

from DeepBl4nder.domain.media import (
    AudioMaster,
    AudioPlan,
    CompositeSpec,
    LanguagePackage,
    MusicPlan,
    SoundDesignPlan,
)
from DeepBl4nder.domain.scene import RenderOutput, SceneSpec
from DeepBl4nder.production.events import EventLog
from DeepBl4nder.production.plugins import PluginShortcuts
from DeepBl4nder.production.runs import ProductionRun
from DeepBl4nder.artifacts.provenance import ProvenanceGraph
from DeepBl4nder.artifacts.registry import Artifact, ArtifactRegistry

logger = logging.getLogger("DeepBl4nder.production.postprod")


class PostProductionRunner(PluginShortcuts):
    """Gere les etapes de post-production du pipeline."""

    def __init__(
        self,
        *,
        audio: Any,
        music_composer: Any,
        sound_designer: Any,
        localization: Any,
        compositing: Any,
        review: Any,
        workdir: Path,
        artifacts: ArtifactRegistry,
        provenance: ProvenanceGraph,
        production_run: ProductionRun,
        event_log: EventLog,
        plugins: Any,
        event_hook: Callable[[str, dict[str, Any]], None],
        charge: Callable[[str, Artifact | None], None],
        write_json: Callable[[str, Any], Path],
        target_languages: list[str],
        llm_semaphore: asyncio.Semaphore,
        reported_llm_meta: Callable[[Any], dict[str, Any]],
        with_generation_retry: Callable[[str, Callable], Any],
        director_art: str | None = None,
    ) -> None:
        self.audio = audio
        self.music_composer = music_composer
        self.sound_designer = sound_designer
        self.localization = localization
        self.compositing = compositing
        self.review = review
        self.workdir = workdir
        self.artifacts = artifacts
        self.provenance = provenance
        self.production_run = production_run
        self.event_log = event_log
        self.plugins = plugins
        self._emit = event_hook
        self._charge = charge
        self._write_json = write_json
        self.target_languages = target_languages
        self._llm_semaphore = llm_semaphore
        self._reported_llm_meta = reported_llm_meta
        self._with_generation_retry = with_generation_retry
        self._director_art = director_art

    async def run_audio(self, scene: SceneSpec) -> tuple[AudioPlan, AudioMaster]:
        """Execute AudioAgent -> AudioPlugin."""
        self.production_run.start_step("audio")
        self._emit("llm_call", {"step": "audio", "agent": "AudioAgent", "status": "started", "model": getattr(self.audio, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        audio_plan = await self._with_generation_retry(
            "audio", lambda: self.audio.plan_audio(scene)
        )
        elapsed_llm = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "audio", "agent": "AudioAgent", "status": "completed", "elapsed_s": elapsed_llm, **self._reported_llm_meta(self.audio)})

        workdir = self.workdir / "audio"
        workdir.mkdir(parents=True, exist_ok=True)

        ambience_path = workdir / "ambience.wav"
        if self.audio_plugin is not None:
            self.audio_plugin.generate_ambience(
                duration=sum(s.duration for s in scene.shots) or 30.0,
                out_path=ambience_path,
            )
            music_path = workdir / "music.wav"
            self.audio_plugin.generate_tone(frequency=220.0, duration=10.0, out_path=music_path)
        else:
            ambience_path.write_bytes(b"")
            music_path = workdir / "music.wav"
            music_path.write_bytes(b"")

        audio_master = AudioMaster(
            path=str(workdir / "master.wav"),
            duration=sum(s.duration for s in scene.shots) or 30.0,
            channels=1,
            sample_rate=44100,
            language="fr",
        )

        plan_artifact = self.artifacts.register(
            Artifact(type="audio_plan", name="audio", path=self._write_json("audio_plan.json", audio_plan.to_mapping()))
        )
        master_artifact = self.artifacts.register(
            Artifact(type="audio_master", name="master", path=Path(audio_master.path))
        )
        if self._director_art:
            self.provenance.record(self._director_art, plan_artifact.id)
            self.provenance.record(self._director_art, master_artifact.id)

        self._charge("audio", plan_artifact)
        self._charge("audio", master_artifact)
        self.production_run.complete_step("audio")
        return audio_plan, audio_master

    async def run_music(self, scene: SceneSpec) -> MusicPlan | None:
        """Execute MusicComposerAgent -> MusicPlan."""
        if self.music_composer is None:
            return None
        self.production_run.start_step("music")
        self._emit("llm_call", {"step": "music", "agent": "MusicComposerAgent", "status": "started", "model": getattr(self.music_composer, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        music_plan = await self._with_generation_retry(
            "music", lambda: self.music_composer.compose_music(scene)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "music", "agent": "MusicComposerAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.music_composer)})
        path = self._write_json("music_plan.json", music_plan.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="music_plan", name="music", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("music", artifact)
        self.production_run.complete_step("music")
        return music_plan

    async def run_sound_design(self, scene: SceneSpec) -> SoundDesignPlan | None:
        """Execute SoundDesignerAgent -> SoundDesignPlan."""
        if self.sound_designer is None:
            return None
        self.production_run.start_step("sound_design")
        self._emit("llm_call", {"step": "sound_design", "agent": "SoundDesignerAgent", "status": "started", "model": getattr(self.sound_designer, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        sound_plan = await self._with_generation_retry(
            "sound_design", lambda: self.sound_designer.design_sound(scene)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "sound_design", "agent": "SoundDesignerAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.sound_designer)})
        path = self._write_json("sound_design_plan.json", sound_plan.to_mapping())
        artifact = self.artifacts.register(
            Artifact(type="sound_design_plan", name="sound_design", path=path, status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("sound_design", artifact)
        self.production_run.complete_step("sound_design")
        return sound_plan

    async def run_review(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None = None,
        audio_plan: AudioPlan | None = None,
        composite_spec: CompositeSpec | None = None,
    ) -> Any:
        """Execute ReviewAgent -> ReviewReport."""
        if self.review is None:
            return None
        self.production_run.start_step("review")
        self._emit("llm_call", {"step": "review", "agent": "ReviewAgent", "status": "started", "model": getattr(self.review, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        review_report = await self._with_generation_retry(
            "review", lambda: self.review.review_production(scene, render_output, audio_plan, composite_spec)
        )
        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "review", "agent": "ReviewAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.review)})
        artifact = self.artifacts.register(
            Artifact(type="review_report", name="review", path=self.workdir / "review_report.json", status="spec")
        )
        if self._director_art:
            self.provenance.record(self._director_art, artifact.id)
        self._charge("review", artifact)
        self.production_run.complete_step("review")
        return review_report

    async def run_compositing(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None = None,
        audio_plan: AudioPlan | None = None,
    ) -> CompositeSpec:
        """Execute CompositingAgent -> FFmpegPlugin pour fusionner tout."""
        self.production_run.start_step("compositing")
        self._emit("llm_call", {"step": "compositing", "agent": "CompositingAgent", "status": "started", "model": getattr(self.compositing, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        composite_spec = await self._with_generation_retry(
            "compositing", lambda: self.compositing.plan_compositing(scene)
        )
        elapsed_llm = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "compositing", "agent": "CompositingAgent", "status": "completed", "elapsed_s": elapsed_llm, **self._reported_llm_meta(self.compositing)})

        workdir = self.workdir / "compositing"
        workdir.mkdir(parents=True, exist_ok=True)

        spec_artifact = self.artifacts.register(
            Artifact(type="composite_spec", name="compositing", path=self._write_json("composite_spec.json", composite_spec.to_mapping()))
        )
        if self._director_art:
            self.provenance.record(self._director_art, spec_artifact.id)

        if self.ffmpeg_plugin and self.ffmpeg_plugin.available():
            await self.merge_final_output(scene, render_output, audio_plan, workdir)

        self._charge("compositing", spec_artifact)
        self.production_run.complete_step("compositing")
        return composite_spec

    async def merge_final_output(
        self,
        scene: SceneSpec,
        render_output: RenderOutput | None,
        audio_plan: AudioPlan | None,
        workdir: Path,
    ) -> None:
        """Fusionne video + audio + sous-titres en un seul fichier final."""
        if render_output is None:
            return

        video_path = Path(render_output.video_path)
        if not video_path.exists():
            return

        audio_dir = self.workdir / "audio"
        ambience_path = audio_dir / "ambience.wav"
        music_path = audio_dir / "music.wav"

        voice_paths: list[Path] = []
        loc_dir = self.workdir / "localization"
        if loc_dir.exists():
            for lang_dir in loc_dir.iterdir():
                if lang_dir.is_dir():
                    voice_path = lang_dir / "voice.wav"
                    if voice_path.exists():
                        voice_paths.append(voice_path)

        sub_dir = self.workdir / "localization" / "fr"
        srt_path = sub_dir / "subtitles.srt"

        output_path = workdir / f"{scene.environment.description[:30].strip() or 'final'}_v{render_output.version}.mp4"

        inputs = ["-y", "-i", str(video_path)]
        has_audio = False

        if ambience_path.exists():
            inputs.extend(["-i", str(ambience_path)])
            has_audio = True
        if music_path.exists():
            inputs.extend(["-i", str(music_path)])
            has_audio = True
        for voice_path in voice_paths:
            inputs.extend(["-i", str(voice_path)])
            has_audio = True

        if has_audio:
            filter_parts = []
            audio_inputs = []
            input_idx = 1

            if ambience_path.exists():
                filter_parts.append(f"[{input_idx}:a]volume=0.3[ambience];")
                audio_inputs.append("[ambience]")
                input_idx += 1
            if music_path.exists():
                filter_parts.append(f"[{input_idx}:a]volume=0.5[music];")
                audio_inputs.append("[music]")
                input_idx += 1
            for i, voice_path in enumerate(voice_paths):
                filter_parts.append(f"[{input_idx}:a]volume=1.0[voice{i}];")
                audio_inputs.append(f"[voice{i}]")
                input_idx += 1

            if len(audio_inputs) > 1:
                mix = "".join(audio_inputs) + f"amix=inputs={len(audio_inputs)}:duration=first[aout]"
                filter_parts.append(mix)
                filter_complex = "".join(filter_parts)
                outputs = ["-map", "0:v", "-map", "[aout]"]
                outputs.extend(["-filter_complex", filter_complex])
            elif audio_inputs:
                outputs = ["-map", "0:v", "-map", audio_inputs[0]]
            else:
                outputs = []
        else:
            outputs = []

        if srt_path.exists():
            if has_audio and 'filter_complex' in locals():
                filter_complex += f"[0:v]subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF&,Outline=1,Shadow=1'[vout];"
                outputs = ["-map", "[vout]", "-map", "[aout]"]
                outputs.extend(["-filter_complex", filter_complex])
            else:
                outputs = ["-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF&,Outline=1,Shadow=1'"]

        cmd = inputs + outputs + [
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "medium",
        ]
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.append(str(output_path))

        try:
            self.ffmpeg_plugin._run(*cmd)

            artifact = self.artifacts.register(
                Artifact(type="final_output", name="final", path=output_path)
            )
            if self._director_art:
                self.provenance.record(self._director_art, artifact.id)

            if self.storage_plugin and self.storage_plugin.available():
                try:
                    self.storage_plugin.store(output_path, f"final/{scene.environment.description[:30]}_v{render_output.version}.mp4")
                except Exception:
                    pass

            if self.knowledge_graph_plugin and self.knowledge_graph_plugin.available():
                try:
                    self.knowledge_graph_plugin.add_node(
                        f"output_{artifact.id}",
                        "FinalOutput",
                        {"scene": scene.environment.description[:30], "version": render_output.version},
                    )
                except Exception:
                    pass

        except Exception as e:
            self.event_log.append("merge_failed", {"error": str(e)})

    def target_languages_for(self, scene: SceneSpec) -> list[str]:
        """Langues cibles de localisation."""
        targets: list[str] = list(self.target_languages)
        if targets:
            return targets
        for char in scene.characters:
            for lang in char.spoken_languages():
                if lang not in targets:
                    targets.append(lang)
        for lang in self.localization.default_languages():
            if lang not in targets:
                targets.append(lang)
        return targets

    async def run_localization(self, scene: SceneSpec) -> list[LanguagePackage]:
        """Execute LocalizationAgent -> SubtitlePlugin/TTSPlugin pour chaque langue."""
        self.production_run.start_step("localization")
        self._emit("llm_call", {"step": "localization", "agent": "LocalizationAgent", "status": "started", "model": getattr(self.localization, '_get_model_id', lambda: 'unknown')()})
        t0 = time.time()
        targets = self.target_languages_for(scene)

        async def _produce_language(lang: str) -> LanguagePackage | None:
            async with self._llm_semaphore:
                package = await self.localization.plan_localization(scene, lang, languages=targets)
            if package is None:
                return None

            workdir = self.workdir / "localization" / lang
            workdir.mkdir(parents=True, exist_ok=True)

            if self.subtitle_plugin and package.subtitles_path:
                from DeepBl4nder.plugins.media.subtitle import SubtitleEntry
                subtitle_entries = []
                for i, dialogue in enumerate(package.dialogues):
                    if isinstance(dialogue, dict):
                        start = dialogue.get("start", i * 3.0)
                        end = dialogue.get("end", (i + 1) * 3.0)
                        text = dialogue.get("text", "")
                        character = dialogue.get("character", "")
                        subtitle_entries.append(SubtitleEntry(
                            index=i + 1,
                            start=start,
                            end=end,
                            text=f"{character}: {text}" if character else text
                        ))
                if subtitle_entries:
                    self.subtitle_plugin.generate(subtitle_entries, Path(package.subtitles_path))

            if self.tts_plugin and package.voice_path and self.tts_plugin.available():
                full_text = " ".join(
                    d.get("text", "") if isinstance(d, dict) else str(d)
                    for d in package.dialogues
                )
                if full_text.strip():
                    self.tts_plugin.generate(full_text, Path(package.voice_path), lang=lang)

            package_artifact = self.artifacts.register(
                Artifact(type="language_package", name=lang, path=self._write_json(f"language_package_{lang}.json", package.to_mapping()))
            )
            if self._director_art:
                self.provenance.record(self._director_art, package_artifact.id)

            self._charge("localization", package_artifact)
            return package

        results = await asyncio.gather(*(_produce_language(lang) for lang in targets))
        language_packages = [package for package in results if package is not None]

        elapsed = round(time.time() - t0, 2)
        self._emit("llm_call", {"step": "localization", "agent": "LocalizationAgent", "status": "completed", "elapsed_s": elapsed, **self._reported_llm_meta(self.localization), "languages": targets})
        self.production_run.complete_step("localization")
        return language_packages
