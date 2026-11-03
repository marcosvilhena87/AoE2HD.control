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
from .selected_objects_v2_2 import enumerate_selected as enumerate_v22
from .selected_objects_v2_3 import capture as capture_v23, append as append_v23, compare as compare_v23, PHASES as PHASES_V23
from .selected_objects_v2_4 import inspect_consistency as inspect_v24
from .selected_objects_v2_5 import inspect_selection as inspect_v25
from .selected_objects_v2_6 import inspect_selection as inspect_v26
from .selected_objects_v2_7 import inspect_selection as inspect_v27
from .selected_objects_v2_8 import make_selection_intent, verify_selection
from .selected_objects_v2_9 import evaluate_external_transition
from .selection_investigation_v3_0 import investigate_manual_selection
from .selection_coordinate_v3_1 import select_by_screen_point, DispatchGuardError
from .selection_temporal_v3_1_1 import select_with_temporal_verification
from .position_cursor_probe_v3_2 import capture_position_cursor_series
from .camera_projection_v3_3 import calibrate_projection, project
from .projection_audit_v3_3_1 import audit_projection
from .synchronized_calibration_v3_3_2 import synchronized_anchor, fit_and_holdout
from .visual_correspondence_v3_3_3 import audit_aba
from .assisted_visual_v3_3_4 import confirm_anchor, compare_recaptures
from .screenshot_v3_3_5 import screenshot_client
from .observation_projection_v3_3_6 import observe_projection
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
    v22 = commands.add_parser("selected-v2-2", help="Enumerar selecao experimental por slots")
    v22.add_argument("--pid", type=int, required=True)
    v22.add_argument("--max-entries", type=int, default=16)
    v22.add_argument("--allow-candidates", action="store_true")
    v22.add_argument("--output")
    v23 = commands.add_parser("selected-v2-3", help="Capturar capacidade experimental de selecao")
    v23.add_argument("--pid", type=int, required=True)
    v23.add_argument("--phase", choices=PHASES_V23, required=True)
    v23.add_argument("--session", required=True)
    v23.add_argument("--max-entries", type=int, default=32)
    v23.add_argument("--allow-candidates", action="store_true")
    v23.add_argument("--output", required=True)
    c23 = commands.add_parser("compare-selected-v2-3", help="Comparar capacidade e contadores candidatos")
    c23.add_argument("--input", required=True)
    c23.add_argument("--output")
    v24 = commands.add_parser("selected-v2-4", help="Conferir estabilidade de duas leituras da selecao")
    v24.add_argument("--pid", type=int, required=True)
    v24.add_argument("--max-entries", type=int, default=32)
    v24.add_argument("--allow-candidates", action="store_true")
    v24.add_argument("--output")
    v25 = commands.add_parser("selected-v2-5", help="Leitura dupla de ate 64 entradas selecionadas")
    v25.add_argument("--pid", type=int, required=True)
    v25.add_argument("--max-entries", type=int, default=64)
    v25.add_argument("--allow-candidates", action="store_true")
    v25.add_argument("--output")
    v26 = commands.add_parser("selected-v2-6", help="Enumerar selecao usando contador candidato")
    v26.add_argument("--pid", type=int, required=True)
    v26.add_argument("--allow-candidates", action="store_true")
    v26.add_argument("--output")
    v27 = commands.add_parser("selected-v2-7", help="Conferir tres snapshots completos da selecao")
    v27.add_argument("--pid", type=int, required=True)
    v27.add_argument("--allow-candidates", action="store_true")
    v27.add_argument("--output")
    v28 = commands.add_parser("selected-v2-8", help="Verificar intenção de seleção por Object ID; sem enviar comandos")
    v28.add_argument("--pid", type=int, required=True)
    v28.add_argument("--ids", nargs="+", type=int, required=True)
    v28.add_argument("--ordered", action="store_true")
    v28.add_argument("--allow-candidates", action="store_true")
    v28.add_argument("--output")
    v29 = commands.add_parser("compare-selected-v2-9", help="Auditar transicao manual entre snapshots v2.7; nao envia comandos")
    v29.add_argument("--before", required=True)
    v29.add_argument("--after", required=True)
    v29.add_argument("--ids", nargs="+", type=int, required=True)
    v29.add_argument("--output")
    v30 = commands.add_parser("investigate-selection-v3-0", help="Capturar antes/depois de seleção MANUAL no mesmo processo")
    v30.add_argument("--pid", type=int, required=True)
    v30.add_argument("--ids", nargs="+", type=int, required=True)
    v30.add_argument("--allow-candidates", action="store_true")
    v30.add_argument("--output", required=True)
    v31 = commands.add_parser("select-screen-v3-1", help="Clique experimental por coordenada de tela, confirmado por Object ID")
    v31.add_argument("--pid", type=int, required=True)
    v31.add_argument("--id", type=int, required=True)
    v31.add_argument("--x", type=int, required=True)
    v31.add_argument("--y", type=int, required=True)
    v31.add_argument("--allow-candidates", action="store_true")
    v31.add_argument("--arm", action="store_true")
    v31.add_argument("--output", required=True)
    v311 = commands.add_parser("select-screen-v3-1-1", help="Clique unico e verificacao temporal")
    v311.add_argument("--pid", type=int, required=True)
    v311.add_argument("--id", type=int, required=True)
    v311.add_argument("--x", type=int, required=True)
    v311.add_argument("--y", type=int, required=True)
    v311.add_argument("--allow-candidates", action="store_true")
    v311.add_argument("--arm", action="store_true")
    v311.add_argument("--output", required=True)
    v32 = commands.add_parser("probe-position-cursor-v3-2", help="Comparar posicao candidata da unidade com cursor do Windows")
    v32.add_argument("--pid", type=int, required=True)
    v32.add_argument("--id", type=int, required=True)
    v32.add_argument("--samples", type=int, default=12)
    v32.add_argument("--interval", type=float, default=0.5)
    v32.add_argument("--allow-candidates", action="store_true")
    v32.add_argument("--output", required=True)
    v33 = commands.add_parser("calibrate-projection-v3-3", help="Ajustar projecao empirica mundo -> cliente usando CSV de ancoras")
    v33.add_argument("--csv", required=True)
    v33.add_argument("--output", required=True)
    v331 = commands.add_parser("audit-projection-v3-3-1", help="Validacao independente e geometria da projecao")
    v331.add_argument("--calibration", required=True)
    v331.add_argument("--holdouts", required=True)
    v331.add_argument("--output", required=True)
    v332 = commands.add_parser("capture-anchor-v3-3-2", help="Capturar cursor e unidade em janela temporal curta")
    v332.add_argument("--pid", type=int, required=True)
    v332.add_argument("--id", type=int, required=True)
    v332.add_argument("--allow-candidates", action="store_true")
    v332.add_argument("--output", required=True)
    fit332 = commands.add_parser("fit-anchors-v3-3-2", help="Ajustar ancoras e validar em holdout")
    fit332.add_argument("--anchors", nargs="+", required=True)
    fit332.add_argument("--holdout-id", type=int, nargs="+", required=True)
    fit332.add_argument("--output", required=True)
    aba = commands.add_parser("audit-aba-v3-3-3", help="Auditoria A-B-A sem inferir movimento da camera")
    aba.add_argument("--first", required=True)
    aba.add_argument("--middle", required=True)
    aba.add_argument("--last", required=True)
    aba.add_argument("--output", required=True)
    aba.add_argument("--cursor-tolerance-px", type=float, default=15.0)
    aba.add_argument("--world-tolerance", type=float, default=0.02)
    confirm = commands.add_parser("confirm-anchor-v3-3-4", help="Anotar confirmacao humana e geometria da janela")
    confirm.add_argument("--anchor", required=True)
    confirm.add_argument("--id", type=int, required=True)
    confirm.add_argument("--operator-confirmed", action="store_true")
    confirm.add_argument("--window-json", required=True)
    confirm.add_argument("--output", required=True)
    repeat = commands.add_parser("compare-assisted-v3-3-4", help="Conferir repetibilidade visual da mesma unidade")
    repeat.add_argument("--first", required=True)
    repeat.add_argument("--last", required=True)
    repeat.add_argument("--output", required=True)
    visual = commands.add_parser("capture-anchor-v3-3-5", help="Atraso configuravel, ancora e imagem BMP da area cliente")
    visual.add_argument("--pid", type=int, required=True)
    visual.add_argument("--id", type=int, required=True)
    visual.add_argument("--delay", type=float, default=15.0)
    visual.add_argument("--allow-candidates", action="store_true")
    visual.add_argument("--output", required=True)
    visual.add_argument("--image", help="Caminho BMP (padrao: mesmo nome do JSON)")
    obs = commands.add_parser("observe-projection-v3-3-6", help="Prever ponto cliente sem enviar cliques")
    obs.add_argument("--pid", type=int, required=True)
    obs.add_argument("--id", type=int, required=True)
    obs.add_argument("--fit", required=True)
    obs.add_argument("--client-width", type=int, required=True)
    obs.add_argument("--client-height", type=int, required=True)
    obs.add_argument("--measurement", help="JSON v3.3.5 independente opcional")
    obs.add_argument("--allow-candidates", action="store_true")
    obs.add_argument("--output", required=True)
    batch = commands.add_parser("validate-projections-v3-3-7", help="Auditar relatorios observacionais v3.3.6 em lote")
    batch.add_argument("--reports", nargs="+", required=True)
    batch.add_argument("--exclude-ids", nargs="+", type=int, required=True,
                       help="IDs usados no ajuste, holdout e validacoes anteriores")
    batch.add_argument("--min-samples", type=int, default=10)
    batch.add_argument("--threshold-px", type=float, default=25.0)
    batch.add_argument("--output", required=True)
    residual = commands.add_parser("audit-residuals-v3-3-8", help="Auditoria visual offline de residuos e repeticoes")
    residual.add_argument("--reports", nargs="+", required=True)
    residual.add_argument("--client-width", type=int, default=1536)
    residual.add_argument("--client-height", type=int, default=864)
    residual.add_argument("--threshold-px", type=float, default=25.0)
    residual.add_argument("--output", required=True)
    residual.add_argument("--svg", required=True, help="Mapa vetorial dos vetores de erro")
    review = commands.add_parser("review-correspondence-v3-3-9", help="Revisao visual manual e residuos robustos offline")
    review.add_argument("--audit", required=True, help="JSON v3.3.8")
    review.add_argument("--reviews", required=True, help="Manifesto de revisao manual JSON")
    review.add_argument("--output", required=True)
    camera = commands.add_parser("check-camera-v3-3-10", help="Detectar deslocamento entre dois BMPs por marcos estaticos")
    camera.add_argument("--before", required=True)
    camera.add_argument("--after", required=True)
    camera.add_argument("--anchors", required=True, help="JSON com lista de coordenadas de terreno estatico")
    camera.add_argument("--search-px", type=int, default=60)
    camera.add_argument("--output", required=True)
    guarded = commands.add_parser("gate-camera-v3-3-10", help="Bloqueio conservador do lote segundo a camera")
    guarded.add_argument("--camera", required=True)
    guarded.add_argument("--batch", required=True)
    guarded.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "check-camera-v3-3-10":
        from .camera_guard_v3_3_10 import detect_camera_motion
        try:
            from PIL import Image
            marks=json.loads(Path(args.anchors).read_text(encoding="utf-8-sig"))
            if not isinstance(marks,list):
                raise ValueError("anchors must be a JSON list")
            with Image.open(args.before) as left, Image.open(args.after) as right:
                result=detect_camera_motion(left,right,marks,search_px=args.search_px)
            result["before_file"]=str(args.before)
            result["after_file"]=str(args.after)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"Camera v3.3.10: {result['status']}; marcadores={result['n_matches']}/{result['n_anchors']}; dx={result['median_dx_px']}; dy={result['median_dy_px']}; {args.output}")
            return 0 if result["status"]=="candidate_camera_static" else 2
        except (OSError,ValueError,TypeError,KeyError,ImportError) as exc:
            print(f"ERRO check-camera-v3-3-10: {exc}")
            return 1
    if args.command == "gate-camera-v3-3-10":
        from .camera_guard_v3_3_10 import gate_batch
        try:
            cam=json.loads(Path(args.camera).read_text(encoding="utf-8-sig"))
            batch=json.loads(Path(args.batch).read_text(encoding="utf-8-sig"))
            result=gate_batch(cam,batch)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"Camera gate v3.3.10: {result['status']}; selection={result['validated_for_selection']}; {args.output}")
            return 2
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO gate-camera-v3-3-10: {exc}")
            return 1
    if args.command == "review-correspondence-v3-3-9":
        from .correspondence_review_v3_3_9 import review_audit
        try:
            audit=json.loads(Path(args.audit).read_text(encoding="utf-8-sig"))
            labels=json.loads(Path(args.reviews).read_text(encoding="utf-8-sig"))
            result=review_audit(audit,labels)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(f"Revisao v3.3.9: observacoes={result['all_observations']['n']}; elegiveis={result['review_eligible_only']['n']}; pendentes={result['flagged_or_unreviewed']['n']}; {args.output}")
            return 0
        except (OSError,ValueError,KeyError,TypeError) as exc:
            print(f"ERRO review-correspondence-v3-3-9: {exc}")
            return 1
    if args.command == "audit-residuals-v3-3-8":
        from .residual_audit_v3_3_8 import audit_residuals, render_svg
        try:
            if Path(args.output).resolve()==Path(args.svg).resolve():
                raise ValueError("JSON e SVG devem ser arquivos distintos")
            entries=[(p,json.loads(Path(p).read_text(encoding="utf-8-sig"))) for p in args.reports]
            result=audit_residuals(entries,client_width=args.client_width,
                client_height=args.client_height,threshold_px=args.threshold_px)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            Path(args.svg).write_text(render_svg(result),encoding="utf-8")
            print(f"Auditoria v3.3.8: amostras={len(result['samples'])}; repetidos={len(result['repeated_objects'])}; invalidos={len(result['invalid'])}; {args.output}; {args.svg}")
            return 0 if result["samples"] and not result["invalid"] else 2
        except (OSError,ValueError,KeyError,TypeError) as exc:
            print(f"ERRO audit-residuals-v3-3-8: {exc}")
            return 1
    if args.command == "validate-projections-v3-3-7":
        from .batch_validation_v3_3_7 import validate_batch
        try:
            records=[(p,json.loads(Path(p).read_text(encoding="utf-8-sig"))) for p in args.reports]
            result=validate_batch(records,excluded_ids=args.exclude_ids,
                min_samples=args.min_samples,threshold_px=args.threshold_px)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            m=result["metrics"]
            print(f"Validacao v3.3.7: {result['status']}; validos={m['count']}; rejeitados={len(result['rejected'])}; RMSE={m['rmse_px']}; {args.output}")
            return 0 if result["status"]=="candidate_batch_passed" else 2
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO validate-projections-v3-3-7: {exc}")
            return 1
    if args.command == "observe-projection-v3-3-6":
        if not args.allow_candidates:
            parser.error("v3.3.6 exige --allow-candidates")
        try:
            fit=json.loads(Path(args.fit).read_text(encoding="utf-8-sig"))
            measurement=(json.loads(Path(args.measurement).read_text(encoding="utf-8-sig"))
                         if args.measurement else None)
            with WindowsProcessReader(args.pid) as reader:
                api=HDObjectAPI(reader,mapping_dir(args.mapping_dir),allow_candidates=True)
                result=observe_projection(api,pid=args.pid,object_id=args.id,fit=fit,
                    client_width=args.client_width,client_height=args.client_height,
                    measurement=measurement)
            Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            p=result["predicted_client"]
            print(f"Observacao v3.3.6: Object ID={args.id} ponto=({p['x']:.2f}, {p['y']:.2f}) dentro={result['inside_client']}; {args.output}")
            return 0 if result["inside_client"] else 2
        except (OSError,ValueError,TypeError,KeyError,ObjectAPIError) as exc:
            print(f"ERRO observe-projection-v3-3-6: {exc}")
            return 1
    if args.command == "capture-anchor-v3-3-5":
        if not args.allow_candidates:
            parser.error("v3.3.5 exige --allow-candidates")
        if not 0 <= args.delay <= 120:
            parser.error("--delay deve estar entre 0 e 120 segundos")
        try:
            import time
            from datetime import datetime, timezone
            from .position_cursor_probe_v3_2 import read_cursor_coordinates
            image_path = Path(args.image) if args.image else Path(args.output).with_suffix(".bmp")
            if image_path.resolve() == Path(args.output).resolve():
                raise ValueError("image and JSON paths must differ")
            print(f"Volte ao jogo e posicione cursor sobre a base da unidade {args.id}; captura em {args.delay:g} s.",flush=True)
            time.sleep(args.delay)
            with WindowsProcessReader(args.pid) as reader:
                api=HDObjectAPI(reader,mapping_dir(args.mapping_dir),allow_candidates=True)
                anchor=synchronized_anchor(api,pid=args.pid,object_id=args.id)
                before_image=read_cursor_coordinates(args.pid)
                image_meta=None
                image_error=None
                try:
                    image_meta=screenshot_client(args.pid,image_path)
                except (OSError,ValueError) as exc:
                    image_error=str(exc)
                after_image=read_cursor_coordinates(args.pid)
            stable_image=(before_image.get("game_foreground") is True
                          and after_image.get("game_foreground") is True
                          and before_image.get("client")==after_image.get("client")
                          and anchor["cursor_after"].get("client")==before_image.get("client"))
            usable=bool(anchor["usable"] and stable_image and image_meta is not None)
            report={"schema":"hd-visual-evidence-v3.3.5",
                    "timestamp_utc":datetime.now(timezone.utc).isoformat(),
                    "pid":args.pid,"object_id":args.id,"delay_seconds":args.delay,
                    "anchor":anchor,"cursor_before_image":before_image,
                    "cursor_after_image":after_image,
                    "image":image_meta,"image_error":image_error,
                    "cursor_stable_across_image":stable_image,
                    "status":"candidate_visual_evidence" if usable else "inconclusive",
                    "visual_object_correspondence":"unverified",
                    "camera_movement":"unknown","dispatch":"not_dispatched",
                    "note":"Image follows anchor; not atomic. Visually inspect BMP; cursor may not be drawn in GDI screenshot."}
            Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Evidencia v3.3.5: {report['status']}; JSON={args.output}; BMP={image_path if image_meta else 'indisponivel'}")
            return 0 if usable else 2
        except (OSError,ValueError,TypeError,ObjectAPIError) as exc:
            print(f"ERRO capture-anchor-v3-3-5: {exc}")
            return 1
    if args.command == "confirm-anchor-v3-3-4":
        try:
            raw=json.loads(Path(args.anchor).read_text(encoding="utf-8-sig"))
            window=json.loads(Path(args.window_json).read_text(encoding="utf-8-sig"))
            result=confirm_anchor(raw,confirmed_id=args.id,
                                  operator_confirmed=args.operator_confirmed,window=window)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Confirmacao assistida v3.3.4: {result['status']}; {args.output}")
            return 0
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO confirm-anchor-v3-3-4: {exc}")
            return 1
    if args.command == "compare-assisted-v3-3-4":
        try:
            first=json.loads(Path(args.first).read_text(encoding="utf-8-sig"))
            last=json.loads(Path(args.last).read_text(encoding="utf-8-sig"))
            result=compare_recaptures(first,last)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Comparacao v3.3.4: {result['status']}; delta={result['cursor_distance_px']:.2f} px")
            return 0
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO compare-assisted-v3-3-4: {exc}")
            return 1
    if args.command == "audit-aba-v3-3-3":
        try:
            samples=[json.loads(Path(p).read_text(encoding="utf-8-sig"))
                     for p in (args.first,args.middle,args.last)]
            result=audit_aba(*samples,cursor_tolerance_px=args.cursor_tolerance_px,
                             world_tolerance=args.world_tolerance)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Auditoria A-B-A v3.3.3: {result['status']}; delta cursor={result['cursor_delta_px']['distance']:.2f} px")
            return 0
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO audit-aba-v3-3-3: {exc}")
            return 1
    if args.command == "capture-anchor-v3-3-2":
        if not args.allow_candidates:
            parser.error("v3.3.2 exige --allow-candidates")
        try:
            import time
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                print("Em 5 segundos, mantenha o cursor PARADO sobre a unidade identificada.")
                time.sleep(5)
                result = synchronized_anchor(api,pid=args.pid,object_id=args.id)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Ancora v3.3.2: {result['status']}; {args.output}")
            return 0 if result["usable"] else 2
        except (ObjectAPIError,OSError,ValueError,TypeError) as exc:
            print(f"ERRO capture-anchor-v3-3-2: {exc}")
            return 1
    if args.command == "fit-anchors-v3-3-2":
        try:
            anchors=[json.loads(Path(path).read_text(encoding="utf-8-sig")) for path in args.anchors]
            result=fit_and_holdout(anchors,holdout_ids=args.holdout_id)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Fit v3.3.2: {result['status']}; RMSE={result['audit']['holdout_rmse_px']:.2f} px")
            return 0 if result["status"]=="candidate_fit_passed_threshold" else 2
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO fit-anchors-v3-3-2: {exc}")
            return 1
    if args.command == "audit-projection-v3-3-1":
        try:
            import csv
            calibration = json.loads(Path(args.calibration).read_text(encoding="utf-8-sig"))
            with Path(args.holdouts).open(encoding="utf-8-sig",newline="") as fh:
                holdouts = list(csv.DictReader(fh))
            result = audit_projection(calibration, holdouts)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(f"Auditoria v3.3.1: RMSE independente={result['holdout_rmse_px']:.2f} px; arquivo={args.output}")
            return 0
        except (OSError,ValueError,TypeError,KeyError) as exc:
            print(f"ERRO audit-projection-v3-3-1: {exc}")
            return 1
    if args.command == "calibrate-projection-v3-3":
        try:
            import csv
            with Path(args.csv).open(encoding="utf-8-sig",newline="") as fh:
                pairs = list(csv.DictReader(fh))
            result = calibrate_projection(pairs)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False) + "\n",encoding="utf-8")
            print(f"Calibracao v3.3: RMSE={result['rmse_px']} px; arquivo={args.output}")
            return 0
        except (OSError,ValueError,TypeError) as exc:
            print(f"ERRO calibrate-projection-v3-3: {exc}")
            return 1
    if args.command == "probe-position-cursor-v3-2":
        if not args.allow_candidates:
            parser.error("v3.2 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                print("Volte ao jogo; movimente o cursor e a unidade durante as amostras.")
                import time
                time.sleep(5)
                result = capture_position_cursor_series(api, pid=args.pid,
                    object_id=args.id, samples=args.samples, interval=args.interval)
            Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False) + "\n",encoding="utf-8")
            print(f"Relatorio v3.2 salvo em {args.output}")
            return 0
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO probe-position-cursor-v3-2: {exc}")
            return 1
    if args.command == "select-screen-v3-1-1":
        if not args.allow_candidates or not args.arm:
            parser.error("v3.1.1 exige --allow-candidates e --arm")
        try:
            import time
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                print("Volte ao jogo AGORA; clique unico em 5 segundos.")
                time.sleep(5)
                result = select_with_temporal_verification(api, pid=args.pid,
                    object_id=args.id, x=args.x, y=args.y, armed=True)
            Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Resultado v3.1.1: {result['status']}; relatorio em {args.output}")
            return 0 if result["match"] else 2
        except (DispatchGuardError, ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO select-screen-v3-1-1: {exc}")
            return 1
    if args.command == "select-screen-v3-1":
        if not args.allow_candidates or not args.arm:
            parser.error("v3.1 exige --allow-candidates e --arm")
        try:
            import time
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                print("Retorne ao jogo AGORA; clique automatico unico em 5 segundos.")
                time.sleep(5)
                result = select_by_screen_point(api, pid=args.pid,
                    object_id=args.id, x=args.x, y=args.y, armed=True)
            Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Resultado v3.1: {result['status']}; relatorio em {args.output}")
            return 0 if result["match"] else 2
        except (DispatchGuardError, ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO select-screen-v3-1: {exc}")
            return 1
    if args.command == "investigate-selection-v3-0":
        if not args.allow_candidates:
            parser.error("v3.0 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                def manual_pause():
                    print("Captura ANTES concluida. Selecione MANUALMENTE o alvo no jogo; volte aqui.")
                    input("Pressione Enter para realizar a captura DEPOIS: ")
                result = investigate_manual_selection(api, args.ids,
                    pause_for_manual_action=manual_pause, pid=args.pid)
            Path(args.output).write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"Investigacao v3.0 gravada em {args.output}; status={result['status']}")
            return 0 if result["status"] == "external_transition_observed" else 2
        except (ObjectAPIError, OSError, ValueError, TypeError, EOFError) as exc:
            print(f"ERRO investigate-selection-v3-0: {exc}")
            return 1
    if args.command == "compare-selected-v2-9":
        try:
            intent = make_selection_intent(args.ids)
            before = json.loads(Path(args.before).read_text(encoding="utf-8"))
            after = json.loads(Path(args.after).read_text(encoding="utf-8"))
            result = evaluate_external_transition(intent, before, after)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao v2.9 gravada em {args.output}")
            else:
                print(payload)
            return 0 if result["status"] == "external_transition_observed" else 2
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERRO compare-selected-v2-9: {exc}")
            return 1
    if args.command == "selected-v2-8":
        if not args.allow_candidates:
            parser.error("v2.8 exige --allow-candidates")
        try:
            intent = make_selection_intent(args.ids)
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = verify_selection(api, intent, ordered=args.ordered)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Verificacao v2.8 gravada em {args.output}")
            else:
                print(payload)
            return 0 if result["match"] else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-8: {exc}")
            return 1
    if args.command == "selected-v2-7":
        if not args.allow_candidates:
            parser.error("v2.7 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = inspect_v27(api)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Diagnostico v2.7 gravado em {args.output}")
            else:
                print(payload)
            return 0 if result["consistency"] == "stable_with_candidate_count" else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-7: {exc}")
            return 1
    if args.command == "selected-v2-6":
        if not args.allow_candidates:
            parser.error("v2.6 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = inspect_v26(api)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Diagnostico v2.6 gravado em {args.output}")
            else:
                print(payload)
            return 0 if result["consistency"]=="consistent_with_candidate_count" else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-6: {exc}")
            return 1
    if args.command == "selected-v2-5":
        if not args.allow_candidates:
            parser.error("v2.5 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = inspect_v25(api, max_entries=args.max_entries)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Diagnostico v2.5 gravado em {args.output}")
            else:
                print(payload)
            return 0 if result["consistency"]=="stable_within_window" else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-5: {exc}")
            return 1
    if args.command == "selected-v2-4":
        if not args.allow_candidates:
            parser.error("v2.4 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = inspect_v24(api, max_entries=args.max_entries)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Diagnostico v2.4 gravado em {args.output}")
            else:
                print(payload)
            return 0 if result["consistency"]=="stable_within_window" else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-4: {exc}")
            return 1
    if args.command == "selected-v2-3":
        if not args.allow_candidates:
            parser.error("v2.3 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                shot = capture_v23(api, args.phase, args.session, max_entries=args.max_entries)
            series = append_v23(args.output, shot)
            print(f"Captura {len(series)} fase={args.phase} salva em {args.output}")
            return 0 if not shot["enumeration"]["anomalies"] else 2
        except (ObjectAPIError, OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERRO selected-v2-3: {exc}")
            return 1
    if args.command == "compare-selected-v2-3":
        try:
            result = compare_v23(json.loads(Path(args.input).read_text(encoding="utf-8")))
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Comparacao salva em {args.output}")
            else:
                print(payload)
            return 0
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"ERRO compare-selected-v2-3: {exc}")
            return 1
    if args.command == "selected-v2-2":
        if not args.allow_candidates:
            parser.error("v2.2 exige --allow-candidates")
        try:
            with WindowsProcessReader(args.pid) as reader:
                api = HDObjectAPI(reader, mapping_dir(args.mapping_dir), allow_candidates=True)
                result = enumerate_v22(api, max_entries=args.max_entries)
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output:
                Path(args.output).write_text(payload + "\n", encoding="utf-8")
                print(f"Enumeracao experimental gravada em {args.output}")
            else:
                print(payload)
            return 0 if not result["anomalies"] else 2
        except (ObjectAPIError, OSError, ValueError, TypeError) as exc:
            print(f"ERRO selected-v2-2: {exc}")
            return 1
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
