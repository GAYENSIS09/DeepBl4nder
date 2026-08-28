"""Patch application utilities for structured SceneSpec modifications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from DeepBl4nder.domain.scene import SceneSpec


PathPart = str | int


@dataclass
class Patch:
    """A structured patch targeting a specific field in a SceneSpec."""

    target: str  # JSON pointer style: "shots[0].camera.position[1]"
    old_value: Any | None = None
    new_value: Any = None
    rationale: str = ""
    author: str = ""
    applied: bool = False
    applied_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "rationale": self.rationale,
            "author": self.author,
            "applied": self.applied,
            "applied_at": self.applied_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Patch":
        return cls(
            target=data["target"],
            old_value=data.get("old_value"),
            new_value=data["new_value"],
            rationale=data.get("rationale", ""),
            author=data.get("author", ""),
            applied=data.get("applied", False),
            applied_at=data.get("applied_at"),
        )


def parse_path(path: str) -> list[PathPart]:
    """Parse a JSON-pointer-like path into keys/indices.
    
    Examples:
        "shots[0].camera.position[1]" -> ["shots", 0, "camera", "position", 1]
        "render.resolution" -> ["render", "resolution"]
        "environment.rain" -> ["environment", "rain"]
    """
    # Split on dots and bracket notation
    parts: list[PathPart] = []
    for part in re.split(r"\.|\[", path):
        part = part.rstrip("]")
        if part.isdigit():
            parts.append(int(part))
        elif part:
            parts.append(part)
    return parts


def get_value(obj: Any, path_parts: list[PathPart]) -> Any:
    """Get a value from a nested dict/list using path parts."""
    current = obj
    for part in path_parts:
        if isinstance(current, dict):
            current = current.get(part)  # type: ignore[arg-type]
        elif isinstance(current, list) and isinstance(part, int):
            if 0 <= part < len(current):
                current = current[part]
            else:
                raise IndexError(f"List index {part} out of range")
        else:
            return None
        if current is None:
            return None
    return current


def set_value(obj: Any, path_parts: list[PathPart], value: Any) -> None:
    """Set a value in a nested dict/list using path parts."""
    current = obj
    for i, part in enumerate(path_parts[:-1]):
        if isinstance(current, dict):
            if part not in current:
                # Determine if next part is an index (list) or key (dict)
                next_part = path_parts[i + 1]
                current[part] = [] if isinstance(next_part, int) else {}
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int):
            # Extend list if needed
            while len(current) <= part:
                next_part = path_parts[i + 1]
                current.append([] if isinstance(next_part, int) else {})
            current = current[part]
        else:
            raise ValueError(f"Cannot navigate into {type(current)} at path {path_parts[:i+1]}")
    
    # Set final value
    final_part = path_parts[-1]
    if isinstance(current, dict):
        current[final_part] = value
    elif isinstance(current, list) and isinstance(final_part, int):
        while len(current) <= final_part:
            current.append(None)
        current[final_part] = value
    else:
        raise ValueError(f"Cannot set value on {type(current)}")


def apply_patch(scene_spec: SceneSpec, patch: Patch) -> SceneSpec:
    """Apply a patch to a SceneSpec, returning a new modified SceneSpec."""
    # Convert to full dict
    full_dict = scene_spec.to_full_dict()
    
    # Parse path
    path_parts = parse_path(patch.target)
    
    # Verify old_value matches (optimistic locking)
    if patch.old_value is not None:
        current_value = get_value(full_dict, path_parts)
        if current_value != patch.old_value:
            raise ValueError(
                f"Old value mismatch at {patch.target}: "
                f"expected {patch.old_value}, got {current_value}"
            )
    
    # Apply patch
    set_value(full_dict, path_parts, patch.new_value)
    
    # Reconstruct SceneSpec
    return SceneSpec.from_full_dict(full_dict)


def apply_patches(scene_spec: SceneSpec, patches: list[Patch]) -> SceneSpec:
    """Apply multiple patches in order."""
    result = scene_spec
    for patch in patches:
        result = apply_patch(result, patch)
    return result


def patch_to_revision_instruction(patch: Patch) -> str:
    """Convert a patch to a human-readable revision instruction for the BlenderAgent."""
    return (
        f"### Patch appliqué\n"
        f"Cible : {patch.target}\n"
        f"Ancienne valeur : {patch.old_value}\n"
        f"Nouvelle valeur : {patch.new_value}\n"
        f"Raison : {patch.rationale}\n"
        f"\n"
        f"Régénère uniquement le script Blender affecté par ce changement. "
        f"Ne modifie pas les autres plans ni la structure globale."
    )