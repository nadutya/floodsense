"""Small, deterministic urban-drainage model used by the demonstrator.

The model is intentionally explainable: each drain is a storage bucket. Rainfall
creates runoff from its catchment, effective pipe capacity is reduced by blockage,
and overflow is routed to a lower downstream bucket. It is a scenario model, not a
calibrated hydraulic forecast or machine-learning system.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_PATH = Path(__file__).parent / "data" / "oxford_demo.json"


def load_network() -> Dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _risk(fill: float, overflow_m3: float, minutes_to_overflow: Optional[int]) -> str:
    if overflow_m3 > 0 or (minutes_to_overflow is not None and minutes_to_overflow <= 4):
        return "critical"
    if fill >= 0.82 or (minutes_to_overflow is not None and minutes_to_overflow <= 15):
        return "high"
    if fill >= 0.52 or (minutes_to_overflow is not None and minutes_to_overflow <= 40):
        return "watch"
    return "normal"


def _score(state: Dict[str, Any], drain: Dict[str, Any], assets: Dict[str, Any]) -> float:
    asset_weight = assets.get(drain.get("asset"), {}).get("priority", 0.25)
    urgency = 1.0 if state["overflow_m3"] > 0 else max(0.0, 1 - (state.get("minutes_to_overflow") or 90) / 90)
    return round(100 * (0.48 * urgency + 0.32 * drain["blockage"] + 0.20 * asset_weight), 1)


def simulate(rainfall_mmh: float = 38.0, duration_minutes: int = 90,
             cleaned_drain_id: Optional[str] = None, cleaning_minute: int = 18,
             rainfall_schedule: Optional[List[Dict[str, float]]] = None,
             interventions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    if not 0 <= rainfall_mmh <= 120:
        raise ValueError("rainfall_mmh must be between 0 and 120")
    if duration_minutes < 1:
        raise ValueError("duration_minutes must be positive")
    schedule = sorted(rainfall_schedule or [{"minute": 0, "rainfall_mmh": rainfall_mmh}], key=lambda x: x["minute"])
    if not schedule or schedule[0]["minute"] != 0:
        schedule.insert(0, {"minute": 0, "rainfall_mmh": rainfall_mmh})
    if any(not 0 <= item["rainfall_mmh"] <= 120 or item["minute"] < 0 for item in schedule):
        raise ValueError("invalid rainfall schedule")
    network = load_network()
    drains = deepcopy(network["drains"])
    by_id = {d["id"]: d for d in drains}
    if cleaned_drain_id and cleaned_drain_id not in by_id:
        raise ValueError("unknown cleaned drain")
    assets = {a["id"]: a for a in network["assets"]}
    action_log = list(interventions or [])
    if cleaned_drain_id and not any(item["drain_id"] == cleaned_drain_id for item in action_log):
        action_log.append({"drain_id": cleaned_drain_id, "minute": cleaning_minute})
    if any(item["drain_id"] not in by_id or item["minute"] < 0 for item in action_log):
        raise ValueError("invalid intervention log")
    clean_times = {item["drain_id"]: item["minute"] for item in action_log}
    volumes = {d["id"]: d["storage_m3"] * 0.12 for d in drains}
    surface_water = {d["id"]: 0.0 for d in drains}
    overflow_total = {d["id"]: 0.0 for d in drains}
    first_overflow = {d["id"]: None for d in drains}
    latest_overflow = {d["id"]: None for d in drains}
    overflow_active = {d["id"]: False for d in drains}
    timeline: List[Dict[str, Any]] = []
    pending_routes = {d["id"]: 0.0 for d in drains}

    for minute in range(duration_minutes + 1):
        active_rainfall = next(item["rainfall_mmh"] for item in reversed(schedule) if item["minute"] <= minute)
        if minute > 0:
            next_routes = {d["id"]: 0.0 for d in drains}
            for drain in drains:
                numeric_id = int(drain["id"].split("-")[-1])
                drain_cleaning_minute = clean_times.get(drain["id"])
                if drain_cleaning_minute is not None and minute == drain_cleaning_minute:
                    drain["blockage"] = 0.08
                    volumes[drain["id"]] = min(volumes[drain["id"]], drain["storage_m3"] * 0.20)
                    surface_water[drain["id"]] = 0.0
                    overflow_active[drain["id"]] = False
                else:
                    # Prolonged rain carries leaves and litter toward different inlets.
                    sensitivity = 0.0075 + (numeric_id % 4) * 0.0015
                    drain["blockage"] = min(0.96, drain["blockage"] + sensitivity * active_rainfall / 60)
                    # Strong flow periodically shifts a leaf mat and briefly restores capacity.
                    flush_period = 79 + (numeric_id % 5) * 13
                    if minute > 0 and (minute + numeric_id * 11) % flush_period == 0:
                        drain["blockage"] = max(0.12, drain["blockage"] * 0.50)
                        volumes[drain["id"]] = min(volumes[drain["id"]], drain["storage_m3"] * 0.25)
                        surface_water[drain["id"]] = 0.0
                        overflow_active[drain["id"]] = False
                surface_water[drain["id"]] *= 0.94
                if surface_water[drain["id"]] < 0.12:
                    overflow_active[drain["id"]] = False
                # mm/h * m2 / 1000 / 60 gives cubic metres per minute.
                inflow = active_rainfall * drain["catchment_m2"] * drain["runoff"] / 60000
                inflow += pending_routes[drain["id"]]
                effective_capacity = drain["capacity_lps"] * (1 - drain["blockage"]) * 0.06
                volumes[drain["id"]] += inflow - min(effective_capacity, volumes[drain["id"]] + inflow)
                excess = max(0.0, volumes[drain["id"]] - drain["storage_m3"])
                if excess:
                    volumes[drain["id"]] = drain["storage_m3"]
                    surface_retained = excess * 0.62
                    overflow_total[drain["id"]] += surface_retained
                    surface_water[drain["id"]] += surface_retained
                    if not overflow_active[drain["id"]]:
                        latest_overflow[drain["id"]] = minute
                        overflow_active[drain["id"]] = True
                    if first_overflow[drain["id"]] is None:
                        first_overflow[drain["id"]] = minute
                    if drain["downstream"]:
                        next_routes[drain["downstream"]] += excess * 0.38
            pending_routes = next_routes

        snapshot = []
        for drain in drains:
            did = drain["id"]
            numeric_id = int(did.split("-")[-1])
            fill = min(1.0, volumes[did] / drain["storage_m3"])
            net_rate = active_rainfall * drain["catchment_m2"] * drain["runoff"] / 60000 - drain["capacity_lps"] * (1 - drain["blockage"]) * 0.06
            eta = None
            if not overflow_active[did] and net_rate > 0:
                eta = minute + max(1, round((drain["storage_m3"] - volumes[did]) / net_rate))
                if eta > duration_minutes:
                    eta = None
            state = {"id": did, "fill_pct": round(fill * 100, 1), "overflow_m3": round(surface_water[did], 2),
                     "cumulative_overflow_m3": round(overflow_total[did], 2),
                     "water_level_cm": round(fill * 55.0, 1), "sensor_packet": minute + 1,
                     "sensor_id": f"LVL-{numeric_id}",
                     "vision_blockage_pct": round(drain["blockage"] * 100),
                     "camera_id": f"CAM-{numeric_id}",
                     "vision_confidence_pct": round(max(82, min(98, 94 + (numeric_id % 4) - drain["blockage"] * 1.5 + 2.2 * math.sin((minute + numeric_id) / 7))), 1),
                     "camera_status": "restoring_connection" if minute > 0 and (minute + numeric_id * 3) % 25 >= 21 else "recording",
                     "minutes_to_overflow": None if overflow_active[did] else (eta - minute if eta is not None else None),
                     "overflow_at_minute": latest_overflow[did], "blockage_pct": round(drain["blockage"] * 100),
                     "effective_capacity_lps": round(drain["capacity_lps"] * (1 - drain["blockage"]), 1)}
            state["risk"] = _risk(fill, surface_water[did], state["minutes_to_overflow"])
            state["priority_score"] = _score(state, drain, assets)
            snapshot.append(state)
        live_top = max(snapshot, key=lambda item: item["priority_score"])
        live_drain = by_id[live_top["id"]]
        live_asset = assets.get(live_drain.get("asset"))
        timeline.append({"minute": minute, "rainfall_mmh": active_rainfall, "drains": snapshot,
                         "recommendation": {"drain_id": live_top["id"], "action": "Dispatch maintenance crew",
                         "reason": f"Clear {live_drain['name']} to protect {live_asset['name'] if live_asset else 'the downstream street'}.",
                         "priority_score": live_top["priority_score"], "requires_action": live_top["risk"] != "normal"}})

    final = timeline[-1]["drains"]
    ranked = sorted(final, key=lambda item: item["priority_score"], reverse=True)
    top = ranked[0]
    top_drain = by_id[top["id"]]
    asset = assets.get(top_drain.get("asset"))
    recommendation = {
        "drain_id": top["id"], "action": "Dispatch maintenance crew",
        "reason": f"Clear {top_drain['name']} to protect {asset['name'] if asset else 'the downstream street'}.",
        "priority_score": top["priority_score"],
        "requires_action": top["risk"] != "normal"
    }
    return {"scenario": {"rainfall_mmh": rainfall_mmh, "rainfall_schedule": schedule, "interventions": action_log, "duration_minutes": duration_minutes,
                          "cleaned_drain_id": cleaned_drain_id, "cleaning_minute": cleaning_minute},
            "network": {"meta": network["meta"], "map": network["map"], "drains": drains, "assets": network["assets"]},
            "timeline": timeline, "recommendation": recommendation,
            "summary": {"total_overflow_m3": round(sum(overflow_total.values()), 2),
                        "first_overflow": next((dict(x, overflow_at_minute=first_overflow[x["id"]]) for x in final if first_overflow[x["id"]] == min((v for v in first_overflow.values() if v is not None), default=-1)), None)}}


def compare(rainfall_mmh: float, drain_id: str, cleaning_minute: int = 18, duration_minutes: int = 90,
            rainfall_schedule: Optional[List[Dict[str, float]]] = None,
            interventions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    previous_actions = list(interventions or [])
    next_actions = [item for item in previous_actions if item["drain_id"] != drain_id]
    next_actions.append({"drain_id": drain_id, "minute": cleaning_minute})
    baseline = simulate(rainfall_mmh, duration_minutes, rainfall_schedule=rainfall_schedule, interventions=previous_actions)
    intervention = simulate(rainfall_mmh, duration_minutes, rainfall_schedule=rainfall_schedule, interventions=next_actions)
    before = baseline["summary"]["total_overflow_m3"]
    after = intervention["summary"]["total_overflow_m3"]
    return {"baseline": baseline, "intervention": intervention,
            "impact": {"prevented_overflow_m3": round(max(0, before - after), 2),
                       "reduction_pct": round(100 * max(0, before - after) / before, 1) if before else 0,
                       "protected_asset": next((a["name"] for d in baseline["network"]["drains"] if d["id"] == drain_id for a in baseline["network"]["assets"] if a["id"] == d.get("asset")), None)}}
