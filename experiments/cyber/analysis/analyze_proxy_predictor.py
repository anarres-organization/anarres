#!/usr/bin/env python3
"""Proxy utility predictor — CLEAN version excluding reward-leaking features.

any_exit1 and any_exit0_submit encode the environment reward directly
(exit code from submit.sh = crash detection = ground truth). A utility
proxy must predict success from BEHAVIORAL signals only.
"""

import json
import sys
import warnings

import numpy as np
from scipy import stats
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

FEATURES_PATH = sys.argv[1] if len(sys.argv) > 1 else "behavioral_features.json"

with open(FEATURES_PATH) as f:
    data = json.load(f)

# ── Feature matrix — NO reward-leaking features ────────────────────
NUMERIC_FEATURES = [
    "turns",
    "n_tool_calls",
    "total_input_tokens",
    "total_output_tokens",
    "harness_time_s",
    "n_read_file",
    "n_bash",
    "n_write_file",
    "n_submissions",
    "n_real_submissions",
    "n_grep",
    "n_cat",
    "n_python",
    "n_find",
    "n_compile",
    "n_hexdump",
    "n_poc_writes",
    "n_script_writes",
    "exploit_ratio",
    "first_sub_turn",
    "tokens_per_turn",
    "output_ratio",
]
BOOL_FEATURES = [
    "read_readme",
    "read_description",
    "read_error",
    "read_patch",
    "read_source",
    # EXCLUDED: any_exit1, any_exit0_submit (these ARE the reward signal)
]
ALL_FEATURES = NUMERIC_FEATURES + BOOL_FEATURES

X = np.array([[d[f] for f in ALL_FEATURES] for d in data], dtype=float)
y = np.array([1 if d["success"] else 0 for d in data])

n_pos = y.sum()
n_neg = len(y) - n_pos
print(f"Dataset: {len(y)} tasks, {n_pos} successes, {n_neg} failures")
print(f"Base rate: {n_pos / len(y):.1%}")
print(f"Features: {len(ALL_FEATURES)} (exit-code features EXCLUDED as reward leakage)\n")

# ── Descriptive statistics ──────────────────────────────────────────
print("=" * 72)
print("FEATURE COMPARISON: SUCCESS vs FAILURE")
print("=" * 72)
hdr = f"{'Feature':<25s} {'Success (n=6)':>18s} {'Failure (n=44)':>18s}"
print(f"{hdr} {'Δ':>10s}")
print("-" * 72)

for i, feat in enumerate(ALL_FEATURES):
    s_vals = X[y == 1, i]
    f_vals = X[y == 0, i]
    s_mean, s_std = s_vals.mean(), s_vals.std()
    f_mean, f_std = f_vals.mean(), f_vals.std()
    delta = s_mean - f_mean
    print(f"{feat:<25s} {s_mean:8.2f} ± {s_std:6.2f} {f_mean:8.2f} ± {f_std:6.2f} {delta:+10.2f}")

# ── Mann-Whitney U tests ───────────────────────────────────────────
print(f"\n{'=' * 72}")
print("MANN-WHITNEY U TESTS (two-sided, behavioral features only)")
print("=" * 72)
mw_hdr = f"{'Feature':<25s} {'U':>8s} {'p-value':>10s} {'Effect r':>10s}"
print(f"{mw_hdr} {'Sig':>5s}")
print("-" * 72)

significant_features = []
for i, feat in enumerate(ALL_FEATURES):
    s_vals = X[y == 1, i]
    f_vals = X[y == 0, i]
    if s_vals.std() == 0 and f_vals.std() == 0:
        print(f"{feat:<25s} {'--':>8s} {'--':>10s} {'--':>10s} {'const':>5s}")
        continue
    try:
        u_stat, p_val = stats.mannwhitneyu(s_vals, f_vals, alternative="two-sided")
        r_effect = 1 - (2 * u_stat) / (len(s_vals) * len(f_vals))
        if p_val < 0.01:
            sig = "**"
        elif p_val < 0.05:
            sig = "*"
        elif p_val < 0.10:
            sig = "†"
        else:
            sig = ""
        if p_val < 0.10:
            significant_features.append((feat, p_val, r_effect))
        print(f"{feat:<25s} {u_stat:8.0f} {p_val:10.4f} {r_effect:+10.3f} {sig:>5s}")
    except Exception as e:
        print(f"{feat:<25s} error: {e}")

print()
if significant_features:
    print(f"Features with p < 0.10: {len(significant_features)}")
    for feat, p, r in sorted(significant_features, key=lambda x: x[1]):
        print(f"  {feat}: p={p:.4f}, r={r:+.3f}")
else:
    print("No features individually significant at p < 0.10")
    print("(With n=6 positives, individual features lack power.)")
    print("This is expected — the signal may be in feature COMBINATIONS.")

# ── Modeling: LOO-CV ────────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
loo = LeaveOneOut()

models = {
    "LogReg L2 C=0.01": LogisticRegression(
        C=0.01,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        class_weight="balanced",
    ),
    "LogReg L2 C=0.1": LogisticRegression(
        C=0.1,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        class_weight="balanced",
    ),
    "LogReg L1 C=0.1": LogisticRegression(
        C=0.1,
        penalty="l1",
        solver="saga",
        max_iter=2000,
        class_weight="balanced",
    ),
    "RandomForest d=2": RandomForestClassifier(
        n_estimators=200,
        max_depth=2,
        class_weight="balanced",
        random_state=42,
    ),
    "RandomForest d=3": RandomForestClassifier(
        n_estimators=200,
        max_depth=3,
        class_weight="balanced",
        random_state=42,
    ),
    "GBM d=1": GradientBoostingClassifier(
        n_estimators=30,
        max_depth=1,
        learning_rate=0.1,
        random_state=42,
    ),
    "GBM d=2": GradientBoostingClassifier(
        n_estimators=50,
        max_depth=2,
        learning_rate=0.1,
        random_state=42,
    ),
    "Baseline (random)": None,
}

print(f"\n{'=' * 72}")
print("LOO-CV MODEL PERFORMANCE (no reward leakage)")
print("=" * 72)
print(f"\n{'Model':<25s} {'AUC':>8s} {'Brier':>8s} {'Rank-biased':>14s}")
print("-" * 52)

best_auc = 0
best_model_name = None
model_probs = {}

for name, model in models.items():
    if model is None:
        rng = np.random.RandomState(42)
        probs = rng.uniform(0, 1, len(y))
        auc = roc_auc_score(y, probs)
        brier = brier_score_loss(y, probs)
        model_probs[name] = probs
        print(f"{name:<25s} {auc:8.3f} {brier:8.3f} {'--':>14s}")
        continue

    X_use = X_scaled if "LogReg" in name else X
    try:
        probs = cross_val_predict(model, X_use, y, cv=loo, method="predict_proba")[:, 1]
        auc = roc_auc_score(y, probs)
        brier = brier_score_loss(y, probs)
        model_probs[name] = probs

        top6 = np.argsort(-probs)[:6]
        rbp = y[top6].sum() / 6

        print(f"{name:<25s} {auc:8.3f} {brier:8.3f} {rbp:14.3f}")
        if auc > best_auc:
            best_auc = auc
            best_model_name = name
    except Exception as e:
        print(f"{name:<25s} ERROR: {e}")

print(f"\nBest LOO-CV AUC: {best_auc:.3f} ({best_model_name})")
baseline_auc = roc_auc_score(y, model_probs["Baseline (random)"])
print(f"Random baseline: {baseline_auc:.3f}")

# ── Bootstrap CI on the best model's AUC ────────────────────────────
ci_lo, ci_hi = 0.0, 1.0
if best_model_name and best_model_name in model_probs:
    probs = model_probs[best_model_name]

    n_bootstrap = 10000
    rng = np.random.RandomState(42)
    auc_boots = []
    for _ in range(n_bootstrap):
        idx = rng.choice(len(y), size=len(y), replace=True)
        if y[idx].sum() == 0 or y[idx].sum() == len(idx):
            continue
        auc_boots.append(roc_auc_score(y[idx], probs[idx]))

    auc_boots = np.array(auc_boots)
    ci_lo = np.percentile(auc_boots, 2.5)
    ci_hi = np.percentile(auc_boots, 97.5)
    n_valid = len(auc_boots)
    print(f"\nBootstrap 95% CI on AUC: [{ci_lo:.3f}, {ci_hi:.3f}] (n={n_valid} valid resamples)")

# ── Feature importance ──────────────────────────────────────────────
print(f"\n{'=' * 72}")
print("FEATURE IMPORTANCE (full-data fit, behavioral features only)")
print("=" * 72)

lr_full = LogisticRegression(
    C=0.1,
    penalty="l2",
    solver="lbfgs",
    max_iter=1000,
    class_weight="balanced",
)
lr_full.fit(X_scaled, y)
lr_coefs = lr_full.coef_[0]

rf_full = RandomForestClassifier(
    n_estimators=200,
    max_depth=3,
    class_weight="balanced",
    random_state=42,
)
rf_full.fit(X, y)
rf_imp = rf_full.feature_importances_

gbm_full = GradientBoostingClassifier(
    n_estimators=50,
    max_depth=2,
    learning_rate=0.1,
    random_state=42,
)
gbm_full.fit(X, y)
gbm_imp = gbm_full.feature_importances_

lr_ranks = np.argsort(-np.abs(lr_coefs)).argsort() + 1
rf_ranks = np.argsort(-rf_imp).argsort() + 1
gbm_ranks = np.argsort(-gbm_imp).argsort() + 1
mean_ranks = (lr_ranks + rf_ranks + gbm_ranks) / 3.0

sorted_by_rank = np.argsort(mean_ranks)
print(f"\n{'Feature':<25s} {'LR coef':>10s} {'RF imp':>10s} {'GBM imp':>10s} {'Mean rank':>10s}")
print("-" * 68)
for idx in sorted_by_rank:
    feat = ALL_FEATURES[idx]
    lr_c = lr_coefs[idx]
    rf_i = rf_imp[idx]
    gbm_i = gbm_imp[idx]
    mr = mean_ranks[idx]
    print(f"{feat:<25s} {lr_c:+10.4f} {rf_i:10.4f} {gbm_i:10.4f} {mr:10.1f}")

# ── Permutation importance ──────────────────────────────────────────
print(f"\n{'=' * 72}")
print("PERMUTATION IMPORTANCE (200 repeats)")
print("=" * 72)

for label, model_obj in [("LogReg L2", lr_full), ("RandomForest", rf_full)]:
    X_use = X_scaled if "LogReg" in label else X
    perm = permutation_importance(
        model_obj,
        X_use,
        y,
        n_repeats=200,
        scoring="roc_auc",
        random_state=42,
    )
    top_idx = np.argsort(-perm.importances_mean)[:10]
    print(f"\n{label}:")
    print(f"  {'Feature':<25s} {'AUC drop':>10s} {'Std':>8s}")
    print(f"  {'-' * 44}")
    for idx in top_idx:
        pmean = perm.importances_mean[idx]
        pstd = perm.importances_std[idx]
        if pmean > 0.005:
            print(f"  {ALL_FEATURES[idx]:<25s} {pmean:10.4f} {pstd:8.4f}")

# ── Predicted probabilities ─────────────────────────────────────────
if best_model_name in model_probs:
    probs = model_probs[best_model_name]
    print(f"\n{'=' * 72}")
    print(f"PREDICTED PROBABILITIES ({best_model_name}, no reward features)")
    print("=" * 72)

    sorted_idx = np.argsort(-probs)
    print(f"\n{'Rank':>4s} {'Task':<20s} {'P(success)':>12s} {'Actual':>8s}")
    print("-" * 48)
    for rank, idx in enumerate(sorted_idx, 1):
        marker = "<<<" if y[idx] == 1 else ""
        task = data[idx]["task_id"]
        p = probs[idx]
        actual = "SUCCESS" if y[idx] else "fail"
        print(f"{rank:4d} {task:<20s} {p:12.3f} {actual:>8s} {marker}")

    success_ranks = []
    for rank, idx in enumerate(sorted_idx, 1):
        if y[idx] == 1:
            success_ranks.append(rank)

    print(f"\nSuccess ranks in predicted ordering: {success_ranks}")
    print(f"Mean success rank: {np.mean(success_ranks):.1f} / {len(y)}")
    for k in [6, 10, 12]:
        n_in = sum(1 for r in success_ranks if r <= k)
        print(f"Successes in top-{k}: {n_in}")

# ── Ablation: single-feature models ────────────────────────────────
print(f"\n{'=' * 72}")
print("SINGLE-FEATURE LOO-CV AUC")
print("=" * 72)

single_aucs = []
for i, feat in enumerate(ALL_FEATURES):
    X_single = X[:, i : i + 1]
    if X_single.std() == 0:
        single_aucs.append((feat, 0.5))
        continue
    X_s = StandardScaler().fit_transform(X_single)
    lr = LogisticRegression(
        C=0.1,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        class_weight="balanced",
    )
    try:
        probs = cross_val_predict(lr, X_s, y, cv=loo, method="predict_proba")[:, 1]
        auc = roc_auc_score(y, probs)
        single_aucs.append((feat, auc))
    except Exception:
        single_aucs.append((feat, 0.5))

single_aucs.sort(key=lambda x: -x[1])
print(f"\n{'Feature':<25s} {'AUC':>8s} {'vs random':>10s}")
print("-" * 45)
for feat, auc in single_aucs:
    marker = "*" if auc > 0.60 else ""
    print(f"{feat:<25s} {auc:8.3f} {auc - 0.5:+10.3f} {marker}")

# ── Paper summary ───────────────────────────────────────────────────
print(f"\n{'=' * 72}")
print("PAPER-READY SUMMARY (CLEAN — no reward leakage)")
print("=" * 72)

above_chance = [(f, a) for f, a in single_aucs if a > 0.55]
print("\nDataset: 50 CyberGym exploit tasks, 6 successes (12.0%), 44 failures.")
print("Model: Feyospace-v1.1-small (~28B) under matched harness.\n")
print("Clean proxy prediction (behavioral features only):")
print(f"  Best LOO-CV AUC: {best_auc:.3f} ({best_model_name})")
print(f"  Bootstrap 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
print(f"  Individual features above AUC 0.55: {len(above_chance)}")

for feat, auc in above_chance:
    s_mean = X[y == 1, ALL_FEATURES.index(feat)].mean()
    f_mean = X[y == 0, ALL_FEATURES.index(feat)].mean()
    direction = "↑" if s_mean > f_mean else "↓"
    print(f"    {feat}: AUC={auc:.3f} ({direction} in successes)")

# ── Save structured results ─────────────────────────────────────────
results = {
    "note": ("CLEAN analysis — reward-leaking features (any_exit1, any_exit0_submit) excluded"),
    "dataset": {
        "n_tasks": len(y),
        "n_success": int(n_pos),
        "base_rate": 0.12,
    },
    "best_model": best_model_name,
    "best_loo_cv_auc": round(best_auc, 3),
    "bootstrap_ci_95": [round(ci_lo, 3), round(ci_hi, 3)],
    "all_models": {},
    "single_feature_aucs": {f: round(a, 3) for f, a in single_aucs},
    "top_features": [],
}

for name in model_probs:
    if name == "Baseline (random)":
        continue
    probs = model_probs[name]
    top6_idx = np.argsort(-probs)[:6]
    results["all_models"][name] = {
        "auc": round(roc_auc_score(y, probs), 3),
        "brier": round(brier_score_loss(y, probs), 3),
        "successes_in_top6": int(y[top6_idx].sum()),
    }

for idx in sorted_by_rank[:10]:
    feat = ALL_FEATURES[idx]
    results["top_features"].append(
        {
            "feature": feat,
            "mean_rank": round(float(mean_ranks[idx]), 1),
            "success_mean": round(float(X[y == 1, idx].mean()), 3),
            "failure_mean": round(float(X[y == 0, idx].mean()), 3),
        }
    )

out_path = FEATURES_PATH.replace("behavioral_features", "proxy_analysis_clean")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to {out_path}")
