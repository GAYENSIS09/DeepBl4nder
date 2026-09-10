"""Pipeline tracker widget - progressive production stage board.

Renders the film pipeline the way a post-production supervisor reads a dailies
board: stages appear only as they are actually reached (never a preloaded list
of agents), each with a live state glyph. Fed by ``step_started`` /
``step_completed`` / ``step_failed`` / ``revision_requested`` events from the
console screen.
"""

from __future__ import annotations

from collections import OrderedDict

from textual.widgets import Static

from DeepBl4nder.tui import theme

# Ordered pipeline (front-to-end), mirroring production.runner._STEPS + _POST_STEPS.
_STEP_ORDER = (
    "story", "storyboard", "director", "character_design", "environment",
    "blender", "qa", "animation", "render",
    "music", "sound_design", "audio", "localization", "compositing", "review",
)

_STEP_LABELS = {
    "story": "Story",
    "storyboard": "Storyboard",
    "director": "Director",
    "character_design": "Character Design",
    "environment": "Environment",
    "blender": "Blender",
    "qa": "QA",
    "animation": "Animation",
    "render": "Render",
    "music": "Music",
    "sound_design": "Sound Design",
    "audio": "Audio",
    "localization": "Localization",
    "compositing": "Compositing",
    "review": "Review",
}

_STEP_COLORS = {
    "story": theme.ACTOR_COLORS["story"],
    "storyboard": theme.ACTOR_COLORS["storyboard"],
    "director": theme.ACTOR_COLORS["director"],
    "character_design": theme.ACTOR_COLORS["character_designer"],
    "environment": theme.ACTOR_COLORS["environment_artist"],
    "blender": theme.ACTOR_COLORS["blender"],
    "qa": theme.ACTOR_COLORS["qa"],
    "animation": theme.ACTOR_COLORS["animator"],
    "render": theme.INFO,
    "music": theme.ACTOR_COLORS["music_composer"],
    "sound_design": theme.ACTOR_COLORS["sound_designer"],
    "audio": theme.ACTOR_COLORS["audio"],
    "localization": theme.ACTOR_COLORS["localization"],
    "compositing": theme.ACTOR_COLORS["compositing"],
    "review": theme.ACTOR_COLORS["review"],
}

_GLYPHS: dict[str, tuple[str, str]] = {
    "running": ("●", theme.WARNING),
    "done": ("✓", theme.SUCCESS),
    "failed": ("✗", theme.ERROR),
    "revising": ("↻", theme.WARNING),
}


class PipelineTracker(Static):
    """Progressive stage tracker: only reached stages are drawn.

    ``Static`` subclass: the tracker renders its own markup text directly
    (no child widget), so there is never a "container whose render() is
    None" path during scrolling - it is always a leaf with real content.
    """

    def __init__(self, *, id: str = "pipeline-tracker") -> None:
        super().__init__(
            "Idle - awaiting a run",
            id=id,
            markup=True,
        )
        self._states: OrderedDict[str, str] = OrderedDict()

    def reset(self) -> None:
        self._states.clear()
        self.update("Idle - awaiting a run")

    def on_step(self, kind: str, step: str | None) -> None:
        if not step:
            return
        state = {
            "step_started": "running",
            "step_completed": "done",
            "step_failed": "failed",
            "revision_requested": "revising",
            "revising": "revising",
        }.get(kind)
        if state is None:
            return
        self._states[step] = state
        self._refresh()

    def _refresh(self) -> None:
        if not self._states:
            self.update("Idle - awaiting a run")
            return
        lines = []
        for step in reversed(_STEP_ORDER):
            if step not in self._states:
                continue
            glyph, color = _GLYPHS.get(self._states[step], ("…", theme.TEXT_MUTED))
            label = _STEP_LABELS.get(step, step)
            step_color = _STEP_COLORS.get(step, theme.TEXT_MUTED)
            lines.append(f"[{color}]{glyph}[/] [{step_color}]{label}[/]")
        self.update("\n".join(lines))