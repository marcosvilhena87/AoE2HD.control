"""CLI de diagnóstico sem conexão com o processo do jogo."""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict
from .object_api import HDObjectAPI, WindowsProcessReader, ObjectAPIError
from .object_validation_v1_2 import scan_buildings
from .object_validation_v1_3 import capture_series
from .object_validation_v1_4 import capture_series as capture_v14
from .object_validation_v1_5 import phase_capture, compare_phases, append_capture, PHASES
from .selection_discovery_v1_6 import capture as capture_v16, append as append_v16, compare as compare_v16, PHASES as PHASES_V16
from .selected_object_v1_7 import inspect as inspect_v17
from .selected_objects_v1_9 import capture as capture_v19, append as append_v19, compare as compare_v19, PHASES as PHASES_V19
from .selected_objects_v2_0 import diagnose as diagnose_v20
from .selected_objects_v2_1 import capture as capture_v21, append as append_v21, compare as compare_v21, PHASES as PHASES_V21
from .selected_objects_v1_8 import capture as capture_v18, append as append_v18, compare as compare_v18, PHASES as PHASES_V18
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
    v15 = commands.add_parser("objects-v1-5", help="Registrar fase observada manualmente no jogo")
    v15.add_argument("--pid", type=int, required=True)
    v15.add_argument("--start-id", type=int, default=2100)
    v15.add_argument("--end-id", type=int, default=2300)
    v15.add_argument("--phase", choices=sorted(PHASES), required=True)
    v15.add_argument("--session", required=True)
    v15.add_argument("--output", required=True)
    v15.add_argument("--no-positions", action="store_true")
    v15.add_argument("--allow-candidates", action="store_true")
    compare = commands.add_parser("compare-v1-5", help="Comparar capturas anotadas da mesma sessao")
    compare.add_argument("--input", required=True)
    compare.add_argument("--output", help="Salvar comparacao JSON")
    v16 = commands.add_parser("selection-v1-6", help="Captura diferencial limitada de selecao")
    v16.add_argument("--pid", type=int, required=True)
    v16.add_argument("--session", required=True)
    v16.add_argument("--phase", required=True, choices=PHASES_V16)
    v16.add_argument("--ids", type=int, nargs="+", required=True)
    v16.add_argument("--object-bytes", type=int, default=256)
    v16.add_argument("--player-bytes", type=int, default=512)
    v16.add_argument("--allow-candidates", action="store_true")
    v16.add_argument("--output", required=True)
    cmp16 = commands.add_parser("compare-selection-v1-6", help="Comparar ciclos de selecao")
    cmp16.add_argument("--input", required=True)
    cmp16.add_argument("--output")
    v17 = commands.add_parser("selected-v1-7", help="Inspecionar ponteiros e flags candidatos de selecao")
    v17.add_argument("--pid", type=int, required=True)
    v17.add_argument("--ids", type=int, nargs="+", required=True)
    v17.add_argument("--allow-candidates", action="store_true")
    v17.add_argument("--output", help="Arquivo JSON opcional")
    v18 = commands.add_parser("selected-v1-8", help="Capturar selecao multipla por IDs conhecidos")
    v18.add_argument("--pid", type=int, required=True)
    v18.add_argument("--ids", type=int, nargs="+", required=True)
    v18.add_argument("--phase", choices=PHASES_V18, required=True)
    v18.add_argument("--session", required=True)
    v18.add_argument("--output", required=True)
    v18.add_argument("--allow-candidates", action="store_true")
    c18 = commands.add_parser("compare-selected-v1-8", help="Comparar capturas de selecao")
    c18.add_argument("--input", required=True)
    c18.add_argument("--output")
    v19 = commands.add_parser("selected-v1-9", help="Capturar 3+ objetos e ordem de selecao")
    v19.add_argument("--pid", type=int, required=True)
    v19.add_argument("--ids", type=int, nargs="+", required=True)
    v19.add_argument("--session", required=True)
    v19.add_argument("--phase", choices=PHASES_V19, required=True)
    v19.add_argument("--output", required=True)
    v19.add_argument("--allow-candidates", action="store_true")
    c19 = commands.add_parser("compare-selected-v1-9", help="Comparar ordem de selecao 3+")
    c19.add_argument("--input", required=True)
    c19.add_argument("--output")
    v20 = commands.add_parser("selected-v2-0", help="Consultar selecao de IDs conhecidos e procurar referencias locais")
    v20.add_argument("--pid", type=int, required=True)
    v20.add_argument("--ids", type=int, nargs="+", required=True)
    v20.add_argument("--player-bytes", type=int, default=512)
    v20.add_argument("--allow-candidates", action="store_true")
    v20.add_argument("--output", help="Salvar JSON")
    v21 = commands.add_parser("selected-v2-1", help="Capturar slots brutos de selecao no jogador")
    v21.add_argument("--pid", type=int, required=True)
    v21.add_argument("--ids", type=int, nargs="+", required=True)
    v21.add_argument("--phase", choices=PHASES_V21, required=True)
    v21.add_argument("--session", required=True)
    v21.add_argument("--output", required=True)
    v21.add_argument("--allow-candidates", action="store_true")
    c21 = commands.add_parser("compare-selected-v2-1", help="Comparar slots de selecao por fase")
    c21.add_argument("--input", required=True)
    c21.add_argument("--output")
    args = parser.parse_args(argv)
    if args.command == "selected-v2-1":
        if not args.allow_candidates:
            parser.error("v2.1 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = capture_v21(api, args.ids, args.phase, args.session)
            series = append_v21(args.output, shot)
            print(f"Captura {len(series)} fase={args.phase} salva em {args.output}")
            return 0 if not shot["errors"] else 2
        except (ObjectAPIError, OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO selected-v2-1: {exc}")
            return 1
    if args.command == "compare-selected-v2-1":
        try:
            result = compare_v21(json.loads(Path(args.input).read_text(encoding="utf-8")))
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao salva em {args.output}")
            else:
                print(payload)
            return 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO compare-selected-v2-1: {exc}")
            return 1
    if args.command == "selected-v2-0":
        if not args.allow_candidates:
            parser.error("v2.0 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = diagnose_v20(api, args.ids, player_scan_bytes=args.player_bytes)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Diagnostico gravado em {args.output}")
            else:
                print(payload)
            return 0 if not result["errors"] else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-0: {exc}")
            return 1
    if args.command == "selected-v1-9":
        if not args.allow_candidates:
            parser.error("v1.9 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = capture_v19(api, args.ids, args.session, args.phase)
            shots = append_v19(args.output, shot)
            print(f"Captura {len(shots)} fase={args.phase} salva em {args.output}")
            return 0 if not shot["observation"]["errors"] else 2
        except (ObjectAPIError, OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO selected-v1-9: {exc}")
            return 1
    if args.command == "compare-selected-v1-9":
        try:
            result = compare_v19(json.loads(Path(args.input).read_text(encoding="utf-8")))
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao salva em {args.output}")
            else:
                print(payload)
            return 0
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO compare-selected-v1-9: {exc}")
            return 1
    if args.command == "selected-v1-8":
        if not args.allow_candidates:
            parser.error("v1.8 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = capture_v18(api, args.ids, args.phase, args.session)
            saved = append_v18(args.output, shot)
            print(f"Captura {len(saved)} fase={args.phase} salva em {args.output}")
            return 0 if not shot["observation"]["errors"] else 2
        except (ObjectAPIError, OSError, ValueError, KeyError) as exc:
            print(f"ERRO selected-v1-8: {exc}")
            return 1
    if args.command == "compare-selected-v1-8":
        try:
            result = compare_v18(json.loads(Path(args.input).read_text(encoding="utf-8")))
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao salva em {args.output}")
            else:
                print(payload)
            return 0
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERRO compare-selected-v1-8: {exc}")
            return 1
    if args.command == "selected-v1-7":
        if not args.allow_candidates:
            parser.error("v1.7 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = inspect_v17(api, args.ids)
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Captura gravada em {args.output}")
            else:
                print(payload)
            return 0 if not result["errors"] else 2
        except (ObjectAPIError, OSError, ValueError) as exc:
            print(f"ERRO selected-v1-7: {exc}")
            return 1
    if args.command == "selection-v1-6":
        if not args.allow_candidates:
            parser.error("v1.6 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = capture_v16(api, args.phase, args.session, args.ids,
                    object_bytes=args.object_bytes, player_bytes=args.player_bytes)
            series = append_v16(args.output, shot)
            print(f"Captura {len(series)} fase={args.phase} registrada em {args.output}")
            return 0 if not shot["errors"] else 2
        except (OSError, ValueError, ObjectAPIError, KeyError) as exc:
            print(f"ERRO selection-v1-6: {exc}")
            return 1
    if args.command == "compare-selection-v1-6":
        try:
            series = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = compare_v16(series)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao gravada em {args.output}")
            else:
                print(payload)
            return 0 if not any(result["errors"]) else 2
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO compare-selection-v1-6: {exc}")
            return 1
    if args.command == "objects-v1-5":
        if not args.allow_candidates:
            parser.error("v1.5 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = phase_capture(api, args.start_id, args.end_id,
                    phase=args.phase, session=args.session, positions=not args.no_positions)
            series = append_capture(args.output, shot)
            print(f"Captura {len(series)} registrada: {args.phase} -> {args.output}")
            return 0 if not shot["capture"]["errors"] else 2
        except (ObjectAPIError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"ERRO objects-v1-5: {exc}")
            return 1
    if args.command == "compare-v1-5":
        try:
            shots = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = compare_phases(shots)
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao gravada em {args.output}")
            else:
                print(payload)
            return 0 if all(t["complete"] for t in result["transitions"]) else 2
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"ERRO compare-v1-5: {exc}")
            return 1
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
