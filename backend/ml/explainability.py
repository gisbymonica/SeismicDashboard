from __future__ import annotations
import numpy as np
from .hotspot_dataset import FEATURE_LABELS


def global_importance(model, feature_names: list[str]) -> list[dict]:
    estimator = model if hasattr(model, "feature_importances_") else getattr(model, "estimator", model)
    values = getattr(estimator, "feature_importances_", np.zeros(len(feature_names)))
    rows = []
    for name, score in zip(feature_names, values):
        label, interpretation = FEATURE_LABELS[name]
        rows.append({"feature": name, "name": label, "importance": round(float(score), 4), "interpretation": interpretation})
    return sorted(rows, key=lambda row: row["importance"], reverse=True)


def local_contributions(row, importance: list[dict], means: dict, stds: dict, limit: int = 5) -> list[dict]:
    result = []
    for item in importance:
        name = item["feature"]
        z = abs((float(row[name]) - means.get(name, 0.0)) / max(stds.get(name, 1.0), 1e-6))
        result.append({**item, "value": round(float(row[name]), 3), "contribution_score": round(item["importance"] * min(z, 4.0), 4)})
    return sorted(result, key=lambda item: item["contribution_score"], reverse=True)[:limit]

