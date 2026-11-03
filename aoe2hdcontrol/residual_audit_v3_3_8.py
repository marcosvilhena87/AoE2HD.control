"""v3.3.8 — offline residual audit and visual correspondence review.

All observations are retained, including repeated objects and failed measurements.
This module never accesses the game process or dispatches input.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from html import escape


def _trend(points, dimension):
    """Descriptive ordinary-least-squares slope only; never changes calibration."""
    if len(points) < 3:
        return {"slope": None, "n": len(points), "reason": "fewer_than_three"}
    xs = [p["predicted"][dimension] for p in points]
    ys = [p["residual"][dimension] for p in points]
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    denominator = sum((x - mx) ** 2 for x in xs)
    if denominator < 1e-12:
        return {"slope": None, "n": len(points), "reason": "zero_coordinate_variance"}
    return {"slope": sum((x - mx)*(y - my) for x, y in zip(xs, ys)) / denominator,
            "n": len(points), "reason": "descriptive_only"}


def audit_residuals(records, *, client_width, client_height, threshold_px=25.0):
    if not 0 < client_width <= 8192 or not 0 < client_height <= 8192:
        raise ValueError("invalid client dimensions")
    if not math.isfinite(threshold_px) or threshold_px <= 0:
        raise ValueError("invalid threshold")
    samples, invalid = [], []
    for path, report in records:
        try:
            if report.get("schema") != "hd-observation-projection-v3.3.6":
                raise ValueError("wrong_schema")
            if report.get("selection_dispatch") != "not_dispatched" or report.get("memory_write") is not False:
                raise ValueError("not_read_only")
            measured = report["measurement_comparison"]
            if not isinstance(measured, dict):
                raise ValueError("missing_measurement")
            if measured.get("correspondence") != "operator_review_required":
                raise ValueError("unexpected_correspondence")
            pred = report["predicted_client"]
            px, py = float(pred["x"]), float(pred["y"])
            mx, my = float(measured["measured_client_x"]), float(measured["measured_client_y"])
            if not all(math.isfinite(v) for v in (px,py,mx,my)):
                raise ValueError("nonfinite_coordinate")
            if not all(0 <= a < b for a,b in ((px,client_width),(py,client_height),(mx,client_width),(my,client_height))):
                raise ValueError("out_of_client_bounds")
            oid, pid = int(report["object_id"]), int(report["pid"])
            if oid < 0 or pid < 1:
                raise ValueError("invalid_identity")
            dx,dy=mx-px,my-py
            error=math.hypot(dx,dy)
            if abs(error-float(measured["error_px"])) > .15:
                raise ValueError("inconsistent_error")
            samples.append({"file":str(path),"object_id":oid,"pid":pid,
                "predicted":{"x":px,"y":py},"measured":{"x":mx,"y":my},
                "residual":{"x":dx,"y":dy},"error_px":error,"within_threshold":error<=threshold_px,
                "visual_review":"pending","camera_review":"pending"})
        except (KeyError,ValueError,TypeError,OverflowError,AttributeError) as exc:
            invalid.append({"file":str(path),"reason":str(exc)})
    grouped=defaultdict(list)
    for sample in samples:
        grouped[(sample["pid"],sample["object_id"])].append(sample)
    repeated=[]
    for (pid,oid), arr in sorted(grouped.items()):
        if len(arr)<2:continue
        spread=max(math.hypot(a["measured"]["x"]-b["measured"]["x"],
                              a["measured"]["y"]-b["measured"]["y"])
                   for a in arr for b in arr)
        repeated.append({"pid":pid,"object_id":oid,"samples":len(arr),
                         "max_cursor_spread_px":spread,"requires_visual_review":True,
                         "files":[x["file"] for x in arr]})
    n=len(samples)
    errors=[s["error_px"] for s in samples]
    output={"schema":"hd-residual-audit-v3.3.8",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "status":"review_required",
        "client":{"width":client_width,"height":client_height},
        "threshold_px":threshold_px,
        "samples":samples,"invalid":invalid,"repeated_objects":repeated,
        "statistics":{"n_observations":n,"n_distinct_object_pid":len(grouped),
            "mean_dx_px":statistics.mean([s["residual"]["x"] for s in samples]) if n else None,
            "mean_dy_px":statistics.mean([s["residual"]["y"] for s in samples]) if n else None,
            "mean_error_px":statistics.mean(errors) if n else None,
            "rmse_px":math.sqrt(statistics.mean([e*e for e in errors])) if n else None,
            "max_error_px":max(errors) if n else None,
            "inside_tolerance":sum(s["within_threshold"] for s in samples)},
        "trends":{"x_residual_vs_predicted_x":_trend(samples,"x"),
                  "y_residual_vs_predicted_y":_trend(samples,"y")},
        "camera_consistency":"unverified","visual_correspondence":"unverified",
        "note":"Repeated measurements retained; no cherry-picking, auto-recalibration or selection."}
    return output


def render_svg(report):
    """Standalone inspectable coordinate plot; does not embed or validate BMPs."""
    width=report["client"]["width"];height=report["client"]["height"]
    pieces=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#141b29"/>']
    for idx,s in enumerate(report["samples"]):
        x=s["predicted"]["x"];y=s["predicted"]["y"]
        mx=s["measured"]["x"];my=s["measured"]["y"]
        color="#ff7a7a" if not s["within_threshold"] else "#78d1ff"
        title=escape(f'ID {s["object_id"]} | {s["file"]} | erro={s["error_px"]:.2f}px')
        pieces.extend([f'<g><title>{title}</title>',
            f'<line x1="{x:.3f}" y1="{y:.3f}" x2="{mx:.3f}" y2="{my:.3f}" stroke="{color}" stroke-width="2"/>',
            f'<circle cx="{x:.3f}" cy="{y:.3f}" r="5" fill="none" stroke="{color}" stroke-width="2"/>',
            f'<circle cx="{mx:.3f}" cy="{my:.3f}" r="3.5" fill="{color}"/>',
            f'<text x="{x+7:.3f}" y="{y-8:.3f}" fill="#ffffff" font-family="sans-serif" font-size="12">{s["object_id"]}</text>',
            '</g>'])
    pieces.append('</svg>')
    return "\n".join(pieces)+"\n"
