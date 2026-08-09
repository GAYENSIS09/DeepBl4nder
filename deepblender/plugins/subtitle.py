"""SubtitlePlugin : génération et parsing de sous-titres (SRT)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from deepblender.plugins.base import Plugin, PluginError

_BLOCK = re.compile(r"(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\n|\Z)", re.S)


@dataclass(frozen=True)
class SubtitleEntry:
    """Une piste de sous-titre synchronisée (secondes)."""

    index: int
    start: float
    end: float
    text: str


@dataclass
class SubtitlePlugin(Plugin):
    """Frontière d'intégration des sous-titres (formats standards)."""

    name: str = "subtitle"
    description: str = "Génération et parsing de sous-titres (SRT / VTT)."

    def available(self) -> bool:
        return True

    def generate(self, entries: list[SubtitleEntry], path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        blocks = []
        for entry in entries:
            blocks.append(f"{entry.index}\n{_fmt(entry.start)} --> {_fmt(entry.end)}\n{entry.text}\n")
        path.write_text("\n".join(blocks), encoding="utf-8")
        return path

    def parse(self, path: Path) -> list[SubtitleEntry]:
        if not path.is_file():
            raise PluginError(f"subtitle file not found: {path}")
        entries: list[SubtitleEntry] = []
        for index, start, end, text in _BLOCK.findall(path.read_text(encoding="utf-8")):
            entries.append(
                SubtitleEntry(index=int(index), start=_parse_ts(start), end=_parse_ts(end), text=text.strip())
            )
        return entries


def _fmt(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_ts(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
