"""CLI de diagnóstico sem conexão com o processo do jogo."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict
from .object_api import HDObjectAPI, WindowsProcessReader, ObjectAPIError
from pathlib import Path
from . import __version__
from .catalog import CATALOGS, load_catalog, mapping_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aoe2hdcontrol")
    parser.add_argument("--mapping-dir", help="Caminho para AoE2HD.mapping")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Verificar a integração com AoE2HD.mapping")
    catalog = commands.add_parser("catalog", help="Exibir contagem de registros por catálogo")
    catalog.add_argument("--kind", choices=tuple(CATALOGS), help="Inspecionar apenas um catálogo")
    obj = commands.add_parser("object", help="Ler objeto HD por ID (experimental, somente leitura)")
    obj.add_argument("--pid", type=int, required=True, help="PID explicito de AoK HD.exe")
    obj.add_argument("--id", type=int, required=True, help="Object ID da partida atual")
    obj.add_argument("--allow-candidates", action="store_true",
                     help="Aceitar offsets com estado hipotese/experimental; nao e validacao")
    args = parser.parse_args(argv)
    if args.command == "object":
        if not args.allow_candidates:
            parser.error("API de objeto depende de campos candidatos: use --allow-candidates conscientemente")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = api.get_object_by_id(args.id)
            print(json.dumps(asdict(result) if result else None, ensure_ascii=False, indent=2))
            return 0
        except (ObjectAPIError, OSError, ValueError) as exc:
            print(f"ERRO object: {exc}")
            return 1
    root = mapping_dir(args.mapping_dir)
    kinds = [args.kind] if args.command == "catalog" and args.kind else list(CATALOGS)
    print(f"AoE2HD.control v{__version__} | mapping={root}")
    failed = False
    for kind in kinds:
        try:
            rows = load_catalog(kind, root)
            print(f"OK   {kind}: {len(rows)} registros ({CATALOGS[kind]})")
        except (FileNotFoundError, OSError, ValueError, UnicodeError) as exc:
            print(f"ERRO {kind}: {exc}")
            failed = True
    if args.command == "doctor":
        print("Processo do jogo: não acessado (v0.1)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
