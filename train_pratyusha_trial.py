import pandas as pd
import numpy as np
import os
import json
import joblib

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score
)

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score
)

from xgboost import XGBClassifier

# ==========================================
# LOAD DATA
# ==========================================

df = pd.read_csv("../data/event_data.csv")

print("\nDataset Shape:")
print(df.shape)

# ==========================================
# DATETIME FEATURES
# ==========================================

df["start_datetime"] = pd.to_datetime(
    df["start_datetime"],
    errors="coerce"
)

df["hour"] = df["start_datetime"].dt.hour
df["weekday"] = df["start_datetime"].dt.dayofweek
df["month"] = df["start_datetime"].dt.month

# ==========================================
# FEATURE ENGINEERING
# ==========================================

df["planned_flag"] = (
    df["event_type"]
    .astype(str)
    .str.lower()
    .eq("planned")
    .astype(int)
)

df["junction_count"] = (
    df.groupby("junction")["junction"]
      .transform("count")
)

df["corridor_count"] = (
    df.groupby("corridor")["corridor"]
      .transform("count")
)

df["cause_count"] = (
    df.groupby("event_cause")["event_cause"]
      .transform("count")
)

# Historical closure probability by junction

junction_closure_rate = (
    df.groupby("junction")["requires_road_closure"]
      .mean()
)

df["junction_closure_rate"] = (
    df["junction"]
    .map(junction_closure_rate)
)

# Historical closure probability by corridor

corridor_closure_rate = (
    df.groupby("corridor")["requires_road_closure"]
      .mean()
)

df["corridor_closure_rate"] = (
    df["corridor"]
    .map(corridor_closure_rate)
)

# ==========================================
# FEATURES
# ==========================================

features = [
    "event_type",
    "event_cause",
    "direction",
    "corridor",
    "zone",
    "junction",

    "latitude",
    "longitude",

    "hour",
    "weekday",
    "month",

    "planned_flag",

    "junction_count",
    "corridor_count",
    "cause_count",

    "junction_closure_rate",
    "corridor_closure_rate"
]

target = "requires_road_closure"

# ==========================================
# KEEP REQUIRED COLUMNS
# ==========================================

df = df[features + [target]]

# ==========================================
# MISSING VALUES
# ==========================================

categorical_cols = [
    "event_type",
    "event_cause",
    "direction",
    "corridor",
    "zone",
    "junction"
]

numeric_cols = [
    "latitude",
    "longitude",

    "hour",
    "weekday",
    "month",

    "planned_flag",

    "junction_count",
    "corridor_count",
    "cause_count",

    "junction_closure_rate",
    "corridor_closure_rate"
]

for col in categorical_cols:
    df[col] = (
        df[col]
        .fillna("Unknown")
        .astype(str)
    )

for col in numeric_cols:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    df[col] = df[col].fillna(
        df[col].median()
    )

# ==========================================
# ENCODING
# ==========================================

encoders = {}

for col in categorical_cols:

    le = LabelEncoder()

    df[col] = le.fit_transform(
        df[col]
    )

    encoders[col] = le

# ==========================================
# TARGET
# ==========================================

df[target] = df[target].astype(int)

# ==========================================
# X Y
# ==========================================

X = df[features].astype("float32")
y = df[target]

print("\nTarget Distribution:")
print(y.value_counts())

# ==========================================
# CLASS IMBALANCE
# ==========================================

neg = y.value_counts()[0]
pos = y.value_counts()[1]

scale_pos_weight = neg / pos

print("\nScale Pos Weight:")
print(round(scale_pos_weight, 2))

# ==========================================
# TRAIN TEST SPLIT
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42
)

# ==========================================
# MODEL
# ==========================================

model = XGBClassifier(
    n_estimators=800,
    max_depth=8,

    learning_rate=0.03,

    subsample=0.85,
    colsample_bytree=0.85,

    min_child_weight=3,
    gamma=0.2,

    scale_pos_weight=scale_pos_weight,

    random_state=42,
    eval_metric="logloss"
)
# ==========================================
# CROSS VALIDATION
# ==========================================

print("\nRunning Cross Validation...")

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

cv_scores = cross_val_score(
    model,
    X,
    y,
    cv=cv,
    scoring="f1"
)

print("\nCross Validation F1 Scores:")
print(cv_scores)

print(
    "\nMean F1 Score:",
    round(cv_scores.mean(), 4)
)

# ==========================================
# TRAIN MODEL
# ==========================================

print("\nTraining Model...")

model.fit(
    X_train,
    y_train
)

# ==========================================
# PREDICTIONS
# ==========================================

preds = model.predict(X_test)

probs = model.predict_proba(X_test)[:,1]

preds = (probs > 0.35).astype(int)
# ==========================================
# EVALUATION
# ==========================================

print("\nAccuracy:")
print(
    round(
        accuracy_score(
            y_test,
            preds
        ),
        4
    )
)

print("\nPrecision:")
print(
    round(
        precision_score(
            y_test,
            preds
        ),
        4
    )
)

print("\nRecall:")
print(
    round(
        recall_score(
            y_test,
            preds
        ),
        4
    )
)

print("\nF1 Score:")
print(
    round(
        f1_score(
            y_test,
            preds
        ),
        4
    )
)

print("\nROC AUC:")
print(
    round(
        roc_auc_score(
            y_test,
            probs
        ),
        4
    )
)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        preds
    )
)

print("\nConfusion Matrix:")
print(
    confusion_matrix(
        y_test,
        preds
    )
)

# ==========================================
# FEATURE IMPORTANCE
# ==========================================

importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": model.feature_importances_
})

importance_df = importance_df.sort_values(
    "Importance",
    ascending=False
)

print("\nFeature Importance:")
print(importance_df)

# ==========================================
# HOTSPOTS
# ==========================================

hotspots = []

top_junctions = (
    df.groupby("junction")
      .size()
      .sort_values(ascending=False)
      .head(20)
)

for junction_id in top_junctions.index:

    row = df[df["junction"] == junction_id].iloc[0]

    hotspots.append({
        "junction": int(junction_id),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "incident_count": int(top_junctions[junction_id])
    })

# ==========================================
# RESOURCE TABLE
# ==========================================

resource_table = {
    "Low": {
        "officers": 2,
        "barricades": 2,
        "diversion": False
    },
    "Medium": {
        "officers": 5,
        "barricades": 6,
        "diversion": True
    },
    "High": {
        "officers": 10,
        "barricades": 12,
        "diversion": True
    }
}

# ==========================================
# SAVE FILES
# ==========================================

os.makedirs(
    "models",
    exist_ok=True
)

joblib.dump(
    model,
    "models/closure_model.pkl"
)

joblib.dump(
    encoders,
    "models/encoders.pkl"
)

with open(
    "models/resource_table.json",
    "w"
) as f:

    json.dump(
        resource_table,
        f,
        indent=4
    )

with open(
    "models/hotspots.json",
    "w"
) as f:

    json.dump(
        hotspots,
        f,
        indent=4
    )
    

print("\nFiles Generated Successfully")

# ==========================================
# OUTPUT REPORTS
# ==========================================

os.makedirs(
    "../outputs",
    exist_ok=True
)

# Metrics JSON

metrics = {
    "accuracy": float(
        accuracy_score(y_test, preds)
    ),
    "precision": float(
        precision_score(y_test, preds)
    ),
    "recall": float(
        recall_score(y_test, preds)
    ),
    "f1_score": float(
        f1_score(y_test, preds)
    ),
    "roc_auc": float(
        roc_auc_score(y_test, probs)
    ),
    "cv_f1_mean": float(
        cv_scores.mean()
    )
}

with open(
    "../outputs/model_metrics.json",
    "w"
) as f:

    json.dump(
        metrics,
        f,
        indent=4
    )

# Feature Importance CSV

importance_df.to_csv(
    "../outputs/feature_importance.csv",
    index=False
)

# Training Summary TXT

with open(
    "../outputs/training_summary.txt",
    "w"
) as f:

    f.write(
        f"""
MODEL TRAINING SUMMARY

Dataset Shape:
{df.shape}

Cross Validation F1:
{cv_scores.mean():.4f}

Accuracy:
{accuracy_score(y_test,preds):.4f}

Precision:
{precision_score(y_test,preds):.4f}

Recall:
{recall_score(y_test,preds):.4f}

F1 Score:
{f1_score(y_test,preds):.4f}

ROC AUC:
{roc_auc_score(y_test,probs):.4f}

Top Features:

{importance_df.head(10).to_string(index=False)}
"""
    )

print("""
Generated Files

MODELS
------
closure_model.pkl
encoders.pkl
resource_table.json
hotspots.json

OUTPUTS
-------
model_metrics.json
feature_importance.csv
training_summary.txt
""")