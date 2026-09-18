"""Compare cycle-distribution summaries, then save a separate SHM candidate.

Place next to features_v2.csv and run. Original models and results are preserved.
The saved model requires predict_bundle() below, which builds the derived features.
"""
from pathlib import Path
import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

BASE = "rf_range_power5_sum"
SCALE = 1e9
CURRENT = ["stress_min", "stress_max", "stress_mean", "stress_std", "stress_range",
           "stress_rms", "stress_p05", "stress_median", "stress_p95",
           "stress_p95_minus_p05", "mean_absolute_change", "rf_cycle_count",
           "rf_mean_range", "rf_std_range", "rf_max_range", "rf_range_power3_sum",
           "rf_range_power5_sum", "rf_range_power4_sum"]
RAW_COLUMNS = CURRENT + ["rf_range_power6_sum"]
SHAPE_COLUMNS = ["log_power5", "range_weighted_mean", "range_weighted_cv"]


def make_feature_sets(table):
    raw = table[RAW_COLUMNS].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(raw.to_numpy()).all():
        raise ValueError("Raw features contain missing or infinite values.")
    p4 = raw.rf_range_power4_sum.to_numpy()
    p5 = raw.rf_range_power5_sum.to_numpy()
    p6 = raw.rf_range_power6_sum.to_numpy()
    if (p4 <= 0).any() or (p5 <= 0).any() or (p6 <= 0).any():
        raise ValueError("This model requires positive fourth-, fifth-, and sixth-power sums.")
    variance_ratio = p6*p4/p5**2 - 1
    if (variance_ratio < -1e-8).any():
        raise ValueError("Power sums are inconsistent. Recheck feature extraction.")
    # These are exact moment summaries of the cycle ranges with weights count*range^4.
    # They use the recording only, never its damage label.
    shape = pd.DataFrame({
        "log_power5": np.log(p5),
        "range_weighted_mean": p5/p4,
        "range_weighted_cv": np.sqrt(np.maximum(0, variance_ratio)),
        "signal_mean": raw.stress_mean.to_numpy(),
        "signal_std": raw.stress_std.to_numpy(),
    }, index=raw.index)
    return {
        "current_18": raw[CURRENT],
        "shape_3": shape[SHAPE_COLUMNS],
        "shape_5": shape,
        "current_plus_shape": pd.concat([raw[CURRENT], shape[SHAPE_COLUMNS]], axis=1),
    }


def fit_correction(X, base, y):
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(X, np.log(y/base))
    return model


def predict_correction(model, X, base):
    result = base*np.exp(model.predict(X))
    if not np.isfinite(result).all():
        raise ValueError("Non-finite predictions; check the input recording/features.")
    return result


def predict_bundle(bundle, raw_features):
    sets = make_feature_sets(raw_features)
    X = sets[bundle["feature_set"]][bundle["model_feature_columns"]]
    base = raw_features[BASE].to_numpy(dtype=float) / bundle["base_scale"]
    return predict_correction(bundle["correction_model"], X, base)


def error_metrics(y, p):
    ape = 100*np.abs(p-y)/y
    return {"mape_percent": float(ape.mean()), "mae": float(np.abs(p-y).mean()),
            "worst_error_percent": float(ape.max()),
            "mean_signed_percentage_error": float(np.mean(100*(p-y)/y))}


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=folder / "features_v2.csv")
    parser.add_argument("--output-dir", type=Path, default=folder)
    args = parser.parse_args()
    d = pd.read_csv(args.input)
    required = set(RAW_COLUMNS) | {"filename", "damage"}
    if not required.issubset(d.columns):
        raise ValueError(f"Missing columns: {required-set(d.columns)}")
    if len(d) < 5 or d.filename.isna().any() or d.filename.duplicated().any():
        raise ValueError("Need at least five recordings with unique, nonmissing filenames.")
    sets = make_feature_sets(d)
    y = pd.to_numeric(d.damage, errors="raise").to_numpy(dtype=float)
    base = pd.to_numeric(d[BASE], errors="raise").to_numpy(dtype=float)/SCALE
    if not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("This experiment requires finite, positive damage labels.")
    summary = []; nested_summary = []; all_predictions = []; validation = None
    print("Comparing the current alpha=1 model with cycle-distribution features.\n")
    for seed in (42, 11, 73):
        outer = list(KFold(5, shuffle=True, random_state=seed).split(d))
        for name, X in sets.items():
            p = np.empty(len(d)); folds = np.zeros(len(d), dtype=int); baseline = np.empty(len(d))
            for fold, (tr, va) in enumerate(outer, 1):
                model = fit_correction(X.iloc[tr], base[tr], y[tr])
                p[va] = predict_correction(model, X.iloc[va], base[va])
                folds[va] = fold; baseline[va] = np.median(y[tr])
            metrics = error_metrics(y,p)
            summary.append({"split_seed":seed,"feature_set":name,**metrics})
            print(f"Split {seed} | {name:20s} | MAPE {metrics['mape_percent']:.3f}% | worst {metrics['worst_error_percent']:.3f}%")
            result = pd.DataFrame({"filename":d.filename,"validation_fold":folds,"actual_damage":y,
                "predicted_damage":p,"baseline_prediction":baseline,"absolute_percentage_error":100*np.abs(p-y)/y})
            all_predictions.append(result.assign(split_seed=seed,feature_set=name))
            if seed == 42 and name == "current_plus_shape": validation=result
        # Inner folds select a candidate; each outer fold remains unseen during selection.
        nested=np.empty(len(d)); choices=[]
        for tr,va in outer:
            inner=list(KFold(4,shuffle=True,random_state=123).split(tr)); scores={}
            for name,X in sets.items():
                p=np.empty(len(tr))
                for ti,vi in inner:
                    model=fit_correction(X.iloc[tr[ti]],base[tr[ti]],y[tr[ti]])
                    p[vi]=predict_correction(model,X.iloc[tr[vi]],base[tr[vi]])
                scores[name]=float(np.mean(np.abs(p-y[tr])/y[tr]))
            best=min(scores,key=scores.get); choices.append(best); X=sets[best]
            model=fit_correction(X.iloc[tr],base[tr],y[tr])
            nested[va]=predict_correction(model,X.iloc[va],base[va])
        nested_summary.append({"split_seed":seed,"chosen_feature_sets":"|".join(choices),**error_metrics(y,nested)})
    comparison=pd.DataFrame(summary)
    print("\nAverage MAPE across three splits (%):")
    print(comparison.groupby("feature_set").mape_percent.mean().sort_values().to_string())
    print("\nNested validation of choosing a feature set:")
    print(pd.DataFrame(nested_summary).to_string(index=False))
    print("\nAll splits reuse the same recordings. This is exploratory, not independent test evidence.")
    print("Nested validation here covers this candidate comparison, not every earlier development decision.")
    print("An improvement in MAPE does not imply every other metric improves on every split.")
    selected="current_plus_shape"; X=sets[selected]
    model=fit_correction(X,base,y)
    bundle={"model_type":"rainflow_ridge_cycle_shape", "correction_model":model,
        "feature_set":selected,"raw_feature_columns":RAW_COLUMNS,"model_feature_columns":X.columns.tolist(),
        "base_feature":BASE,"base_scale":SCALE,"ridge_alpha":1.0,
        "validation_mape":float(validation.absolute_percentage_error.mean()/100)}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    comparison.to_csv(args.output_dir / "shape_comparison.csv",index=False)
    pd.DataFrame(nested_summary).to_csv(args.output_dir / "nested_shape_results.csv",index=False)
    pd.concat(all_predictions,ignore_index=True).to_csv(args.output_dir / "shape_all_validation_predictions.csv",index=False)
    validation.to_csv(args.output_dir / "validation_results_shape.csv",index=False)
    path=args.output_dir / "shm_shape_model.joblib"
    joblib.dump(bundle,path)
    np.testing.assert_allclose(predict_bundle(joblib.load(path),d),predict_correction(model,X,base))
    print(f"\nSaved 21-input candidate and four result CSVs in {args.output_dir.resolve()}")
    print("Use predict_bundle() in this script: it constructs the derived features before prediction.")
    print("Previous files are unchanged. Re-running replaces only the shape-model outputs.")
    print("Official Test files were not used.")


if __name__ == "__main__":
    main()
