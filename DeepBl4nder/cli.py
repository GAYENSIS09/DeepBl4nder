"""CLI DeepBl4nder : point d'entrée `DeepBl4nder` (pyproject [project.scripts])."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from DeepBl4nder import __version__
from DeepBl4nder.codegen.validator import ASTValidator
from DeepBl4nder.plugins.registry import PluginRegistry
from DeepBl4nder.plugins.rendering.render_farm import RenderFarmPlugin
from DeepBl4nder.plugins.tools import ToolRegistry
from DeepBl4nder.skills.registry import get_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="DeepBl4nder", description="Production audiovisuelle assistée par agents IA (NOOA).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("inspect", help="Affiche l'environnement (Python, NOOA, skills, Blender).")

    validate = sub.add_parser("validate", help="Valide statiquement un script Blender généré.")
    validate.add_argument("script", type=Path, help="Chemin du script .py à valider.")

    sub.add_parser("tui", help="Lance l'interface terminal (Textual TUI).")

    return parser


def _cmd_inspect() -> int:
    import nooa

    from DeepBl4nder.bridges.blender.bridge import BlenderBridge
    from DeepBl4nder.bridge.worker import blender_version

    registry = get_default_registry()
    bridge = BlenderBridge()
    plugin_registry = PluginRegistry()
    tool_registry = ToolRegistry()
    farm = RenderFarmPlugin()
    skills = [info.name for info in registry.discover()]
    plugins = [f"{p['name']} ({p['available']})" for p in plugin_registry.discover()]
    print(f"DeepBl4nder        : {__version__}")
    print(f"Python             : {sys.version.split()[0]}")
    print(f"NOOA               : {getattr(nooa, '__version__', 'unknown')}")
    print(f"Blender binaire    : {'disponible' if bridge.available() else 'absent (set BLENDER_EXE)'}")
    print(f"Blender bpy        : {blender_version()}")
    print(f"Workers            : {farm.worker_count()} (gpu: {farm.gpu_count()})")
    print(f"Skills ({len(skills)}) : {', '.join(skills) or 'aucun'}")
    print(f"Plugins            : {', '.join(plugins) or 'aucun'}")
    print(f"Tools              : {', '.join(tool_registry.names()) or 'aucun'}")
    return 0


def _cmd_validate(script: Path) -> int:
    if not script.is_file():
        print(f"erreur : fichier introuvable : {script}", file=sys.stderr)
        return 2
    report = ASTValidator().validate(script.read_text(encoding="utf-8"))
    if report.ok:
        print(f"OK : {script} (imports: {', '.join(report.imports) or 'aucun'})")
        return 0
    for error in report.errors:
        print(f"refusé : {error}", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return _cmd_inspect()
    if args.command == "validate":
        return _cmd_validate(args.script)
    if args.command == "tui":
        return _cmd_tui()
    return 2


def _cmd_tui() -> int:
    """Lance l'interface terminal (Textual TUI)."""
    try:
        from DeepBl4nder.tui.app import DeepBl4nderTUI
        _tui_preflight()
        app = DeepBl4nderTUI()
        app.run()
        return 0
    except ImportError as e:
        print("Erreur: Dépendances TUI manquantes. Installez avec: pip install 'DeepBl4nder[tui]'", file=sys.stderr)
        print(f"Détail: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erreur lancement TUI: {e}", file=sys.stderr)
        return 1


def _tui_preflight() -> None:
    """Vérifie les prérequis avant de lancer le TUI."""
    from DeepBl4nder.llm import PROVIDERS

    missing = [p for p in PROVIDERS.values() if not p.is_available()]
    if missing:
        keys = ", ".join(sorted({p.api_key_env for p in missing}))
        print(
            "AVERTISSEMENT : aucune clé d'API LLM cloud configurée.",
            file=sys.stderr,
        )
        print(
            f"Le routeur fonctionne en pool cloud uniquement — ajoutez au moins une clé dans .env : {keys}.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())
