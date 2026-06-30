from __future__ import annotations
from datetime import datetime, timezone
import json
import pickle
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from .hotspot_dataset import FEATURES, build_hotspot_dataset
from .explainability import global_importance

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "random_forest_hotspot.pkl"
SCHEMA_PATH = MODEL_DIR / "hotspot_features.json"
METADATA_PATH = MODEL_DIR / "hotspot_metadata.json"
DISCLAIMER = "This is not an earthquake prediction or public warning system."
LONG_DISCLAIMER = "This model identifies historical-pattern-based hotspot likelihood. It does not predict exact earthquake timing, magnitude, or epicenter and must not be used for emergency response or public safety decisions."


def train_random_forest(events: list[dict], magnitude_threshold: float = 4.5, grid_size: float = 2.0, feature_window_days: int = 30, prediction_window_days: int = 7) -> dict:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    X, y, times, _ = build_hotspot_dataset(events, magnitude_threshold, grid_size, feature_window_days, prediction_window_days)
    unique_times = sorted(times.unique())
    if len(unique_times) < 5:
        raise ValueError("At least five time windows are required")
    split_time = unique_times[max(1, int(len(unique_times) * 0.8) - 1)]
    train_mask, test_mask = times <= split_time, times > split_time
    X_train, y_train, X_test, y_test = X[train_mask], y[train_mask], X[test_mask], y[test_mask]
    model = RandomForestClassifier(n_estimators=220, max_depth=14, min_samples_leaf=2, class_weight="balanced", n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]
    predicted = (probabilities >= 0.5).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
        "precision": round(float(precision_score(y_test, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predicted, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, predicted, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4) if len(np.unique(y_test)) > 1 else None,
    }
    importance = global_importance(model, FEATURES)
    event_times = [event["time"] for event in events]
    metadata = {
        "model_type": "RandomForestClassifier", "training_date": datetime.now(timezone.utc).isoformat(),
        "data_date_range": {"start": min(event_times).isoformat(), "end": max(event_times).isoformat()},
        "magnitude_threshold": magnitude_threshold, "grid_size_degrees": grid_size,
        "historical_lookback_days": 365, "feature_window_days": feature_window_days,
        "prediction_window_days": prediction_window_days, "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)), "positive_rate_train": round(float(y_train.mean()), 5),
        **metrics, "title": "Exploratory next-hotspot likelihood based on historical USGS patterns",
        "disclaimer": DISCLAIMER, "limitations": LONG_DISCLAIMER,
        "probability_calibration": "Not applied in MVP; scores are classifier likelihoods and not prediction certainty.",
        "split_strategy": "Chronological 80/20 holdout by time window",
    }
    artifact = {"model": model, "features": FEATURES, "metadata": metadata, "importance": importance,
                "means": X_train.mean().to_dict(), "stds": X_train.std().fillna(1).to_dict()}
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(artifact, handle)
    SCHEMA_PATH.write_text(json.dumps({"features": FEATURES, "labels": {item["feature"]: item["name"] for item in importance}}, indent=2))
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    return metadata


def load_artifact() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Hotspot model has not been trained")
    with MODEL_PATH.open("rb") as handle:
        return pickle.load(handle)
