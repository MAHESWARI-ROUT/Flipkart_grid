import joblib, json, os
import numpy as np
from datetime import datetime

_m = {}   # model registry


# LOAD
def load_models(model_dir: str = "./models"):
    _m["closure"]          = joblib.load(f"{model_dir}/closure_model.pkl")
    _m["encoders"]         = joblib.load(f"{model_dir}/encoders.pkl")
    _m["junction_freq"]    = joblib.load(f"{model_dir}/junction_freq_map.pkl")
    _m["corridor_freq"]    = joblib.load(f"{model_dir}/corridor_freq_map.pkl")
    _m["cluster_centers"]  = joblib.load(f"{model_dir}/cluster_centers.pkl")
    _m["cluster_density"]  = joblib.load(f"{model_dir}/cluster_density_map.pkl")
    _m["cause_severity"]   = joblib.load(f"{model_dir}/cause_severity.pkl")
    _m["cause_model"]      = joblib.load(f"{model_dir}/cause_model.pkl")
    _m["cause_features"]   = joblib.load(f"{model_dir}/cause_features.pkl")
    _m["closure_features"] = joblib.load(f"{model_dir}/closure_features.pkl")
    with open(f"{model_dir}/hotspots.json") as f:
        _m["hotspots"] = json.load(f)
    with open(f"{model_dir}/resource_table.json") as f:
        _m["resource_table"] = json.load(f)
    print("✅ All models loaded")


# HELPERS
def _enc(col: str, val: str) -> int:
    le = _m["encoders"][col]
    v  = val if val in le.classes_ else le.classes_[0]
    return int(le.transform([v])[0])


def _get_nearest_cluster(lat: float, lon: float) -> int:
    best, best_d = None, float("inf")
    for cid, center in _m["cluster_centers"].items():
        d = (lat - center["lat"])**2 + (lon - center["lon"])**2
        if d < best_d:
            best_d, best = d, cid
    return best


# IMPACT SCORE — domain-expert formula (same as training)
def _impact_score(cause_severity: int, road_closure: bool,
                  is_major: int, is_peak: int) -> float:
    score = (
        cause_severity * 5
        + int(road_closure) * 20
        + is_major * 10
        + is_peak * 5
    )
    return float(min(max(score, 0), 100))


# PRIORITY — rule-based (explainable, no leaking model)
def _priority_rule(impact: float, cause: str,
                   is_major: int, road_closure: bool) -> tuple:
    HIGH_CAUSES = {"accident", "rare_event", "public_event", "procession"}
    if road_closure and is_major:
        return "High", 92.0
    if cause in HIGH_CAUSES and is_major:
        return "High", 85.0
    if impact >= 50:
        conf = min(50 + (impact - 50) * 1.5, 95)
        return "High", round(conf, 1)
    conf = max(5, 50 - (50 - impact) * 1.2)
    return "Low", round(conf, 1)


# RESOURCE RECOMMENDATION
RESOURCE_TABLE_DEFAULT = {
    "accident":          (4, 2, True),
    "rare_event":        (5, 3, True),
    "public_event":      (5, 3, True),
    "procession":        (4, 3, True),
    "vehicle_breakdown": (2, 1, False),
    "construction":      (3, 2, True),
    "water_logging":     (2, 2, False),
    "congestion":        (3, 1, False),
    "tree_fall":         (3, 2, True),
    "road_conditions":   (2, 1, False),
    "pot_holes":         (1, 1, False),
    "others":            (2, 1, False),
}

# NEW: Attendance buckets → (impact_points, resource_multiplier, label)
ATTENDANCE_TABLE = {
    "lt_500":     {"points": 0,  "mult": 1.0,  "label": "Less than 500"},
    "500_2000":   {"points": 8,  "mult": 1.15, "label": "500 - 2,000"},
    "2000_5000":  {"points": 15, "mult": 1.35, "label": "2,000 - 5,000"},
    "5000_10000": {"points": 22, "mult": 1.6,  "label": "5,000 - 10,000"},
    "gt_10000":   {"points": 30, "mult": 2.0,  "label": "10,000+"},
}

def _attendance_info(expected_attendance: str) -> dict:
    return ATTENDANCE_TABLE.get(
        str(expected_attendance), ATTENDANCE_TABLE["lt_500"]
    )


def _recommend(cause: str, impact: float, road_closure: bool,
               is_peak: int, is_major: int,
               attendance_mult: float = 1.0) -> dict:
    rt = _m.get("resource_table", {})
    base = rt.get(cause, None)
    if base:
        officers, barricades, diversion = base[0], base[1], base[2]
    else:
        officers, barricades, diversion = RESOURCE_TABLE_DEFAULT.get(
            cause, (2, 1, False))

    mult = 1.0
    if impact >= 75:   mult = 2.0
    elif impact >= 50: mult = 1.5
    elif impact >= 25: mult = 1.2
    if is_peak:        mult += 0.3
    if is_major:       mult += 0.2
    if road_closure:   mult += 0.5

    # Crowd-size scaling stacks multiplicatively
    mult *= attendance_mult

    import math
    return {
        "officers_needed":   math.ceil(officers   * mult),
        "barricades_needed": math.ceil(barricades * mult),
        "diversion_needed":  bool(diversion or road_closure),
    }


def _actions(cause: str, severity: str, road_closure: bool,
             attendance_key: str = "lt_500") -> list:
    a = []
    if severity in ("CRITICAL", "HIGH"):
        a.append("Dispatch officers immediately")
    if road_closure:
        a.append("Activate diversion plan")
        a.append("Alert adjacent signal controllers")
    if cause == "accident":
        a.append("Alert ambulance and fire services")
    if cause in ("public_event", "procession", "rare_event"):
        a.append("Coordinate with event organizers")
        a.append("Pre-position officers at entry/exit points")
    if cause == "vehicle_breakdown":
        a.append("Dispatch tow vehicle")
    if cause in ("tree_fall",):
        a.append("Alert BBMP clearance team")
    if cause == "water_logging":
        a.append("Alert BBMP drainage team")
    if cause == "construction":
        a.append("Verify work permit and enforce timeline")
    # NEW: crowd-specific actions
    if attendance_key in ("5000_10000", "gt_10000"):
        a.append("Request additional traffic police battalion")
        a.append("Set up barricaded pedestrian corridors")
    elif attendance_key == "2000_5000":
        a.append("Deploy extra barricades at entry/exit points")
    return a


def _generate_diversion_plan(corridor, junction, severity,
                              road_closure, congestion_risk):
    plans = []
    if road_closure:
        plans.append(f"Divert traffic away from {junction}")
        plans.append("Activate nearby service roads")
        plans.append("Deploy temporary barricades")
    if congestion_risk >= 60:
        plans.append("Use alternate ORR route")
        plans.append("Optimize nearby traffic signals")
    if severity in ("HIGH", "CRITICAL"):
        plans.append("Deploy additional traffic officers")
        plans.append("Broadcast traffic advisory")
    if corridor:
        plans.append(f"Monitor traffic flow on {corridor}")
    return plans


# MAIN PREDICT FUNCTION
def predict(data: dict) -> dict:

    now      = datetime.now()
    cause    = str(data.get("event_cause", "others")).lower().strip()
    etype    = str(data.get("event_type", "unplanned"))
    corridor = str(data.get("corridor", "Non-corridor"))
    zone     = str(data.get("zone", "Unknown"))
    junction = str(data.get("junction", "Unknown"))
    hour     = int(data.get("hour") or now.hour)

    minute = (
        int(data["minute"])
        if data.get("minute") is not None
        else now.minute
    )
    month = (
        int(data["month"])
        if data.get("month") is not None
        else now.month
    )

    lat     = float(data.get("latitude",  12.97))
    lon     = float(data.get("longitude", 77.59))
    rc      = bool(data.get("requires_road_closure", False))
    dow     = now.weekday()
    is_wknd = int(dow >= 5)

    # NEW: Expected attendance bucket (crowd-size signal)
    attendance_key   = str(data.get("expected_attendance", "lt_500"))
    attendance_info  = _attendance_info(attendance_key)
    attendance_points = attendance_info["points"]
    attendance_mult  = attendance_info["mult"]
    attendance_label = attendance_info["label"]

    # Derived flags
    is_peak  = int(hour in [7, 8, 9, 17, 18, 19, 20, 21])
    is_night = int(hour in [22, 23, 0, 1, 2, 3, 4, 5])
    is_major = int(corridor not in ("Non-corridor", "Unknown", ""))

    # Cause severity (from saved map, same as training)
    sev = _m["cause_severity"].get(cause, 3)

    # Frequency features (same logic as training)
    jf = _m["junction_freq"].get(junction,
         float(np.mean(list(_m["junction_freq"].values()))))
    cf = _m["corridor_freq"].get(corridor,
         float(np.mean(list(_m["corridor_freq"].values()))))

    # Hotspot density via nearest cluster
    nearest = _get_nearest_cluster(lat, lon)
    hd      = _m["cluster_density"].get(nearest,
              float(np.mean(list(_m["cluster_density"].values()))))

    # Encode categoricals
    enc_cause    = _enc("event_cause", cause)
    enc_type     = _enc("event_type",  etype)
    enc_corridor = _enc("corridor",    corridor)
    enc_zone     = _enc("zone",        zone)
    enc_junction = _enc("junction",    junction)

    # Model B: Road Closure (ML)
    closure_row = np.array([[
        enc_cause, enc_type, hour, minute, dow, month,
        is_wknd, is_peak, is_night, is_major,
        enc_corridor, enc_zone, sev,
        enc_junction, jf, cf, hd
    ]])
    assert closure_row.shape[1] == _m["closure"].n_features_in_, (
        f"Feature mismatch: expected {_m['closure'].n_features_in_}, "
        f"got {closure_row.shape[1]}"
    )
    closure_prob = float(_m["closure"].predict_proba(closure_row)[0][1])
    closure_pred = bool(closure_prob > 0.30)

    # Impact Score — now includes attendance points
    base_impact = _impact_score(sev, closure_pred or rc, is_major, is_peak)
    impact = float(min(max(base_impact + attendance_points, 0), 100))

    # Priority (rule-based)
    priority_label, priority_conf = _priority_rule(
        impact, cause, is_major, closure_pred or rc)

    # Severity bucket
    if impact >= 75:   severity = "CRITICAL"
    elif impact >= 50: severity = "HIGH"
    elif impact >= 25: severity = "MEDIUM"
    else:              severity = "LOW"

    # Resources — scaled by attendance_mult
    res = _recommend(cause, impact, closure_pred or rc, is_peak, is_major,
                     attendance_mult=attendance_mult)

    # Congestion risk — attendance-aware
    congestion_risk = min(
        0.4 * impact + 20 * is_peak + 15 * is_major
        + 10 * int(closure_pred or rc) + 0.3 * attendance_points,
        100
    )

    # Diversion plan
    diversion_plan = _generate_diversion_plan(
        corridor, junction, severity, closure_pred or rc, congestion_risk)

    # Prediction drivers
    cause_display = cause.replace("_", " ").title()
    drivers = [{"name": f"{cause_display} Incident Severity", "score": sev * 5}]
    if closure_pred or rc:
        drivers.append({"name": "Road Closure",         "score": 20})
    if is_major:
        drivers.append({"name": "Major Traffic Corridor", "score": 10})
    if is_peak:
        drivers.append({"name": "Peak Hour",             "score": 5})
    if attendance_points > 0:
        drivers.append({"name": "Expected Attendance",   "score": attendance_points})
    drivers = sorted(drivers, key=lambda x: x["score"], reverse=True)

    # Impact contributors breakdown (for explainability panel)
    impact_contributors = [
        {"label": "Cause Severity", "points": round(sev * 5, 1)},
        {"label": "Road Closure",   "points": 20 if (closure_pred or rc) else 0},
        {"label": "Major Corridor", "points": 10 if is_major else 0},
        {"label": "Peak Hour",      "points": 5  if is_peak  else 0},
        {"label": "Attendance",     "points": attendance_points},
    ]
    impact_contributors = sorted(
        [c for c in impact_contributors if c["points"] > 0],
        key=lambda c: c["points"], reverse=True
    )

    # Explanation text
    explanation = []
    if closure_pred or rc:
        explanation.append("road closure")
    if is_major:
        explanation.append("major traffic corridor")
    if is_peak:
        explanation.append("peak-hour traffic")
    if sev >= 5:
        explanation.append("high incident severity")
    if attendance_points >= 15:
        explanation.append("large expected attendance")

    if explanation:
        explanation_text = (
            "High impact driven by "
            + ", ".join(explanation[:-1])
            + (" and " + explanation[-1] if len(explanation) > 1 else explanation[0])
            + "."
        )
    else:
        explanation_text = "Moderate traffic impact expected."

    return {
        # Core predictions
        "impact_score":               round(impact, 1),
        "severity":                   severity,
        "congestion_risk":            round(congestion_risk, 1),
        "priority":                   priority_label,
        "priority_confidence":        priority_conf,
        # Road closure (ML model B)
        "road_closure_risk":          "Yes" if closure_pred else "No",
        "road_closure_probability":   round(closure_prob * 100, 2),
        # Resources
        **res,
        # SLA
        "response_sla_mins":          {"CRITICAL":5,"HIGH":10,"MEDIUM":20,"LOW":30}[severity],
        "estimated_delay_mins":       {"CRITICAL":30,"HIGH":20,"MEDIUM":10,"LOW":5}[severity],
        "vehicles_affected_est":      int(impact * 85),
        # Actions
        "actions":                    _actions(cause, severity, closure_pred or rc, attendance_key),
        "diversion_plan":             diversion_plan,
        # Spatial intelligence
        "junction_freq":              round(float(jf), 4),
        "corridor_freq":              round(float(cf), 4),
        "hotspot_density":            round(float(hd), 4),
        # Drivers & explanation
        "prediction_drivers":         drivers,
        "prediction_explanation":     explanation_text,
        # NEW — attendance impact details
        "expected_attendance":        attendance_key,
        "expected_attendance_label":  attendance_label,
        "attendance_impact_points":   attendance_points,
        "attendance_resource_mult":   attendance_mult,
        "impact_contributors":        impact_contributors,
    }


# ANALYTICS (pre-computed from training data)
ANALYTICS = {
    "total_incidents":     8173,
    "high_priority_count": 5030,
    "high_priority_pct":   61.5,
    "road_closure_count":  676,
    "road_closure_pct":    8.3,
    "hotspot_clusters":    92,
    "corridors_monitored": 22,
    "junctions_covered":   294,
    "avg_congestion_risk": 36.88,
    "critical_events":     59,
    "model_b_auc":         0.7507,
    "model_d_accuracy":    0.71,
    "top_causes": [
        {"cause":"vehicle_breakdown","count":4896},
        {"cause":"others",           "count":640},
        {"cause":"pot_holes",        "count":537},
        {"cause":"construction",     "count":480},
        {"cause":"water_logging",    "count":458},
        {"cause":"accident",         "count":365},
        {"cause":"tree_fall",        "count":284},
    ],
    "hourly_distribution": {
        "0":534,"1":381,"2":387,"3":372,"4":558,"5":661,"6":660,
        "7":480,"8":327,"9":160,"10":68,"11":68,"12":63,"13":33,
        "14":13,"15":9,"16":9,"17":34,"18":228,"19":578,"20":681,
        "21":810,"22":564,"23":495
    },
    "top_junctions": [
        {"junction":"MekhriCircle",          "count":64},
        {"junction":"AyyappaTempleJunc",      "count":49},
        {"junction":"SatteliteBusStandJunc",  "count":43},
        {"junction":"YeshwanthpuraCircle",    "count":38},
        {"junction":"YelhankaCircle",         "count":34},
        {"junction":"SilkBoardJunc",          "count":33},
        {"junction":"toll gate mysore road",  "count":33},
        {"junction":"Nagavara-ORR Junction",  "count":32},
    ],
    "top_corridors": [
        {"corridor":"Mysore Road",     "count":743, "risk":46.9},
        {"corridor":"Bellary Road 1",  "count":610, "risk":46.1},
        {"corridor":"Tumkur Road",     "count":458, "risk":46.0},
        {"corridor":"Bellary Road 2",  "count":379, "risk":47.2},
        {"corridor":"Hosur Road",      "count":298, "risk":46.6},
        {"corridor":"ORR North 1",     "count":275, "risk":46.2},
        {"corridor":"ORR East 1",      "count":244, "risk":48.1},
        {"corridor":"ORR East 2",      "count":187, "risk":52.2},
    ],
    "cause_impact": {
        "public_event":51.4,"rare_event":50.2,"accident":47.8,
        "construction":45.1,"tree_fall":41.2,"congestion":40.3,
        "water_logging":38.9,"vehicle_breakdown":38.1,
        "road_conditions":32.4,"pot_holes":26.1,"others":25.8,
    }
}

def get_analytics() -> dict:
    return ANALYTICS