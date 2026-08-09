"""CLI DeepBlender : point d'entrée `deepblender` (pyproject [project.scripts])."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from deepblender import __version__
from deepblender.codegen.validator import ASTValidator
from deepblender.plugins.registry import PluginRegistry
from deepblender.plugins.render_farm import RenderFarmPlugin
from deepblender.plugins.tools import ToolRegistry
from deepblender.skills.registry import get_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deepblender", description="Production audiovisuelle assistée par agents IA (NOOA).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("inspect", help="Affiche l'environnement (Python, NOOA, skills, Blender).")

    validate = sub.add_parser("validate", help="Valide statiquement un script Blender généré.")
    validate.add_argument("script", type=Path, help="Chemin du script .py à valider.")

    serve = sub.add_parser("serve", help="Lance la gateway HTTP.")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)

    return parser


def _cmd_inspect() -> int:
    import nooa

    from deepblender.blender.bridge import BlenderBridge
    from deepblender.bridge.worker import blender_version

    registry = get_default_registry()
    bridge = BlenderBridge()
    plugin_registry = PluginRegistry()
    tool_registry = ToolRegistry()
    farm = RenderFarmPlugin()
    skills = [info.name for info in registry.discover()]
    plugins = [f"{p['name']} ({p['available']})" for p in plugin_registry.discover()]
    print(f"DeepBlender        : {__version__}")
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
    if args.command == "serve":
        from deepblender.api.server import serve

        serve(host=args.host, port=args.port)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
