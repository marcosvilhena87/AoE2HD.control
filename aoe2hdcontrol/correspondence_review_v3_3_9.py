"""v3.3.9: human-reviewed correspondence and robust descriptive residual audit.

Offline only. Source files are read but never modified. Manual labels are evidence
of reviewer assertions, not proof of automatic image recognition.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IDENTITY = {"confirmed", "rejected", "uncertain"}
CAMERA = {"confirmed_static", "changed", "uncertain"}
REFERENCE = {"unit_base", "other", "unknown"}


def _stats(points, threshold):
    errors = [p["error_px"] for p in points]
    n = len(points)
    return {"n": n,
            "mean_error_px": statistics.mean(errors) if n else None,
            "median_error_px": statistics.median(errors) if n else None,
            "rmse_px": math.sqrt(sum(v*v for v in errors)/n) if n else None,
            "max_error_px": max(errors) if n else None,
            "within_25_or_threshold_count": sum(x <= threshold for x in errors),
            "mean_dx_px": statistics.mean(p["residual"]["x"] for p in points) if n else None,
            "mean_dy_px": statistics.mean(p["residual"]["y"] for p in points) if n else None}


def _theil_sen(points, axis):
    pairs = []
    for i,a in enumerate(points):
        for b in points[i+1:]:
            dx = b["predicted"][axis]-a["predicted"][axis]
            if abs(dx)>1e-9:
                pairs.append((b["residual"][axis]-a["residual"][axis])/dx)
    return {"slope": statistics.median(pairs) if pairs else None,
            "pair_count": len(pairs), "method": "theil_sen_descriptive_only"}


def review_audit(audit, review_manifest, *, threshold_px=None):
    if audit.get("schema") != "hd-residual-audit-v3.3.8":
        raise ValueError("expected v3.3.8 residual audit")
    if review_manifest.get("schema") != "hd-visual-reviews-v3.3.9":
        raise ValueError("expected v3.3.9 review manifest")
    threshold = float(audit["threshold_px"] if threshold_px is None else threshold_px)
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("invalid threshold")
    rows = audit["samples"]
    paths = [p["file"] for p in rows]
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate source path in residual audit: cannot review unambiguously")
    known = set(paths)
    labels = {}
    for review in review_manifest.get("reviews", []):
        path = review["report"]
        if path not in known:
            raise ValueError(f"review references unknown report: {path}")
        if path in labels:
            raise ValueError(f"duplicate review for {path}")
        if review.get("identity") not in IDENTITY or review.get("camera") not in CAMERA:
            raise ValueError(f"invalid review labels: {path}")
        if review.get("reference") not in REFERENCE:
            raise ValueError(f"invalid reference: {path}")
        if review["identity"] != "uncertain" or review["camera"] != "uncertain":
            if not str(review.get("reason", "")).strip():
                raise ValueError(f"reason required for asserted review: {path}")
        labels[path] = {"identity": review["identity"],
                        "camera": review["camera"],
                        "reference": review["reference"],
                        "reason": str(review.get("reason", "")),
                        "bmp": str(review.get("bmp", "")),
                        "reviewer": str(review.get("reviewer", ""))}
    detailed = []
    for row in rows:
        status = labels.get(row["file"], {"identity":"uncertain","camera":"uncertain",
                     "reference":"unknown","reason":"not_reviewed","bmp":"","reviewer":""})
        is_confirmed = (status["identity"] == "confirmed" and
                        status["camera"] == "confirmed_static" and
                        status["reference"] == "unit_base")
        detailed.append({**row, "review": status,
                         "review_eligible": is_confirmed})
    confirmed=[x for x in detailed if x["review_eligible"]]
    flagged=[x for x in detailed if not x["review_eligible"]]
    # Repeated observations count as observations, not independent objects.
    repeated=defaultdict(list)
    for s in detailed: repeated[(s["pid"],s["object_id"])].append(s)
    groups=[]
    for (pid,oid),entries in sorted(repeated.items()):
        if len(entries)>1:
            spread=max(math.hypot(a["measured"]["x"]-b["measured"]["x"],
                                  a["measured"]["y"]-b["measured"]["y"])
                       for a in entries for b in entries)
            groups.append({"pid":pid,"object_id":oid,"n":len(entries),
                           "max_measured_spread_px":spread,
                           "reports":[a["file"] for a in entries],
                           "classification":"manual_review_required"})
    h=float(audit["client"]["height"])
    spatial=[]
    for region,subset in (("upper", [x for x in detailed if x["predicted"]["y"]<h/3]),
                          ("middle", [x for x in detailed if h/3<=x["predicted"]["y"]<2*h/3]),
                          ("lower", [x for x in detailed if x["predicted"]["y"]>=2*h/3])):
        spatial.append({"region":region,"all":_stats(subset,threshold),
                        "review_eligible":_stats([x for x in subset if x["review_eligible"]],threshold)})
    return {"schema":"hd-correspondence-robust-audit-v3.3.9",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"manual_review_required",
            "threshold_px":threshold,
            "all_observations":_stats(detailed,threshold),
            "review_eligible_only":_stats(confirmed,threshold),
            "flagged_or_unreviewed":_stats(flagged,threshold),
            "n_distinct_objects_all":len(repeated),
            "n_distinct_objects_review_eligible":len({(x["pid"],x["object_id"]) for x in confirmed}),
            "region_by_predicted_y":spatial,
            "robust_trends_all":{"dx_vs_x":_theil_sen(detailed,"x"),
                                 "dy_vs_y":_theil_sen(detailed,"y")},
            "robust_trends_review_eligible":{"dx_vs_x":_theil_sen(confirmed,"x"),
                                             "dy_vs_y":_theil_sen(confirmed,"y")},
            "repeated_objects":groups,"samples":detailed,
            "invalid_source_entries":audit.get("invalid",[]),
            "interpretation":"These are descriptive statistics, not a recalibration.",
            "selection_dispatch":"not_dispatched",
            "camera_consistency":"operator_asserted_only",
            "visual_correspondence":"operator_asserted_only",
            "note":"Preserves all originals and all outliers; subset results may be biased by review decisions. SVG/BMP review is manual."}
