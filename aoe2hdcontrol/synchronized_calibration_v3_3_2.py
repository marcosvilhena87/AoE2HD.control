"""v3.3.2 — synchronized cursor/object anchor sampling, read-only.

Observations are sequential (not atomic); record their duration explicitly.
"""
from __future__ import annotations
import math
import time
from datetime import datetime, timezone
from .position_cursor_probe_v3_2 import probe_unit_position, read_cursor_coordinates
from .camera_projection_v3_3 import calibrate_projection
from .projection_audit_v3_3_1 import audit_projection

def synchronized_anchor(api, *, pid, object_id, cursor_reader=None, clock=None):
    if type(pid) is not int or pid<=0:raise ValueError("positive PID required")
    if type(object_id) is not int or not 0<=object_id<=1000000:
        raise ValueError("invalid Object ID")
    clock=clock or time.monotonic
    cursor_reader=cursor_reader or read_cursor_coordinates
    started=clock()
    cursor_before=cursor_reader(pid)
    unit=probe_unit_position(api,object_id)
    cursor_after=cursor_reader(pid)
    elapsed=round((clock()-started)*1000,3)
    stable=(cursor_before.get("game_foreground") is True
            and cursor_after.get("game_foreground") is True
            and cursor_before.get("client")==cursor_after.get("client")
            and cursor_before.get("screen")==cursor_after.get("screen")
            and unit["finite"])
    return {"schema":"hd-synchronized-anchor-v3.3.2",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "pid":pid,"object_id":object_id,
            "observation_window_ms":elapsed,
            "cursor_before":cursor_before,"unit":unit,
            "cursor_after":cursor_after,
            "usable":bool(stable),
            "status":"candidate_anchor" if stable else "inconclusive",
            "camera_verified_stationary":False,
            "note":"Place pointer over unit center without moving it; stationary camera must be confirmed by operator."}

def fit_and_holdout(anchors, *, holdout_ids, max_rmse_px=25.):
    if not isinstance(anchors,list) or len(anchors)<4:
        raise ValueError("at least 4 anchors required")
    if not isinstance(holdout_ids,(list,tuple,set)) or not holdout_ids:
        raise ValueError("at least one holdout id required")
    if not math.isfinite(max_rmse_px) or max_rmse_px<=0:
        raise ValueError("invalid RMSE threshold")
    rows=[]
    pids=set();ids=set()
    for item in anchors:
        if item.get("schema")!="hd-synchronized-anchor-v3.3.2" or not item.get("usable"):
            raise ValueError("inconclusive or invalid anchor")
        pid=item["pid"];oid=item["object_id"]
        if oid in ids:raise ValueError("duplicate Object ID")
        ids.add(oid);pids.add(pid)
        u=item["unit"];c=item["cursor_after"]["client"]
        rows.append({"object_id":oid,"world_x":u["candidate_world_x"],
                     "world_y":u["candidate_world_y"],
                     "client_x":c["x"],"client_y":c["y"]})
    if len(pids)!=1:raise ValueError("mixed PIDs")
    hold=set(holdout_ids)
    if hold-ids:raise ValueError("holdout ID not captured")
    training=[r for r in rows if r["object_id"] not in hold]
    test=[r for r in rows if r["object_id"] in hold]
    if len(training)<3:raise ValueError("need at least 3 training anchors")
    calibration=calibrate_projection(training)
    audit=audit_projection(calibration,test)
    geometry_flags=audit["geometry"]["flags"]
    accept=(audit["holdout_rmse_px"]<=max_rmse_px
            and "nearly_parallel_world_axes" not in geometry_flags
            and "near_singular_transform" not in geometry_flags
            and "degenerate_scale" not in geometry_flags)
    return {"schema":"hd-synchronized-calibration-v3.3.2",
            "calibration":calibration,"audit":audit,
            "status":"candidate_fit_passed_threshold" if accept else "rejected",
            "holdout_threshold_px":max_rmse_px,
            "camera_verified_stationary":False,
            "dispatch":"not_dispatched",
            "note":"Passes numeric screening only. Independent camera/session verification remains necessary."}
