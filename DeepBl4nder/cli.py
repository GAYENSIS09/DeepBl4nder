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

    serve = sub.add_parser("serve", help="Lance la gateway HTTP.")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)

    seed = sub.add_parser("seed", help="Crée le compte admin de dev (SaaS).")
    seed.add_argument("--db", default=None, help="Base SQLAlchemy (URL ou fichier SQLite).")
    seed.add_argument("--email", default=None)
    seed.add_argument("--password", default=None)
    seed.add_argument("--org", default=None)
    seed.add_argument("--project", default=None)

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
    if args.command == "serve":
        import uvicorn

        from DeepBl4nder.api.app import create_app

        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if args.command == "seed":
        from DeepBl4nder.api.seed import main as seed_main

        seed_args: list[str] = []
        for option, value in (("--db", args.db), ("--email", args.email), ("--password", args.password),
                              ("--org", args.org), ("--project", args.project)):
            if value is not None:
                seed_args.extend([option, value])
        return seed_main(seed_args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
