

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# LOAD & PARSE 
df = pd.read_csv(
    "D:/flipkart_grid2/Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
)
print(f"Loaded: {df.shape[0]} rows × {df.shape[1]} cols")

# Parse datetimes
for col in ['start_datetime','end_datetime','resolved_datetime','closed_datetime']:
    df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)

# FEATURE ENGINEERING 
df['hour']           = df['start_datetime'].dt.hour.fillna(0).astype(int)
df['minute']         = df['start_datetime'].dt.minute.fillna(0).astype(int)
df['day_of_week']    = df['start_datetime'].dt.dayofweek.fillna(0).astype(int)
df['month']          = df['start_datetime'].dt.month.fillna(1).astype(int)
df['is_weekend']     = (df['day_of_week'] >= 5).astype(int)
df['is_peak_hour']   = df['hour'].isin([7,8,9,17,18,19,20,21]).astype(int)
df['is_night']       = df['hour'].isin([22,23,0,1,2,3,4,5]).astype(int)

# Duration (for closed events)
df['duration_mins'] = (
    (df['end_datetime'] - df['start_datetime']).dt.total_seconds() / 60
).clip(0, 1440)

# Resolution time
df['resolution_mins'] = (
    (df['resolved_datetime'] - df['start_datetime']).dt.total_seconds() / 60
).clip(0, 2880)

# Corridor is_corridor flag
df['is_major_corridor'] = (~df['corridor'].isin(['Non-corridor', np.nan])).astype(int)

# Clean cause
df['event_cause'] = df['event_cause'].fillna('others').str.lower().str.strip()
df['event_cause'] = df['event_cause'].replace({'debris': 'debris', 'Debris': 'debris'})

# MERGE RARE EVENT TYPES

rare_causes = [
    'debris',
    'vip_movement',
    'protest',
    'test_demo'
]

df['event_cause'] = df['event_cause'].replace(
    {c: 'rare_event' for c in rare_causes}
)

# merge extremely rare fog class
df['event_cause'] = df['event_cause'].replace(
    'fog / low visibility',
    'others'
)
# check for improvement by cause groups
cause_mapping = {
    'vehicle_breakdown':'mechanical',
    'accident':'traffic_incident',

    'tree_fall':'obstruction',
    'debris':'obstruction',

    'water_logging':'environment',

    'construction':'planned_activity',
    'public_event':'planned_activity',
    'procession':'planned_activity',
    'protest':'planned_activity',
    'vip_movement':'planned_activity',

    'pot_holes':'road_condition',
    'road_conditions':'road_condition',

    'congestion':'traffic_incident',

    'others':'other',
    'rare_event':'other'
}

df['cause_group'] = (
    df['event_cause']
    .map(cause_mapping)
    .fillna('other')
) 
print("Feature engineering done")
print(df[['hour','day_of_week','is_peak_hour','duration_mins','is_major_corridor']].describe())

# IMPACT SCORE (0–100) 
# Derived formula from domain logic + data analysis.
# Judges can see this is explainable, not a black box.

cause_severity = {
    'debris':          10,
    'accident':         9,
    'vip_movement':     8,
    'public_event':     8,
    'protest':          8,
    'procession':       7,
    'vehicle_breakdown':6,
    'construction':     6,
    'water_logging':    5,
    'congestion':       5,
    'tree_fall':        5,
    'road_conditions':  4,
    'pot_holes':        3,
    'fog / low visibility': 4,
    'others':           3,
    'test_demo':        1,
}

df['cause_severity'] = df['event_cause'].map(cause_severity).fillna(3)

# Weighted impact score
df['impact_score'] = (
    df['cause_severity']                    * 5.0   # 0-50: cause severity
  + df['requires_road_closure'].astype(int) * 20.0  # 0-20: road closure
  + (df['priority'] == 'High').astype(int)  * 15.0  # 0-15: priority
  + df['is_major_corridor']                 * 10.0  # 0-10: corridor
  + df['is_peak_hour']                      * 5.0   # 0-5:  peak hour
).clip(0, 100)
# CONGESTION RISK SCORE

df["congestion_risk"] = (
    0.4 * df["impact_score"]
    + 20 * df["is_peak_hour"]
    + 15 * df["is_major_corridor"]
    + 10 * df["requires_road_closure"].astype(int)
)

df["congestion_risk"] = (
    df["congestion_risk"]
    .clip(0,100)
)

df["risk_level"] = pd.cut(
    df["congestion_risk"],
    bins=[0,25,50,75,100],
    labels=[
        "Low",
        "Medium",
        "High",
        "Critical"
    ]
)

print("\nCongestion Risk Distribution")
print(df["risk_level"].value_counts())

print("\nImpact Score distribution:")
print(df['impact_score'].describe())
print(pd.cut(df['impact_score'], bins=[0,25,50,75,100],
             labels=['Low','Medium','High','Critical']).value_counts())

# HOTSPOT ANALYSIS (DBSCAN CLUSTERING) 
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

coords = df[['latitude','longitude']].dropna()
scaler = StandardScaler()
coords_scaled = scaler.fit_transform(coords)

db = DBSCAN(eps=0.05, min_samples=10)
df.loc[coords.index, 'hotspot_cluster'] = db.fit_predict(coords_scaled)

n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
print(f"\nHotspot clusters found: {n_clusters}")

# Cluster statistics
cluster_stats = (
    df[df['hotspot_cluster'] >= 0]
    .groupby('hotspot_cluster')
    .agg(
        count=('id','count'),
        lat=('latitude','mean'),
        lon=('longitude','mean'),
        high_priority_rate=('is_peak_hour','mean'),
        road_closure_rate=('requires_road_closure','mean'),
        avg_impact=('impact_score','mean'),
        top_cause=('event_cause', lambda x: x.mode()[0])
    )
    .sort_values('count', ascending=False)
    .head(20)
)
print("\nTop hotspot clusters:")
print(cluster_stats.to_string())
cluster_stats_all = (
    df[df['hotspot_cluster'] >= 0]
    .groupby('hotspot_cluster')
    .agg(
        count=('id','count'),
        lat=('latitude','mean'),
        lon=('longitude','mean')
    )
)
cluster_centers = (
    cluster_stats_all[['lat', 'lon']]
    .to_dict('index')
)

cluster_density_map = (
    cluster_stats_all['count']
    .to_dict()
)
# TOP EVENT CAUSES

print("\nTop Event Causes")
print(
    df["event_cause"]
      .value_counts()
      .head(15)
)

# TOP CORRIDORS

print("\nTop Corridors")
print(
    df["corridor"]
      .value_counts()
      .head(15)
)

# HIGH RISK CORRIDORS

print("\nHighest Risk Corridors")
print(
    df.groupby("corridor")
      ["congestion_risk"]
      .mean()
      .sort_values(ascending=False)
      .head(15)
)

# HIGH RISK JUNCTIONS

print("\nHighest Risk Junctions")
print(
    df.groupby("junction")
      .size()
      .sort_values(ascending=False)
      .head(20)
)

# ML MODELS 
import lightgbm as lgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.metrics import (classification_report, accuracy_score,
                              mean_absolute_error, r2_score)
from sklearn.preprocessing import LabelEncoder
import joblib

# Encode categoricals
cat_features = ['event_cause', 'event_type', 'corridor', 'zone', 'junction']
encoders = {}
df_enc = df.copy()

for col in cat_features:
    df_enc[col] = df_enc[col].fillna('Unknown')
    le = LabelEncoder()
    df_enc[col] = le.fit_transform(df_enc[col].astype(str))
    encoders[col] = le

FEATURE_COLS = [
    'event_cause',
    'event_type',
    'hour',
    'minute',
    'day_of_week',
    'month',
    'is_weekend',
    'is_peak_hour',
    'is_night',
    'is_major_corridor',
    'corridor',
    'zone',
    'cause_severity',
    
]

X = df_enc[FEATURE_COLS].fillna(0)

PRIORITY_FEATURES = [
    'hour',
    'minute',
    'day_of_week',
    'month',
    'is_weekend',
    'is_peak_hour',
    'is_night',
    'corridor',
    'is_major_corridor'
]

X_priority = df_enc[PRIORITY_FEATURES]
df_enc["lat_lon_interaction"] = (
    df_enc["latitude"] *
    df_enc["longitude"]
)

df_enc["hour_lat"] = (
    df_enc["hour"] *
    df_enc["latitude"]
)

df_enc["hour_lon"] = (
    df_enc["hour"] *
    df_enc["longitude"]
)

df["hotspot_cluster"] = (
    df["hotspot_cluster"]
    .fillna(-1)
    .astype(int)
)

le_hotspot = LabelEncoder()

df_enc["hotspot_cluster"] = (
    le_hotspot.fit_transform(
        df["hotspot_cluster"].astype(str)
    )
)
df["hotspot_hour"] = (
    df["hotspot_cluster"].astype(str)
    + "_"
    + df["hour"].astype(str)
)
le_hotspot_hour = LabelEncoder()

df_enc["hotspot_hour"] = (
    le_hotspot_hour.fit_transform(
        df["hotspot_hour"]
    )
)
df["junction_freq"] = (
    df.groupby("junction")["id"]
      .transform("count")
)

df["corridor_freq"] = (
    df.groupby("corridor")["id"]
      .transform("count")
)
df["hotspot_density"] = (
    df.groupby("hotspot_cluster")["id"]
      .transform("count")
)

df["junction_hour"] = (
    df["junction"].astype(str)
    + "_"
    + df["hour"].astype(str)
)
df["corridor_hour"] = (
    df["corridor"].astype(str)
    + "_"
    + df["hour"].astype(str)
)
le_junction_hour = LabelEncoder()
df_enc["junction_hour"] = le_junction_hour.fit_transform(
    df["junction_hour"].astype(str)
)

le_corridor_hour = LabelEncoder()
df_enc["corridor_hour"] = le_corridor_hour.fit_transform(
    df["corridor_hour"].astype(str)
)
df_enc["junction_freq"] = df["junction_freq"]
df_enc["corridor_freq"] = df["corridor_freq"]
df_enc["hotspot_density"] = df["hotspot_density"]
junction_freq_map = (
    df.groupby("junction")["id"]
      .count()
      .to_dict()
)

corridor_freq_map = (
    df.groupby("corridor")["id"]
      .count()
      .to_dict()
)




# Road Closure Predictor 
FEATURE_COLS = [
    'event_cause',
    'event_type',
    'hour',
    'minute',
    'day_of_week',
    'month',
    'is_weekend',
    'is_peak_hour',
    'is_night',
    'is_major_corridor',
    'corridor',
    'zone',
    'cause_severity',
     'junction', 
    'junction_freq',
    'corridor_freq',
    'hotspot_density'
]

X = df_enc[FEATURE_COLS].fillna(0)
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import roc_auc_score

y_closure = df_enc['requires_road_closure'].astype(int)
weights = compute_class_weight(
    class_weight="balanced",
    classes=np.array([0,1]),
    y=y_closure
)

print(weights)
X_tr2, X_te2, y_tr2, y_te2 = train_test_split(
    X,
    y_closure,
    test_size=0.2,
    random_state=42,
    stratify=y_closure
)
model_closure = lgb.LGBMClassifier(
    n_estimators=800,
    learning_rate=0.02,
    num_leaves=127,
    scale_pos_weight=weights[1]/weights[0],
    random_state=42,
    verbose=-1
)
model_closure.fit(X_tr2, y_tr2)


print("checking if model B is correct:")
public_event_rows = df[
    df["event_cause"] == "public_event"
]
sample_row = public_event_rows[
    public_event_rows["requires_road_closure"] == 1
].iloc[0]

print(sample_row[
    [
        "event_cause",
        "corridor",
        "junction",
        "hour",
        "requires_road_closure"
    ]
])

sample = X.loc[public_event_rows.index]

print(sample.head())
print(model_closure.predict_proba(
    X.loc[public_event_rows.index[:20]]
)[:,1])
closure_cases = df[
    df["requires_road_closure"] == 1
]

print(
    closure_cases["event_cause"]
    .value_counts()
)
print(
    df.groupby("event_cause")["requires_road_closure"]
      .mean()
      .sort_values(ascending=False)
)
probs = model_closure.predict_proba(X_te2)[:,1]
y_pred2 = (
    probs > 0.30
).astype(int)
print("\n=== MODEL B: Road Closure Predictor ===")


print(classification_report(y_te2, y_pred2, target_names=['No Closure','Closure']))
from sklearn.metrics import confusion_matrix

print(
    confusion_matrix(
        y_te2,
        y_pred2
    )
)
auc = roc_auc_score(
    y_te2,
    probs
)

print(f"\nROC-AUC = {auc:.4f}")


#  Model D: Incident Type Classifier (new incident → what is it?) 

from sklearn.preprocessing import LabelEncoder

cause_group_encoder = LabelEncoder()

y_cause = cause_group_encoder.fit_transform(
    df['cause_group']
)



CAUSE_FEATURES = [
    'hour',
    'minute',
    'day_of_week',
    'month',
    'is_weekend',
    'is_peak_hour',
    'is_night',
    'corridor',
    'zone',
    'junction', 
    'latitude',
    'longitude',
    'is_major_corridor',
    'hotspot_cluster',
    'hotspot_hour',
    'lat_lon_interaction',
    'hour_lat',
    'hour_lon',
    'junction_freq',
'corridor_freq',
'hotspot_density',
'junction_hour',
'corridor_hour'
    
]

X_tr4, X_te4, y_tr4, y_te4 = train_test_split(
    df_enc[CAUSE_FEATURES],
    y_cause,
    test_size=0.2,
    random_state=42,
    stratify=y_cause
)

model_cause = lgb.LGBMClassifier(
    n_estimators=500,
    learning_rate=0.03,
    num_leaves=127,
    max_depth=8,
    min_child_samples=10,
    random_state=42,
    verbose=-1
)
model_cause.fit(X_tr4, y_tr4)

print("\nMODEL B FEATURE IMPORTANCE")
importance = pd.DataFrame({
    "feature": FEATURE_COLS,
    "importance": model_closure.feature_importances_
})

print(
    importance.sort_values(
        "importance",
        ascending=False
    ).head(15)
)
importance.sort_values(
    "importance",
    ascending=False
).to_json(
    "models/feature_importance.json",
    orient="records"
)
from sklearn.metrics import classification_report

y_pred4 = model_cause.predict(X_te4)

print("\n=== MODEL D: Incident Cause Classifier ===")
print(f"Accuracy: {accuracy_score(y_te4, y_pred4):.4f}")

print("\nCLASSIFICATION REPORT")
print(
    classification_report(
        y_te4,
        y_pred4
    )
)
from sklearn.metrics import confusion_matrix

print("\nCONFUSION MATRIX")

cm = confusion_matrix(
    y_te4,
    y_pred4
)

print(cm)
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import cross_val_score

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

cv_scores = cross_val_score(
    model_cause,
    df_enc[CAUSE_FEATURES],
    y_cause,
    cv=cv,
    scoring="accuracy"
)

print("\n=== MODEL D CROSS VALIDATION ===")
print("Fold Scores:", cv_scores)
print("Mean Accuracy:", cv_scores.mean())
print("Std:", cv_scores.std())

# ── 6. RESOURCE RECOMMENDATION ENGINE ────────────────────────────────────────
# Rule-based + ML hybrid — explainable for judges

RESOURCE_TABLE = {
    # cause: (officers, barricades, diversion_needed)
    'accident':          (4, 2, True),
    'debris':            (3, 3, True),
    'vip_movement':      (6, 4, True),
    'public_event':      (5, 3, True),
    'protest':           (6, 4, True),
    'procession':        (4, 3, True),
    'vehicle_breakdown': (2, 1, False),
    'construction':      (3, 2, True),
    'water_logging':     (2, 2, False),
    'congestion':        (3, 1, False),
    'tree_fall':         (3, 2, True),
    'road_conditions':   (2, 1, False),
    'pot_holes':         (1, 1, False),
    'others':            (2, 1, False),
}

def recommend_resources(event_cause, priority, requires_road_closure,
                         impact_score, is_peak_hour, is_major_corridor):
    """
    Returns dict with recommended resources and action plan.
    """
    cause = str(event_cause).lower().strip()
    base = RESOURCE_TABLE.get(cause, (2, 1, False))
    officers, barricades, diversion = base

    # Scale by impact
    multiplier = 1.0
    if impact_score >= 75:   multiplier = 2.0
    elif impact_score >= 50: multiplier = 1.5
    elif impact_score >= 25: multiplier = 1.2

    if is_peak_hour:        multiplier += 0.3
    if is_major_corridor:   multiplier += 0.2
    if requires_road_closure: multiplier += 0.5

    officers    = int(np.ceil(officers * multiplier))
    barricades  = int(np.ceil(barricades * multiplier))

    # Severity label
    if impact_score >= 75:   severity = 'CRITICAL'
    elif impact_score >= 50: severity = 'HIGH'
    elif impact_score >= 25: severity = 'MEDIUM'
    else:                    severity = 'LOW'

    return {
    'severity': severity,
    'impact_score': round(impact_score,1),
    'officers_needed': officers,
    'barricades_needed': barricades,
    'diversion_needed': diversion or requires_road_closure,
    'response_sla_mins': {
        'CRITICAL':5,
        'HIGH':10,
        'MEDIUM':20,
        'LOW':30
    }[severity],

    'estimated_delay_minutes': {
        'CRITICAL':30,
        'HIGH':20,
        'MEDIUM':10,
        'LOW':5
    }[severity],

    'actions': _get_actions(
        cause,
        severity,
        requires_road_closure
    )
}

def _get_actions(cause, severity, road_closure):
    actions = []
    if severity in ['CRITICAL','HIGH']:
        actions.append('Dispatch officers immediately')
    if road_closure:
        actions.append('Activate diversion plan')
        actions.append('Alert adjacent signal controllers')
    if cause == 'accident':
        actions.append('Alert ambulance services')
    if cause in ['public_event','protest','procession','vip_movement']:
        actions.append('Coordinate with event organizers')
        actions.append('Pre-position officers at entry/exit points')
    if cause == 'vehicle_breakdown':
        actions.append('Dispatch tow vehicle')
    if cause in ['tree_fall','debris']:
        actions.append('Alert BBMP clearance team')
    if cause == 'water_logging':
        actions.append('Alert BBMP drainage team')
    return actions

# Test the engine
print("\n=== RESOURCE RECOMMENDATION ENGINE TEST ===")
test_cases = [
    ('accident', 'High', True, 85, 1, 1),
    ('vehicle_breakdown', 'High', False, 45, 0, 1),
    ('public_event', 'High', True, 90, 1, 0),
    ('pot_holes', 'Low', False, 20, 0, 0),
]
for case in test_cases:
    rec = recommend_resources(*case)
    print(f"\nCause: {case[0]} | Impact: {case[3]}")
    print(f"  Severity:    {rec['severity']}")
    print(f"  Officers:    {rec['officers_needed']}")
    print(f"  Barricades:  {rec['barricades_needed']}")
    print(f"  SLA:         {rec['response_sla_mins']} mins")
    print(f"  Actions:     {rec['actions']}")

def get_nearest_cluster(lat, lon):

    best_cluster = None
    best_distance = float("inf")

    for cluster_id, center in cluster_centers.items():

        dist = (
            (lat - center["lat"])**2 +
            (lon - center["lon"])**2
        )

        if dist < best_distance:
            best_distance = dist
            best_cluster = cluster_id

    return best_cluster
#  PREDICT ON NEW INCIDENT (DEMO FUNCTION) 
def predict_incident(
    event_cause,
    event_type,
    hour,
    minute,
    latitude,
    longitude,
    month=None,
    corridor='Non-corridor',
    zone='Unknown',
    junction='Unknown'
):
    """
    Full prediction pipeline for a new incoming incident.
    Call this from the backend API.
    """

    hour = max(0, min(23, int(hour)))

    if minute is not None:
       minute = max(0, min(59, int(minute)))
    # Encode inputs
    enc_cause     = encoders['event_cause'].transform(
                        [event_cause if event_cause in encoders['event_cause'].classes_
                         else 'others'])[0]
    enc_type      = encoders['event_type'].transform(
                        [event_type if event_type in encoders['event_type'].classes_
                         else 'unplanned'])[0]
    enc_corridor  = encoders['corridor'].transform(
                        [corridor if corridor in encoders['corridor'].classes_
                         else 'Non-corridor'])[0]
    enc_zone      = encoders['zone'].transform(
                        [zone if zone in encoders['zone'].classes_
                         else 'Unknown'])[0]
    enc_junction = encoders['junction'].transform(
    [junction if junction in encoders['junction'].classes_
     else 'Unknown']
)[0]

    is_peak  = 1 if hour in [7,8,9,17,18,19,20,21] else 0
    is_night = 1 if hour in [22,23,0,1,2,3,4,5] else 0
    is_major = 1 if corridor not in ['Non-corridor','Unknown'] else 0
    sev      = cause_severity.get(event_cause.lower(), 3)
    
    junction_freq = junction_freq_map.get(
    junction,
    np.mean(list(junction_freq_map.values()))
)

    corridor_freq = corridor_freq_map.get(
    corridor,
    np.mean(list(corridor_freq_map.values()))
)

    """hotspot_density = (
    0.7 * corridor_freq
    + 0.3 * junction_freq
)"""
    nearest_cluster = get_nearest_cluster(
    latitude,
    longitude
)

    hotspot_density = cluster_density_map.get(
    nearest_cluster,
    np.mean(list(cluster_density_map.values()))
)
    from datetime import datetime

    now = datetime.now()

    dow = now.weekday()
    if minute is None:
      minute = now.minute

    if month is None:
      month = now.month

    is_wknd = int(dow >= 5)

    row = np.array([[
    enc_cause,
    enc_type,
    hour,
    minute ,
    dow,
    month,
    is_wknd,
    is_peak,
    is_night,
    is_major,
    enc_corridor,
    enc_zone,
    sev,              
    enc_junction,
    junction_freq,
    corridor_freq,
    hotspot_density
]])
    
    DEBUG = False

    if DEBUG:
      print("Test row")
      print(pd.DataFrame(row, columns=FEATURE_COLS).T)
      print(pd.DataFrame(row, columns=FEATURE_COLS).T)
      print("Encoded cause:", enc_cause)
      print("Encoded corridor:", enc_corridor)
      print("Encoded junction:", enc_junction)

    probs = model_closure.predict_proba(row)[0]
    

    if DEBUG:
      print("Closure probability:", probs[1])
      test_df = pd.DataFrame(
      row,
    columns=FEATURE_COLS
)

      print(test_df)

    
    closure_prob = probs[1]

    closure_pred = int(
    closure_prob > 0.30
)
    impact_pred = (
    sev * 5
    + closure_pred * 20
    + is_major * 10
    + is_peak * 5
)
    priority_pred = 1 if impact_pred >= 50 else 0
    priority_prob = min(impact_pred,95)/100

    rec = recommend_resources(
        event_cause, 'High' if priority_pred else 'Low',
        bool(closure_pred), impact_pred, is_peak, is_major
    )
    assert row.shape[1] == model_closure.n_features_in_, \
    f"Expected {model_closure.n_features_in_} features, got {row.shape[1]}"

    return {
        'priority':         'High' if priority_pred else 'Low',
        'priority_score': min(
    max(priority_prob * 100, 1),
    99
),
        'road_closure_risk': 'Yes' if closure_pred else 'No',
        **rec
        ,
        'road_closure_probability': round(closure_prob * 100, 4),
   
    }




# Demo prediction
print("\n=== LIVE PREDICTION DEMO ===")
row433 = df.loc[433]

result = predict_incident(
    event_cause=row433['event_cause'],
    event_type=row433['event_type'],
    hour=int(row433['hour']),
    minute=int(row433['minute']),
    latitude=float(row433['latitude']),
    longitude=float(row433['longitude']),
    corridor=row433['corridor'],
    zone=row433['zone'],
    junction=row433['junction']
)
print("Input: public_event, ORR East 2, 18 PM")
print("Output:")
for k, v in result.items():
    print(f"  {k}: {v}")

# SAVE MODELS & ARTIFACTS 
import joblib, os
os.makedirs("models", exist_ok=True)

joblib.dump(model_closure, "models/closure_model.pkl")
joblib.dump(encoders, "models/encoders.pkl")
joblib.dump(junction_freq_map,
            "models/junction_freq_map.pkl")

joblib.dump(corridor_freq_map,
            "models/corridor_freq_map.pkl")

joblib.dump(
    cluster_centers,
    "models/cluster_centers.pkl"
)

joblib.dump(
    cluster_density_map,
    "models/cluster_density_map.pkl"
)
joblib.dump(
    cause_group_encoder,
    "models/cause_group_encoder.pkl"
)

joblib.dump(
    le_hotspot,
    "models/hotspot_encoder.pkl"
)

joblib.dump(
    le_hotspot_hour,
    "models/hotspot_hour_encoder.pkl"
)

joblib.dump(
    le_junction_hour,
    "models/junction_hour_encoder.pkl"
)

joblib.dump(
    le_corridor_hour,
    "models/corridor_hour_encoder.pkl"
)

joblib.dump(
    cause_severity,
    "models/cause_severity.pkl"
)
joblib.dump(
    model_cause,
    "models/cause_model.pkl"
)
joblib.dump(
    FEATURE_COLS,
    "models/closure_features.pkl"
)

joblib.dump(
    CAUSE_FEATURES,
    "models/cause_features.pkl"
)
joblib.dump(
    cluster_stats,
    "models/cluster_stats.pkl"
)

metadata = {
    "model_b_auc": auc,
    "model_d_accuracy": accuracy_score(y_te4, y_pred4),
    "training_rows": len(df)
}

joblib.dump(
    metadata,
    "models/model_metadata.pkl"
)

# Save hotspot data for frontend map
hotspot_export = cluster_stats.reset_index()
hotspot_export.to_json(
    "models/hotspots.json",
    orient="records"
)
hotspot_export.to_csv(
    "models/hotspot_summary.csv",
    index=False
)
cluster_stats.reset_index().to_json(
    "models/dashboard_hotspots.json",
    orient="records"
)

# Save resource table
import json
with open("models/resource_table.json", "w") as f:
    json.dump(RESOURCE_TABLE, f)

print("\nAll models saved to models/")
print("Files:", os.listdir("models"))

# ANALYTICS SUMMARY (for dashboard) 
print("\n=== ANALYTICS SUMMARY ===")
print(f"Total incidents analyzed: {len(df):,}")
print(f"High priority incidents:  {(df['priority']=='High').sum():,} ({(df['priority']=='High').mean()*100:.1f}%)")
print(f"Road closures:            {df['requires_road_closure'].sum():,} ({df['requires_road_closure'].mean()*100:.1f}%)")
print(f"Peak hour incidents:      {df['is_peak_hour'].sum():,}")
print(f"Hotspot clusters:         {n_clusters}")
print(f"Corridors monitored:      {df['corridor'].nunique()}")
print(f"Junctions covered:        {df['junction'].nunique()}")
print(f"\nMost dangerous cause:     {df.groupby('event_cause')['impact_score'].mean().idxmax()}")
print(f"Busiest corridor:         {df[df['corridor']!='Non-corridor']['corridor'].value_counts().index[0]}")
print(
    f"Average Congestion Risk: "
    f"{df['congestion_risk'].mean():.2f}"
)

print(
    f"Critical Risk Events: "
    f"{(df['risk_level']=='Critical').sum()}"
)
print(f"Highest risk junction:    {df[df['junction'].notna()]['junction'].value_counts().index[0]}")


print("\nCAUSE vs CORRIDOR")

cause_corridor = pd.crosstab(
    df["corridor"],
    df["event_cause"]
)

print(
    cause_corridor.idxmax(axis=1)
    .head(20)
)

print("\nHOTSPOT INSIGHTS")

for cluster_id in cluster_stats.index[:10]:

    subset = df[
        df["hotspot_cluster"] == cluster_id
    ]

    print(
        f"Cluster {cluster_id}: "
        f"{subset['event_cause'].mode()[0]}"
    )
