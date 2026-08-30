"""Artifact library screen - browse productions and their generated files.

Un clic sur un artefact ouvre directement sa preview (JSON colorisé, texte
ou carte media) sans bouton « Open » dédié. Les formats binaires (vidéos,
images, audio, modèles 3D) restent accessibles via « External » (application
par défaut) et « Reveal in folder ».
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Label, Static

from DeepBl4nder.tui import theme
from DeepBl4nder.tui.screens.base import BaseScreen

_TEXT_EXTS = {".json", ".md", ".txt", ".py", ".toml", ".yml", ".yaml", ".log", ".srt", ".vtt", ".csv", ".ini", ".cfg"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tga", ".bmp", ".exr", ".hdr"}
_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".ts"}
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a"}
_MODEL_EXTS = {".blend", ".glb", ".gltf", ".fbx", ".obj", ".stl"}
_MEDIA_EXTS = _IMAGE_EXTS | _VIDEO_EXTS | _AUDIO_EXTS | _MODEL_EXTS

_JSON_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\b(?:true|false|null)\b')


class LibraryScreen(BaseScreen):
    """Full-screen secondary view: productions on the left, artifacts on the right."""

    BINDINGS = [
        Binding("escape", "back", "Back to console", priority=True),
    ]

    def __init__(self, api, *, name: str = "library"):
        super().__init__(api, name=name)
        self.title = "Artifact Library"
        self._current_production: str | None = None
        self._artifacts: list = []

    def action_back(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Horizontal(id="library-root"):
            with Vertical(classes="tree-pane", id="pane-productions"):
                yield Label("Productions", classes="section-title")
                yield DataTable(id="productions-table", classes="artifact-tree")
                yield Button("Refresh", id="btn-refresh-productions", variant="default")
            with Vertical(classes="detail-pane", id="pane-artifacts"):
                yield Label("Artifacts", classes="section-title")
                yield DataTable(id="artifacts-table", classes="artifact-tree")
                with Horizontal(classes="artifact-actions"):
                    yield Button("External", id="btn-external-artifact", variant="default", disabled=True)
                    yield Button("Copy path", id="btn-copy-path", variant="default", disabled=True)
                    yield Button("Reveal in folder", id="btn-reveal", variant="default", disabled=True)
                with VerticalScroll(id="artifact-preview-wrap"):
                    yield Static(id="artifact-preview", markup=False)

    def on_mount(self) -> None:
        current = self.api.current_production()
        if current is not None and current.status in ("running", "revising"):
            self._current_production = current.id

        prod_table = self.query_one("#productions-table", DataTable)
        prod_table.add_columns("Name", "Status", "Progress", "Checkpoints")
        prod_table.cursor_type = "row"
        prod_table.zebra_stripes = True

        art_table = self.query_one("#artifacts-table", DataTable)
        art_table.add_columns("Name", "Type", "Size")
        art_table.cursor_type = "row"
        art_table.zebra_stripes = True

        self.run_worker(self._load_productions, exclusive=True)

    async def _load_productions(self) -> None:
        try:
            productions = self.api.list_productions()
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to load productions: {exc}", severity="error")
            return
        table = self.query_one("#productions-table", DataTable)
        table.clear()
        for prod in productions:
            checkpoint = f"{len(prod.checkpoint_steps)} ckpt" if prod.resumable else "-"
            table.add_row(
                prod.name,
                prod.status,
                f"{prod.progress * 100:.0f}%",
                checkpoint,
                key=prod.id,
            )
        if self._current_production is None and productions:
            self._current_production = productions[0].id
            table.move_cursor(row=0)
            await self._load_artifacts()

    async def _load_artifacts(self) -> None:
        if not self._current_production:
            return
        try:
            artifacts = self.api.list_artifacts(self._current_production)
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to load artifacts: {exc}", severity="error")
            return
        self._artifacts = artifacts
        table = self.query_one("#artifacts-table", DataTable)
        table.clear()
        for art in artifacts:
            table.add_row(art.name, art.type, self._format_size(art.size), key=str(art.path))
        self._update_artifact_buttons()

    def _update_artifact_buttons(self) -> None:
        table = self.query_one("#artifacts-table", DataTable)
        has_selection = table.cursor_row >= 0
        for button_id in (
            "btn-external-artifact",
            "btn-copy-path",
            "btn-reveal",
        ):
            self.query_one(f"#{button_id}", Button).disabled = not has_selection

    @on(DataTable.RowSelected, "#productions-table")
    def on_production_selected(self, event: DataTable.RowSelected) -> None:
        self._current_production = str(event.row_key.value)
        self.run_worker(self._load_artifacts, exclusive=True)

    @on(DataTable.RowSelected, "#artifacts-table")
    def on_artifact_selected(self) -> None:
        self._update_artifact_buttons()
        self.on_open()

    def _selected_artifact_path(self) -> str | None:
        if not self._current_production:
            return None
        table = self.query_one("#artifacts-table", DataTable)
        if table.cursor_row < 0:
            return None
        art = self._artifacts[table.cursor_row]
        return str(art.path)

    @on(Button.Pressed, "#btn-refresh-productions")
    async def on_refresh_productions(self) -> None:
        await self._load_productions()

    def on_open(self) -> None:
        path = self._selected_artifact_path()
        if not path:
            return
        preview = self.query_one("#artifact-preview", Static)
        if Path(path).name == "qa_report.json":
            report = self.api.get_qa_report(self._current_production or "")
            preview.update(self._render_qa_report(report) if report else Text(f"qa_report.json missing or unreadable — {path}", style=theme.ERROR))
            return
        try:
            data = self.api.download_artifact(self._current_production or "", path)
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to open: {exc}", severity="error")
            return
        preview.update(self._render_preview(path, data))

    def _render_qa_report(self, report: dict) -> Text:
        text = Text()
        text.append(" QA report ", style=theme.SUCCESS + " bold" if report.get("passed") else theme.ERROR + " bold")
        text.append(f" — score {report.get('score', 0.0):.1f}/100\n", style=theme.TEXT_DIM)
        issues = report.get("issues", [])
        if issues:
            text.append(f"issues ({len(issues)}):\n", style=theme.TEXT)
            for issue in issues[:8]:
                kind = issue.get("kind", "technical") if isinstance(issue, dict) else "technical"
                message = issue.get("message", str(issue)) if isinstance(issue, dict) else str(issue)
                step = issue.get("step", "") if isinstance(issue, dict) else ""
                target = f" [{step}]" if step else ""
                text.append(f"  • [{kind}]{target} {message}\n", style=theme.WARNING)
        recommendations = report.get("recommendations", [])
        if recommendations:
            text.append(f"recommendations ({len(recommendations)}):\n", style=theme.TEXT)
            for rec in recommendations[:5]:
                text.append(f"  * {rec}\n", style=theme.TEXT_MUTED)
        return text

    @staticmethod
    def _file_kind(ext: str) -> str:
        if ext in _IMAGE_EXTS:
            return "image"
        if ext in _VIDEO_EXTS:
            return "video"
        if ext in _AUDIO_EXTS:
            return "audio"
        if ext in _MODEL_EXTS:
            return "3d model"
        return "text"

    @staticmethod
    def _preview_header(name: str, ext: str, size: str) -> Text:
        head = Text(" ")
        head.append(name, style=theme.ACCENT + " bold")
        head.append(f"  {LibraryScreen._file_kind(ext)} · {size}\n", style=theme.TEXT_DIM)
        return head

    def _render_preview(self, path: str, data: bytes) -> Text:
        name = Path(path).name
        ext = Path(path).suffix.lower()
        size = self._format_size(len(data))
        head = self._preview_header(name, ext, size)
        if ext in _MEDIA_EXTS or b"\x00" in data[:8192]:
            body = Text(
                "Media / binary file — use 'External' to open in your default "
                "application, 'Reveal in folder' to locate it.\n",
                style=theme.TEXT_MUTED,
            )
            return Text.assemble(head, "\n", body)
        text = data.decode("utf-8", errors="replace")
        body: Text
        if ext == ".json":
            body = self._color_json(text)
        else:
            lines = text.splitlines()
            truncated = len(lines) - 2000
            if truncated > 0:
                lines = lines[-2000:]
            body = Text("\n".join(lines) or "", style=theme.TEXT)
            if truncated > 0:
                body = Text(f"… ({truncated} older lines hidden) …\n", style=theme.TEXT_DIM) + body
        return Text.assemble(head, "\n", body)

    def _color_json(self, text: str) -> Text:
        try:
            value = json.loads(text)
        except Exception:  # noqa: BLE001
            return Text(text[:200_000] or "", style=theme.TEXT)
        dumped = json.dumps(value, indent=2, ensure_ascii=False)
        if len(dumped) > 200_000:
            dumped = dumped[:200_000] + "\n… (truncated) …"
        body = Text(style=theme.TEXT_DIM)
        pos = 0
        for match in _JSON_TOKEN.finditer(dumped):
            if match.start() > pos:
                body.append(dumped[pos : match.start()])
            token = match.group()
            if token.startswith('"'):
                if dumped[match.end() : match.end() + 1] == ":":
                    body.append(token, style=theme.INFO + " bold")
                else:
                    body.append(token, style=theme.SUCCESS)
            elif token in ("true", "false", "null"):
                body.append(token, style=theme.ACCENT)
            else:
                body.append(token, style=theme.WARNING)
            pos = match.end()
        if pos < len(dumped):
            body.append(dumped[pos:])
        return body

    @on(Button.Pressed, "#btn-external-artifact")
    def on_open_external(self) -> None:
        path = self._selected_artifact_path()
        if not path:
            return
        try:
            abs_path = self.api.artifact_abs_path(self._current_production or "", path)
            self._open_external(abs_path)
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to open: {exc}", severity="error")

    @on(Button.Pressed, "#btn-copy-path")
    def on_copy_path(self) -> None:
        path = self._selected_artifact_path()
        if not path:
            return
        abs_path = str(self.api.artifact_abs_path(self._current_production or "", path))
        try:
            os.system(f"echo {abs_path} | clip")
        except Exception:  # noqa: BLE001
            pass
        self.notify(f"Copied: {abs_path}", severity="information")

    @on(Button.Pressed, "#btn-reveal")
    def on_reveal(self) -> None:
        path = self._selected_artifact_path()
        if not path:
            return
        try:
            abs_path = self.api.artifact_abs_path(self._current_production or "", path)
            system = sys.platform
            if system == "win32":
                subprocess.Popen(["explorer", "/select,", str(abs_path)])
            elif system == "darwin":
                subprocess.Popen(["open", "-R", str(abs_path)])
            else:
                subprocess.Popen(["xdg-open", str(abs_path.parent)])
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to reveal: {exc}", severity="error")

    def _open_external(self, abs_path) -> None:
        if sys.platform == "win32":
            os.startfile(abs_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(abs_path)])
        else:
            subprocess.Popen(["xdg-open", str(abs_path)])

    def _format_size(self, size: int) -> str:
        value: float = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"