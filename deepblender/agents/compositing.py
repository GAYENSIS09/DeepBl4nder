"""CompositingAgent : planifie les passes et l'étalonnage post-rendu (NOOA Agent).

Produit un `CompositeSpec` typé à partir de la `SceneSpec`. L'exécution des
passes et le grade se font dans un worker dédié (FFmpegPlugin), jamais dans l'agent.

Utilise le skill : compositing.
"""

from __future__ import annotations

from typing import Any

from nooa import CodeActLiteStrategy, strategy

from deepblender.agents.base import BaseAgent, DefaultsMixin
from deepblender.domain.media import CompositeSpec
from deepblender.domain.scene import SceneSpec
from deepblender.skills.registry import SkillRegistry


class CompositingAgent(BaseAgent, DefaultsMixin):
    """You are a compositing agent.

    You plan the post-render pipeline for a typed scene specification: render
    passes, color grade and effects.

    ## Skills available (progressive disclosure)
    - compositing: render passes, AOVs, color grading, LUTs, effects, output formats

    ## Rules
    - Start from the render passes the scene actually needs.
    - Choose an output format compatible with the downstream pipeline.
    - Produce a typed CompositeSpec, never raw compositor scripts.
    - Output MUST be a valid CompositeSpec (validated via output_model).
    """

    def __init__(self, *args: Any, skill_registry: SkillRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, skill_registry=skill_registry, **kwargs)

    @strategy(CodeActLiteStrategy())  # type: ignore[arg-type]
    async def plan_compositing(self, spec: SceneSpec) -> CompositeSpec:  # type: ignore[return]
        """Turn the scene spec into a post-render compositing plan.

        Steps:
        1. Load core skill summaries
        2. Analyze scene: lighting complexity, mood, shot count
        3. Load compositing skill
        4. Generate CompositeSpec with:
           - passes: list of required AOVs (diffuse, direct, indirect, shadow, mist, crypto, etc.)
           - grade: "balanced" | "filmic" | "anime" | "toon" | "high-contrast" | "custom"
           - effects: ["bloom", "glare", "vignette", "film-grain", "chromatic-aberration"]
           - output_format: "exr" | "png" | "tiff" (multi-layer for EXR)
        """
        self._load_core_skills()
        self._load_skill("compositing")

        ...
