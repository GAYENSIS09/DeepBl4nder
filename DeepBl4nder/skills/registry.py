"""Registry de skills : découverte, chargement et progressive disclosure.

Le mécanisme est celui de NOOA (TextSkill lit SKILL.md avec frontmatter) ;
DeepBl4nder fournit le contenu métier (Roadmap C §9-10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from nooa import TextSkill

_FRONTMATTER_DESCRIPTION = re.compile(r"(?m)^description:\s*(.+)$")


@dataclass(frozen=True)
class SkillInfo:
    """Métadonnée d'un skill, injectable dans le contexte à bas coût."""

    name: str
    description: str
    path: Path

    def to_summary(self) -> str:
        return f"{self.name}: {self.description}"


class SkillRegistry:
    """Découvre les skills d'un répertoire `skills/<name>/SKILL.md`."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _default_skills_root()

    def discover(self) -> list[SkillInfo]:
        """Liste les skills disponibles (progressive disclosure, niveau 1)."""
        if not self.root.is_dir():
            return []
        infos: list[SkillInfo] = []
        for skill_dir in sorted(self.root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            infos.append(SkillInfo(name=skill_dir.name, description=_read_description(skill_md), path=skill_dir))
        return infos

    def resolve(self, name: str) -> TextSkill:
        """Charge le skill complet (progressive disclosure, niveau final)."""
        path = self.root / name
        if not (path / "SKILL.md").is_file():
            raise KeyError(f"skill not found: {name}")
        return TextSkill(path=path, id=name)

    def summaries(self) -> list[str]:
        return [info.to_summary() for info in self.discover()]


# Module-level default registry for easy sharing across agents
_default_registry: SkillRegistry | None = None


def get_default_registry() -> SkillRegistry:
    """Retourne le registre de skills par défaut (singleton partagé)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
    return _default_registry


def set_default_registry(registry: SkillRegistry) -> None:
    """Remplace le registre par défaut (utile pour tests)."""
    global _default_registry
    _default_registry = registry


def _read_description(skill_md: Path) -> str:
    match = _FRONTMATTER_DESCRIPTION.search(skill_md.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else skill_md.parent.name


def _default_skills_root() -> Path:
    return Path(__file__).resolve().parent
