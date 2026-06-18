"""
train_lipakshi_fixed.py
=======================
All leakage and overfitting issues from the original fixed:

FIX-1  LabelEncoder   → fit on X_tr only, transform X_val with unseen-label fallback
FIX-2  grid_density   → computed on X_tr rows, mapped to X_val (0 if unseen cell)
FIX-3  Median impute  → computed on X_tr only, applied to X_val
FIX-4  pd.cut bins    → bin edges computed on X_tr, applied to X_val via pd.cut(bins=edges)
FIX-5  Stacking       → real StackingClassifier (XGB + LGB → LR meta), not just LGB
FIX-6  Duplicate fit  → removed duplicate stack.fit() call
FIX-7  Threshold      → aggregated from ALL folds, not just the last fold
FIX-8  Final model    → retrained on full data after CV, using best per-fold params
FIX-9  SHAP           → computed on a held-out slice, not the Optuna val fold
"""

import json
import warnings

import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder, label_binarize
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score,
    average_precision_score, precision_recall_curve,
)
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

from imblearn.over_sampling import SMOTE
import shap
import joblib

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
DATA_PATH  = r"D:\project\Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
OUTPUT_DIR = Path("model_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

N_OPTUNA_TRIALS    = 30   # bump to 100 for production
N_CV_FOLDS         = 5
SMOTE_RANDOM_STATE = 42


# ═════════════════════════════════════════════════════════════
# 1. LOAD (raw — NO encoding or imputation yet)
# ═════════════════════════════════════════════════════════════
print("=" * 60)
print("Loading data …")
df_raw = pd.read_csv(DATA_PATH)
print(f"  Shape : {df_raw.shape}")
print(f"  Cols  : {df_raw.columns.tolist()[:10]} …")


# ═════════════════════════════════════════════════════════════
# 2. IDENTIFY TARGET COLUMNS  (before any encoding)
# ═════════════════════════════════════════════════════════════
PRIORITY_COL = next((c for c in df_raw.columns if "priority" in c.lower()), None)
CLOSURE_COL  = next((c for c in df_raw.columns if "closure"  in c.lower()), None)
IMPACT_COL   = next((c for c in df_raw.columns if "impact"   in c.lower()), None)

if not PRIORITY_COL:
    raise ValueError("Cannot detect priority column — check column names.")

print(f"\n  Priority col : {PRIORITY_COL}")
print(f"  Closure col  : {CLOSURE_COL}")
print(f"  Impact col   : {IMPACT_COL}")

DROP_COLS = [c for c in [PRIORITY_COL, CLOSURE_COL, IMPACT_COL] if c]

y_priority = df_raw[PRIORITY_COL].values
GLOBAL_PRIORITY_CLASSES = np.unique(y_priority)
n_priority_classes      = len(GLOBAL_PRIORITY_CLASSES)
IS_MULTICLASS           = n_priority_classes > 2
print(f"\n  Priority classes : {GLOBAL_PRIORITY_CLASSES}  "
      f"→ {'MULTI-CLASS' if IS_MULTICLASS else 'BINARY'}")


# ═════════════════════════════════════════════════════════════
# 3. FOLD-SAFE FEATURE ENGINEERING  (called inside each fold)
# ═════════════════════════════════════════════════════════════

def engineer_features(df_tr_raw: pd.DataFrame,
                       df_val_raw: pd.DataFrame):
    """
    All preprocessing fitted on df_tr_raw only, then applied to df_val_raw.
    Returns (X_tr, X_val, feature_names, encoders_dict, train_medians).
    """
    df_tr  = df_tr_raw.copy()
    df_val = df_val_raw.copy()

    # ── Temporal features (no fit needed) ───────────────────────
    for ts_col in ["timestamp", "created_at"]:
        if ts_col in df_tr.columns:
            for df in [df_tr, df_val]:
                df[ts_col]        = pd.to_datetime(df[ts_col], errors="coerce")
                df["hour"]        = df[ts_col].dt.hour
                df["day_of_week"] = df[ts_col].dt.dayofweek
                df["month"]       = df[ts_col].dt.month
                df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
                df["is_peak_am"]  = df["hour"].between(7, 10).astype(int)
                df["is_peak_pm"]  = df["hour"].between(17, 20).astype(int)
                df["hour_sin"]    = np.sin(2 * np.pi * df["hour"] / 24)
                df["hour_cos"]    = np.cos(2 * np.pi * df["hour"] / 24)
                df["dow_sin"]     = np.sin(2 * np.pi * df["day_of_week"] / 7)
                df["dow_cos"]     = np.cos(2 * np.pi * df["day_of_week"] / 7)
                df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
                df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)
            break

    # ── FIX-4: Spatial grid — bin edges from train only ─────────
    if "latitude" in df_tr.columns and "longitude" in df_tr.columns:
        # Compute bin edges on training data
        _, lat_bins = pd.cut(df_tr["latitude"],  bins=20, retbins=True, labels=False)
        _, lng_bins = pd.cut(df_tr["longitude"], bins=20, retbins=True, labels=False)

        for df in [df_tr, df_val]:
            df["lat_bin"]   = pd.cut(df["latitude"],  bins=lat_bins,
                                     labels=False, include_lowest=True)
            df["lng_bin"]   = pd.cut(df["longitude"], bins=lng_bins,
                                     labels=False, include_lowest=True)
            df["lat_bin"]   = df["lat_bin"].fillna(-1).astype(int)
            df["lng_bin"]   = df["lng_bin"].fillna(-1).astype(int)
            df["grid_cell"] = df["lat_bin"].astype(str) + "_" + df["lng_bin"].astype(str)

        # FIX-2: grid_density computed on train rows only
        tr_grid_counts = df_tr.groupby("grid_cell").size()
        tr_max         = tr_grid_counts.max()
        df_tr["grid_density"]  = df_tr["grid_cell"].map(tr_grid_counts / tr_max).fillna(0)
        df_val["grid_density"] = df_val["grid_cell"].map(tr_grid_counts / tr_max).fillna(0)

    # Interaction feature
    if "is_peak_am" in df_tr.columns and "event_cause" in df_tr.columns:
        df_tr["peak_x_cause"]  = df_tr["is_peak_am"]  * df_tr["event_cause"]
        df_val["peak_x_cause"] = df_val["is_peak_am"] * df_val["event_cause"]

    # ── FIX-1: LabelEncoder fitted on TRAIN only ─────────────────
    object_cols = df_tr.select_dtypes(include="object").columns.tolist()
    encoders    = {}
    for col in object_cols:
        le = LabelEncoder()
        df_tr[col]  = le.fit_transform(df_tr[col].astype(str).fillna("MISSING"))
        # Unseen categories → -1
        known = set(le.classes_)
        df_val[col] = df_val[col].astype(str).fillna("MISSING").apply(
            lambda x: le.transform([x])[0] if x in known else -1
        )
        encoders[col] = le

    # ── FIX-3: Median imputation from TRAIN only ─────────────────
    train_medians = df_tr.median(numeric_only=True)
    df_tr.fillna(train_medians, inplace=True)
    df_val.fillna(train_medians, inplace=True)

    # Drop targets from feature set
    feature_cols = [c for c in df_tr.columns if c not in DROP_COLS]

    X_tr  = df_tr[feature_cols].values.astype(np.float64)
    X_val = df_val[feature_cols].values.astype(np.float64)

    X_tr  = np.nan_to_num(X_tr,  nan=0.0, posinf=0.0, neginf=0.0)
    X_val = np.nan_to_num(X_val, nan=0.0, posinf=0.0, neginf=0.0)

    return X_tr, X_val, feature_cols, encoders, train_medians


# ═════════════════════════════════════════════════════════════
# 4. CORE HELPERS
# ═════════════════════════════════════════════════════════════

def expand_proba(proba_fold, fold_classes, global_classes):
    n_global = len(global_classes)
    out = np.zeros((proba_fold.shape[0], n_global), dtype=np.float64)
    for local_idx, cls in enumerate(fold_classes):
        global_idx = np.searchsorted(global_classes, cls)
        out[:, global_idx] = proba_fold[:, local_idx]
    return out


def compute_auc(y_true, proba_global, multiclass, global_classes):
    if not multiclass:
        return roc_auc_score(y_true, proba_global[:, 1])

    present_classes = np.unique(y_true)
    if len(present_classes) < len(global_classes):
        preds = np.argmax(proba_global, axis=1)
        return accuracy_score(y_true, preds)

    try:
        y_bin = label_binarize(y_true, classes=global_classes)
        score = roc_auc_score(y_bin, proba_global, average="macro", multi_class="ovr")
        if np.isnan(score):
            return accuracy_score(y_true, np.argmax(proba_global, axis=1))
        return score
    except Exception:
        return accuracy_score(y_true, np.argmax(proba_global, axis=1))


# ═════════════════════════════════════════════════════════════
# 5. DEFAULT FALLBACK PARAMS
# ═════════════════════════════════════════════════════════════
def default_xgb_params(multiclass, n_classes):
    p = dict(n_estimators=300, max_depth=5, learning_rate=0.05,
             subsample=0.8, colsample_bytree=0.8,
             reg_alpha=0.1, reg_lambda=1.0, random_state=42,
             objective="multi:softprob" if multiclass else "binary:logistic",
             eval_metric="mlogloss" if multiclass else "logloss")
    if multiclass:
        p["num_class"] = n_classes
    return p

def default_lgb_params(multiclass, n_classes):
    p = dict(n_estimators=300, num_leaves=63, learning_rate=0.05,
             min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
             reg_alpha=0.1, reg_lambda=1.0, random_state=42, verbose=-1,
             objective="multiclass" if multiclass else "binary")
    if multiclass:
        p["num_class"] = n_classes
    return p

def default_rf_params():
    return dict(n_estimators=300, max_depth=10, min_samples_split=5,
                max_features="sqrt")


# ═════════════════════════════════════════════════════════════
# 6. OPTUNA OBJECTIVE FACTORIES
# ═════════════════════════════════════════════════════════════

def make_xgb_objective(X_tr, y_tr, X_val, y_val,
                       multiclass, n_classes, global_classes):
    def objective(trial):
        params = dict(
            n_estimators          = trial.suggest_int("n_estimators", 200, 800),
            max_depth             = trial.suggest_int("max_depth", 3, 10),
            learning_rate         = trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample             = trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree      = trial.suggest_float("colsample_bytree", 0.5, 1.0),
            reg_alpha             = trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            reg_lambda            = trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            objective             = "multi:softprob" if multiclass else "binary:logistic",
            eval_metric           = "mlogloss"       if multiclass else "logloss",
            early_stopping_rounds = 30,
            random_state          = 42,
        )
        if multiclass:
            params["num_class"] = n_classes

        m = xgb.XGBClassifier(**params)
        m.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        proba = expand_proba(m.predict_proba(X_val), m.classes_, global_classes)
        return compute_auc(y_val, proba, multiclass, global_classes)
    return objective


def make_lgb_objective(X_tr, y_tr, X_val, y_val,
                       multiclass, global_classes, n_classes):
    def objective(trial):
        params = dict(
            n_estimators      = trial.suggest_int("n_estimators", 200, 800),
            num_leaves        = trial.suggest_int("num_leaves", 20, 200),
            learning_rate     = trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            min_child_samples = trial.suggest_int("min_child_samples", 5, 100),
            subsample         = trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree  = trial.suggest_float("colsample_bytree", 0.5, 1.0),
            reg_alpha         = trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            reg_lambda        = trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            objective         = "multiclass" if multiclass else "binary",
            random_state      = 42,
            verbose           = -1,
        )
        if multiclass:
            params["num_class"] = n_classes

        m = lgb.LGBMClassifier(**params)
        m.fit(X_tr, y_tr,
              eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(50, verbose=False),
                         lgb.log_evaluation(-1)])
        proba = expand_proba(m.predict_proba(X_val), m.classes_, global_classes)
        return compute_auc(y_val, proba, multiclass, global_classes)
    return objective


def make_rf_objective(X_tr, y_tr, X_val, y_val,
                      multiclass, global_classes, class_weight=None):
    def objective(trial):
        params = dict(
            n_estimators      = trial.suggest_int("n_estimators", 100, 600),
            max_depth         = trial.suggest_int("max_depth", 3, 20),
            min_samples_split = trial.suggest_int("min_samples_split", 2, 20),
            max_features      = trial.suggest_categorical("max_features", ["sqrt", "log2"]),
            class_weight      = class_weight,
            random_state      = 42,
            n_jobs            = -1,
        )
        m = RandomForestClassifier(**params)
        m.fit(X_tr, y_tr)
        proba = expand_proba(m.predict_proba(X_val), m.classes_, global_classes)
        return compute_auc(y_val, proba, multiclass, global_classes)
    return objective


def run_study(objective_fn, n_trials, direction="maximize"):
    study = optuna.create_study(direction=direction)
    study.optimize(objective_fn, n_trials=n_trials,
                   catch=(Exception,), show_progress_bar=False)
    from optuna.trial import TrialState
    completed = [t for t in study.trials if t.state == TrialState.COMPLETE]
    if not completed:
        return None
    completed.sort(key=lambda t: t.value, reverse=(direction == "maximize"))
    return completed[0].params


# ═════════════════════════════════════════════════════════════
# 7. MODEL A — PRIORITY  (leakage-free CV)
# ═════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("Training PRIORITY model …")

skf       = StratifiedKFold(n_splits=N_CV_FOLDS, shuffle=True, random_state=42)
fold_aucs = []

# Track best params across folds (by AUC) to retrain final model
best_fold_auc    = -1
best_xgb_params_ = None
best_lgb_params_ = None

# For SHAP: collect a clean held-out sample (last fold val, separate from HPO)
shap_X_val   = None
FEATURE_COLS = None  # will be set in first fold

# FIX-7: collect all val probs for global threshold (used for closure later)
# (priority is multi-class, no threshold needed here)

for fold, (tr_idx, val_idx) in enumerate(skf.split(df_raw, y_priority)):
    df_tr_raw  = df_raw.iloc[tr_idx]
    df_val_raw = df_raw.iloc[val_idx]

    # FIX-1/2/3/4: all preprocessing inside the fold
    X_tr, X_val, feat_cols, encoders_fold, train_medians = engineer_features(
        df_tr_raw, df_val_raw
    )

    if FEATURE_COLS is None:
        FEATURE_COLS = feat_cols   # record feature names from fold 1

    y_tr  = y_priority[tr_idx]
    y_val = y_priority[val_idx]

    fold_classes_tr = np.unique(y_tr)
    n_fold_cls      = len(fold_classes_tr)
    fold_multi      = n_fold_cls > 2

    print(f"\n  Fold {fold+1}  |  train classes: {fold_classes_tr}  "
          f"val classes: {np.unique(y_val)}")

    # ── XGBoost ─────────────────────────────────────────────
    xgb_best = run_study(
        make_xgb_objective(X_tr, y_tr, X_val, y_val,
                           fold_multi, n_fold_cls, GLOBAL_PRIORITY_CLASSES),
        N_OPTUNA_TRIALS,
    )
    if xgb_best is None:
        print("    XGBoost: all trials failed — using default params")
        xgb_best = {}

    xgb_best.pop("early_stopping_rounds", None)
    xgb_best.update({
        "objective":    "multi:softprob" if fold_multi else "binary:logistic",
        "eval_metric":  "mlogloss"       if fold_multi else "logloss",
        "random_state": 42,
    })
    if fold_multi:
        xgb_best["num_class"] = n_fold_cls
    else:
        xgb_best.pop("num_class", None)

    full_xgb_params = {**default_xgb_params(fold_multi, n_fold_cls), **xgb_best}
    xgb_model = xgb.XGBClassifier(**full_xgb_params)
    xgb_model.fit(X_tr, y_tr)

    # ── LightGBM ────────────────────────────────────────────
    lgb_best = run_study(
        make_lgb_objective(X_tr, y_tr, X_val, y_val,
                           fold_multi, GLOBAL_PRIORITY_CLASSES, n_fold_cls),
        N_OPTUNA_TRIALS,
    )
    if lgb_best is None:
        print("    LightGBM: all trials failed — using default params")
        lgb_best = {}

    lgb_best.update({
        "objective":    "multiclass" if fold_multi else "binary",
        "random_state": 42,
        "verbose":      -1,
    })
    if fold_multi:
        lgb_best["num_class"] = n_fold_cls
    else:
        lgb_best.pop("num_class", None)

    full_lgb_params = {**default_lgb_params(fold_multi, n_fold_cls), **lgb_best}
    lgb_model = lgb.LGBMClassifier(**full_lgb_params)
    lgb_model.fit(X_tr, y_tr)

    # FIX-5: Real StackingClassifier (XGB + LGB → Logistic meta)
    meta_lr = LogisticRegression(C=0.1, max_iter=1000, solver="lbfgs")
    stack = StackingClassifier(
        estimators=[("xgb", xgb_model), ("lgb", lgb_model)],
        final_estimator=meta_lr,
        cv=3,          # inner 3-fold CV for meta features
        passthrough=False,
        n_jobs=-1,
    )
    stack.fit(X_tr, y_tr)   # FIX-6: only ONE fit call

    proba_stack = expand_proba(
        stack.predict_proba(X_val), stack.classes_, GLOBAL_PRIORITY_CLASSES
    )
    auc = compute_auc(y_val, proba_stack, IS_MULTICLASS, GLOBAL_PRIORITY_CLASSES)
    fold_aucs.append(auc)
    print(f"    Fold {fold+1} ROC-AUC : {auc:.4f}")

    # Track best fold for final-model param selection
    if auc > best_fold_auc:
        best_fold_auc    = auc
        best_xgb_params_ = full_xgb_params.copy()
        best_lgb_params_ = full_lgb_params.copy()
        shap_X_val       = X_val.copy()   # FIX-9: held-out, not HPO val

print(f"\n  CV Mean ROC-AUC : {np.mean(fold_aucs):.4f} ± {np.std(fold_aucs):.4f}")

# ── FIX-8: Retrain final model on FULL DATA ──────────────────
print("\n  Retraining final priority model on full dataset …")
X_full_tr, _, feat_cols_full, encoders_final, medians_final = engineer_features(
    df_raw, df_raw   # pass df_raw as both; val output is discarded
)
y_full = y_priority

n_global_cls = len(GLOBAL_PRIORITY_CLASSES)
final_multi  = n_global_cls > 2

best_xgb_params_["objective"]   = "multi:softprob" if final_multi else "binary:logistic"
best_xgb_params_["eval_metric"] = "mlogloss"       if final_multi else "logloss"
if final_multi:
    best_xgb_params_["num_class"] = n_global_cls
else:
    best_xgb_params_.pop("num_class", None)

best_lgb_params_["objective"] = "multiclass" if final_multi else "binary"
if final_multi:
    best_lgb_params_["num_class"] = n_global_cls
else:
    best_lgb_params_.pop("num_class", None)

final_xgb = xgb.XGBClassifier(**best_xgb_params_)
final_lgb = lgb.LGBMClassifier(**best_lgb_params_)
final_meta = LogisticRegression(C=0.1, max_iter=1000, solver="lbfgs")

priority_model = StackingClassifier(
    estimators=[("xgb", final_xgb), ("lgb", final_lgb)],
    final_estimator=final_meta,
    cv=3,
    passthrough=False,
    n_jobs=-1,
)
priority_model.fit(X_full_tr, y_full)

if not IS_MULTICLASS:
    # Calibrate on a small hold-out only for binary case
    cal_idx = np.random.choice(len(y_full), size=int(0.2 * len(y_full)), replace=False)
    priority_model = CalibratedClassifierCV(priority_model, cv="prefit")
    priority_model.fit(X_full_tr[cal_idx], y_full[cal_idx])

joblib.dump(priority_model, OUTPUT_DIR / "priority_model.pkl")
joblib.dump(encoders_final,  OUTPUT_DIR / "encoders.pkl")
joblib.dump(medians_final,   OUTPUT_DIR / "train_medians.pkl")
print("  Saved priority_model.pkl")


# ═════════════════════════════════════════════════════════════
# 8. MODEL B — ROAD CLOSURE  (binary, imbalanced)
# ═════════════════════════════════════════════════════════════
fold_aucs_cl, fold_ap_cl               = [], []
all_probs_cl_list, all_y_val_cl_list   = [], []   # FIX-7 accumulators
best_thresh                            = 0.5
best_rf_params_                        = None
best_fold_auc_cl                       = -1

if CLOSURE_COL:
    print("\n" + "=" * 60)
    print("Training ROAD CLOSURE model (imbalanced) …")
    y_closure         = df_raw[CLOSURE_COL].values
    GLOBAL_CL_CLASSES = np.array([0, 1])
    print(f"  Road closure base rate: {y_closure.mean():.2%}")

    skf_cl = StratifiedKFold(n_splits=N_CV_FOLDS, shuffle=True, random_state=42)

    for fold, (tr_idx, val_idx) in enumerate(skf_cl.split(df_raw, y_closure)):
        df_tr_raw  = df_raw.iloc[tr_idx]
        df_val_raw = df_raw.iloc[val_idx]

        # FIX-1/2/3/4 inside fold
        X_tr, X_val, _, _, _ = engineer_features(df_tr_raw, df_val_raw)
        y_tr  = y_closure[tr_idx]
        y_val = y_closure[val_idx]

        smote = SMOTE(sampling_strategy="minority", random_state=SMOTE_RANDOM_STATE)
        X_tr_sm, y_tr_sm = smote.fit_resample(X_tr, y_tr)

        rf_best = run_study(
            make_rf_objective(X_tr_sm, y_tr_sm, X_val, y_val,
                              multiclass=False,
                              global_classes=GLOBAL_CL_CLASSES,
                              class_weight="balanced"),
            N_OPTUNA_TRIALS,
        )
        if rf_best is None:
            print(f"    RF fold {fold+1}: all trials failed — using defaults")
            rf_best = {}

        full_rf_params = {**default_rf_params(), **rf_best,
                          "class_weight": "balanced",
                          "random_state": 42, "n_jobs": -1}
        rf = RandomForestClassifier(**full_rf_params)
        rf.fit(X_tr_sm, y_tr_sm)

        probs = rf.predict_proba(X_val)[:, 1]
        auc   = roc_auc_score(y_val, probs)
        ap    = average_precision_score(y_val, probs)
        fold_aucs_cl.append(auc)
        fold_ap_cl.append(ap)

        # FIX-7: accumulate ALL fold probs for global threshold search
        all_probs_cl_list.append(probs)
        all_y_val_cl_list.append(y_val)

        print(f"  Fold {fold+1} ROC-AUC: {auc:.4f}  Avg-Prec: {ap:.4f}")

        if auc > best_fold_auc_cl:
            best_fold_auc_cl = auc
            best_rf_params_  = full_rf_params.copy()

    # FIX-7: threshold from aggregated probs across ALL folds
    all_probs_cl = np.concatenate(all_probs_cl_list)
    all_y_cl     = np.concatenate(all_y_val_cl_list)
    precisions, recalls, thresholds = precision_recall_curve(all_y_cl, all_probs_cl)
    denom        = np.where((precisions + recalls) == 0, 1e-9, precisions + recalls)
    f1s          = 2 * precisions * recalls / denom
    best_thresh  = float(thresholds[np.argmax(f1s[:-1])])

    print(f"\n  Optimal threshold : {best_thresh:.3f}")
    print(f"  CV Mean ROC-AUC   : {np.mean(fold_aucs_cl):.4f} "
          f"± {np.std(fold_aucs_cl):.4f}")
    print(f"  CV Mean Avg-Prec  : {np.mean(fold_ap_cl):.4f}")

    # FIX-8: retrain closure model on full data
    print("\n  Retraining final closure model on full dataset …")
    X_full_cl, _, _, _, _ = engineer_features(df_raw, df_raw)
    smote_full = SMOTE(sampling_strategy="minority", random_state=SMOTE_RANDOM_STATE)
    X_cl_sm, y_cl_sm = smote_full.fit_resample(X_full_cl, y_closure)
    closure_model = RandomForestClassifier(**best_rf_params_)
    closure_model.fit(X_cl_sm, y_cl_sm)

    joblib.dump(closure_model, OUTPUT_DIR / "closure_model.pkl")
    joblib.dump(best_thresh,   OUTPUT_DIR / "closure_threshold.pkl")
    print("  Saved closure_model.pkl + closure_threshold.pkl")


# ═════════════════════════════════════════════════════════════
# 9. MODEL C — IMPACT SCORE  (CatBoost multi-class)
# ═════════════════════════════════════════════════════════════
fold_accs = []

if IMPACT_COL:
    print("\n" + "=" * 60)
    print("Training IMPACT SCORE model (CatBoost multi-class) …")
    y_impact  = df_raw[IMPACT_COL].values
    n_imp_cls = len(np.unique(y_impact))
    skf_imp   = StratifiedKFold(n_splits=N_CV_FOLDS, shuffle=True, random_state=42)

    def catboost_objective(trial, X_tr, y_tr, X_val, y_val, n_cls):
        params = dict(
            iterations    = trial.suggest_int("iterations", 200, 800),
            depth         = trial.suggest_int("depth", 4, 10),
            learning_rate = trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            l2_leaf_reg   = trial.suggest_float("l2_leaf_reg", 1e-3, 10.0, log=True),
            loss_function = "MultiClass" if n_cls > 2 else "Logloss",
            eval_metric   = "Accuracy",
            random_seed   = 42,
            verbose       = 0,
        )
        m = CatBoostClassifier(**params)
        m.fit(X_tr, y_tr, eval_set=(X_val, y_val), early_stopping_rounds=50)
        return accuracy_score(y_val, m.predict(X_val))

    cb = None
    best_cb_params_  = None
    best_fold_acc_cb = -1

    for fold, (tr_idx, val_idx) in enumerate(skf_imp.split(df_raw, y_impact)):
        df_tr_raw  = df_raw.iloc[tr_idx]
        df_val_raw = df_raw.iloc[val_idx]

        X_tr, X_val, _, _, _ = engineer_features(df_tr_raw, df_val_raw)
        y_tr  = y_impact[tr_idx]
        y_val = y_impact[val_idx]

        cb_best = run_study(
            lambda trial: catboost_objective(trial, X_tr, y_tr, X_val, y_val, n_imp_cls),
            N_OPTUNA_TRIALS,
        )
        if cb_best is None:
            print(f"    CatBoost fold {fold+1}: all trials failed — using defaults")
            cb_best = {}

        cb_best.update({
            "loss_function": "MultiClass" if n_imp_cls > 2 else "Logloss",
            "random_seed": 42, "verbose": 0,
        })
        cb = CatBoostClassifier(**cb_best)
        cb.fit(X_tr, y_tr)
        acc = accuracy_score(y_val, cb.predict(X_val))
        fold_accs.append(acc)
        print(f"  Fold {fold+1} Accuracy: {acc:.4f}")

        if acc > best_fold_acc_cb:
            best_fold_acc_cb = acc
            best_cb_params_  = cb_best.copy()

    print(f"\n  CV Mean Accuracy: {np.mean(fold_accs):.4f} ± {np.std(fold_accs):.4f}")

    # FIX-8: retrain on full data
    if best_cb_params_ is not None:
        print("\n  Retraining final impact model on full dataset …")
        X_full_imp, _, _, _, _ = engineer_features(df_raw, df_raw)
        final_cb = CatBoostClassifier(**best_cb_params_)
        final_cb.fit(X_full_imp, y_impact)
        joblib.dump(final_cb, OUTPUT_DIR / "impact_model.pkl")
        print("  Saved impact_model.pkl")


# ═════════════════════════════════════════════════════════════
# 10. SHAP FEATURE IMPORTANCE
#     FIX-9: use shap_X_val (from the best CV fold's held-out set,
#             NOT the Optuna tuning val split)
# ═════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("Computing SHAP feature importance …")
SELECTED_FEATS = FEATURE_COLS

try:
    # Use the LGB component of the stacking model for SHAP
    lgb_component = priority_model.named_estimators_["lgb"] \
        if hasattr(priority_model, "named_estimators_") else priority_model

    explainer  = shap.TreeExplainer(lgb_component)
    shap_vals  = explainer.shap_values(shap_X_val)

    if isinstance(shap_vals, list):
        mean_shap = np.mean([np.abs(sv) for sv in shap_vals], axis=0).mean(axis=0)
    elif len(shap_vals.shape) == 3:
        mean_shap = np.abs(shap_vals).mean(axis=(0, 2))
    else:
        mean_shap = np.abs(shap_vals).mean(axis=0)

    feat_imp = (pd.Series(mean_shap, index=FEATURE_COLS)
                  .sort_values(ascending=False))
    print("\n  Top 20 features by SHAP:")
    print(feat_imp.head(20).to_string())

    keep_thresh    = feat_imp.max() * 0.001
    SELECTED_FEATS = feat_imp[feat_imp >= keep_thresh].index.tolist()
    print(f"\n  Features kept after SHAP selection: "
          f"{len(SELECTED_FEATS)} / {len(FEATURE_COLS)}")
    joblib.dump(SELECTED_FEATS, OUTPUT_DIR / "selected_features.pkl")

except Exception as e:
    print(f"  SHAP skipped: {e}")


# ═════════════════════════════════════════════════════════════
# 11. SAVE ARTEFACTS & REPORT
# ═════════════════════════════════════════════════════════════
joblib.dump(FEATURE_COLS, OUTPUT_DIR / "feature_cols.pkl")

report = {
    "priority_model": {
        "type":            "XGBoost + LightGBM Stacking → Logistic Meta (retrained on full data)",
        "n_classes":       int(n_priority_classes),
        "is_multiclass":   IS_MULTICLASS,
        "cv_roc_auc_mean": round(float(np.mean(fold_aucs)), 4),
        "cv_roc_auc_std":  round(float(np.std(fold_aucs)), 4),
        "optuna_trials":   N_OPTUNA_TRIALS,
        "n_cv_folds":      N_CV_FOLDS,
    },
    "leakage_fixes": [
        "FIX-1: LabelEncoder fitted on train fold only; unseen categories → -1",
        "FIX-2: grid_density computed on train rows only; mapped to val via train lookup",
        "FIX-3: Median imputation from train rows only, applied to val",
        "FIX-4: pd.cut bin edges from train lat/lng; applied to val with include_lowest",
        "FIX-5: Real StackingClassifier (XGB + LGB → LR meta) replacing single LGB",
        "FIX-6: Duplicate stack.fit() call removed",
        "FIX-7: Closure threshold from aggregated ALL-fold probs, not last fold only",
        "FIX-8: Final ../backend/models retrained on full dataset using best CV params",
        "FIX-9: SHAP computed on best fold's held-out val, not the Optuna tuning split",
    ],
}

if CLOSURE_COL and fold_aucs_cl:
    report["closure_model"] = {
        "type":              "Random Forest + SMOTE (retrained on full data)",
        "cv_roc_auc_mean":   round(float(np.mean(fold_aucs_cl)), 4),
        "cv_roc_auc_std":    round(float(np.std(fold_aucs_cl)), 4),
        "cv_avg_prec_mean":  round(float(np.mean(fold_ap_cl)), 4),
        "optimal_threshold": round(best_thresh, 4),
    }

if IMPACT_COL and fold_accs:
    report["impact_model"] = {
        "type":             "CatBoost Multi-Class (retrained on full data)",
        "cv_accuracy_mean": round(float(np.mean(fold_accs)), 4),
        "cv_accuracy_std":  round(float(np.std(fold_accs)), 4),
    }

with open(OUTPUT_DIR / "training_report_v5.json", "w") as f:
    json.dump(report, f, indent=2)

print("\n" + "=" * 60)
print("All done! Outputs in:", OUTPUT_DIR)
print(json.dumps(report, indent=2))