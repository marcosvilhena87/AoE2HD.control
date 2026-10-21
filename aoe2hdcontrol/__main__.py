"""CLI de diagnóstico sem conexão com o processo do jogo."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict
from .object_api import HDObjectAPI, WindowsProcessReader, ObjectAPIError
from .object_validation_v1_2 import scan_buildings
from .object_validation_v1_3 import capture_series
from .object_validation_v1_4 import capture_series as capture_v14
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
    scan = commands.add_parser("buildings-v1-2", help="Investigar construcoes por Object ID e proprietario")
    scan.add_argument("--pid", type=int, required=True)
    scan.add_argument("--start-id", type=int, default=2100)
    scan.add_argument("--end-id", type=int, default=2300)
    scan.add_argument("--type", type=int, default=None, help="Filtro Genie opcional (ex.: 109)")
    scan.add_argument("--all-owners", action="store_true", help="Exibir tambem construcoes de outros jogadores")
    scan.add_argument("--allow-candidates", action="store_true")
    v13 = commands.add_parser("objects-v1-3", help="Capturar tipos 109/618/619/620 em serie")
    v13.add_argument("--pid", type=int, required=True)
    v13.add_argument("--start-id", type=int, default=2100)
    v13.add_argument("--end-id", type=int, default=2300)
    v13.add_argument("--samples", type=int, default=3)
    v13.add_argument("--interval", type=float, default=1.0)
    v13.add_argument("--positions", action="store_true", help="Ler X/Y candidatos 0x3C/0x40")
    v13.add_argument("--allow-candidates", action="store_true")
    v13.add_argument("--output", help="Arquivo JSON para evidencias; opcional")
    v14 = commands.add_parser("objects-v1-4", help="Investigar referencias entre objetos HD")
    v14.add_argument("--pid", type=int, required=True)
    v14.add_argument("--start-id", type=int, default=2100)
    v14.add_argument("--end-id", type=int, default=2300)
    v14.add_argument("--samples", type=int, default=3)
    v14.add_argument("--interval", type=float, default=2.0)
    v14.add_argument("--pointer-window", type=lambda x: int(x, 0), default=0x100)
    v14.add_argument("--no-positions", action="store_true")
    v14.add_argument("--allow-candidates", action="store_true")
    v14.add_argument("--output", help="Caminho de arquivo JSON de evidencia")
    args = parser.parse_args(argv)
    if args.command == "objects-v1-4":
        if not args.allow_candidates:
            parser.error("v1.4 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = capture_v14(api, args.start_id, args.end_id,
                    samples=args.samples, interval=args.interval,
                    pointer_window=args.pointer_window, positions=not args.no_positions)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Evidencia gravada em {args.output}")
            else:
                print(payload)
            return 0 if all(not sample["errors"] for sample in result["snapshots"]) else 2
        except (ObjectAPIError, OSError, ValueError) as exc:
            print(f"ERRO objects-v1-4: {exc}")
            return 1
    if args.command == "objects-v1-3":
        if not args.allow_candidates:
            parser.error("v1.3 requer --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = capture_series(api, args.start_id, args.end_id,
                    samples=args.samples, interval=args.interval, positions=args.positions)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Evidencia gravada em {args.output}")
            else:
                print(payload)
            return 0 if all(not s["errors"] for s in result["samples"]) else 2
        except (ObjectAPIError, OSError, ValueError) as exc:
            print(f"ERRO objects-v1-3: {exc}")
            return 1
    if args.command == "buildings-v1-2":
        if not args.allow_candidates:
            parser.error("Os campos de ID/tipo/proprietario sao candidatos; use --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = scan_buildings(api, args.start_id, args.end_id,
                    only_local=not args.all_owners, target_type=args.type)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if not result["counters"]["read_errors"] else 2
        except (ObjectAPIError, OSError, ValueError) as exc:
            print(f"ERRO buildings-v1-2: {exc}")
            return 1
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
