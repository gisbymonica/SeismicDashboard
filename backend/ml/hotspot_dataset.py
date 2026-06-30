from __future__ import annotations
from datetime import datetime, timedelta, timezone
from math import floor
import numpy as np
import pandas as pd

FEATURES = [
    "event_count_7d", "event_count_30d", "event_count_90d",
    "max_magnitude_30d", "mean_magnitude_30d", "max_depth_30d",
    "mean_depth_30d", "seismic_energy_30d", "days_since_last_event",
    "distance_to_nearest_recent_cluster", "historical_event_density_365d",
    "recent_cluster_status_encoded",
]

FEATURE_LABELS = {
    "event_count_7d": ("Recent 7-day event count", "More very recent activity increased the model's active-cell signal."),
    "event_count_30d": ("Recent 30-day event count", "Cells with more recent seismic activity were more often active in the following window."),
    "event_count_90d": ("Recent 90-day event count", "Sustained activity provides a broader baseline than the latest month."),
    "max_magnitude_30d": ("Max magnitude in 30 days", "Larger recent events influenced how the classifier separated active cells."),
    "mean_magnitude_30d": ("Mean magnitude in 30 days", "The typical magnitude of recent activity contributed to the historical pattern."),
    "max_depth_30d": ("Maximum recent depth", "The deepest recent event helped distinguish different seismic settings."),
    "mean_depth_30d": ("Mean recent depth", "Average depth captures differences between shallow and subduction-zone activity."),
    "seismic_energy_30d": ("Seismic energy released", "Higher recent energy release was associated with subsequent active-cell labels."),
    "days_since_last_event": ("Days since last event", "Recency helps distinguish currently active cells from quieter historical cells."),
    "distance_to_nearest_recent_cluster": ("Distance to recent cluster", "Cells nearer concentrations of recent events were more often classified as active."),
    "historical_event_density_365d": ("Historical event density", "Longer-term event density represents persistent seismic activity."),
    "recent_cluster_status_encoded": ("Recent cluster pattern", "An encoded emerging, persistent, or fading activity pattern informed the classifier."),
}


def cell_for(lat: float, lon: float, grid_size: float) -> tuple[int, int]:
    return floor((lat + 90) / grid_size), floor((lon + 180) / grid_size)


def cell_bounds(cell: tuple[int, int], grid_size: float) -> tuple[float, float, float, float]:
    row, col = cell
    south, west = row * grid_size - 90, col * grid_size - 180
    return west, south, west + grid_size, south + grid_size


def cell_center(cell: tuple[int, int], grid_size: float) -> tuple[float, float]:
    west, south, east, north = cell_bounds(cell, grid_size)
    return (south + north) / 2, (west + east) / 2


def _event_frame(events: list[dict], grid_size: float) -> pd.DataFrame:
    rows = []
    for event in events:
        when = pd.Timestamp(event["time"])
        if when.tzinfo is None:
            when = when.tz_localize("UTC")
        else:
            when = when.tz_convert("UTC")
        cell = cell_for(event["latitude"], event["longitude"], grid_size)
        rows.append({**event, "time": when, "cell_row": cell[0], "cell_col": cell[1]})
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def candidate_cells(frame: pd.DataFrame, grid_size: float) -> list[tuple[int, int]]:
    observed = {(int(r), int(c)) for r, c in frame[["cell_row", "cell_col"]].itertuples(index=False, name=None)}
    candidates = set(observed)
    rows, cols = int(180 / grid_size), int(360 / grid_size)
    for row, col in observed:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (row + dr, (col + dc) % cols)
            if 0 <= neighbor[0] < rows:
                candidates.add(neighbor)
    return sorted(candidates)


def _haversine_to_many(lat: float, lon: float, centers: np.ndarray) -> float:
    if not len(centers):
        return 2000.0
    lat1, lon1 = np.radians(lat), np.radians(lon)
    lat2, lon2 = np.radians(centers[:, 0]), np.radians(centers[:, 1])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return float(np.min(6371.0088 * 2 * np.arcsin(np.sqrt(a))))


def _features_for_cell(cell_frame: pd.DataFrame, anchor: pd.Timestamp, center: tuple[float, float], cluster_centers: np.ndarray, grid_size: float) -> dict:
    past = cell_frame[cell_frame.time <= anchor]
    d7 = past[past.time > anchor - pd.Timedelta(days=7)]
    d30 = past[past.time > anchor - pd.Timedelta(days=30)]
    d90 = past[past.time > anchor - pd.Timedelta(days=90)]
    d365 = past[past.time > anchor - pd.Timedelta(days=365)]
    baseline30 = d30[d30.time <= anchor - pd.Timedelta(days=7)]
    if len(d7) and len(baseline30): status = 2
    elif len(d7): status = 1
    elif len(baseline30): status = -1
    else: status = 0
    energies = np.power(10.0, 1.5 * d30.magnitude.to_numpy() + 4.8) if len(d30) else np.array([])
    return {
        "event_count_7d": len(d7), "event_count_30d": len(d30), "event_count_90d": len(d90),
        "max_magnitude_30d": float(d30.magnitude.max()) if len(d30) else 0.0,
        "mean_magnitude_30d": float(d30.magnitude.mean()) if len(d30) else 0.0,
        "max_depth_30d": float(d30.depth_km.max()) if len(d30) else 0.0,
        "mean_depth_30d": float(d30.depth_km.mean()) if len(d30) else 0.0,
        "seismic_energy_30d": float(np.log10(energies.sum())) if len(energies) else 0.0,
        "days_since_last_event": min(365.0, float((anchor - past.time.max()).total_seconds()/86400)) if len(past) else 365.0,
        "distance_to_nearest_recent_cluster": _haversine_to_many(center[0], center[1], cluster_centers),
        "historical_event_density_365d": float(len(d365) / (grid_size * grid_size)),
        "recent_cluster_status_encoded": status,
    }


def _cluster_centers(frame: pd.DataFrame, anchor: pd.Timestamp, grid_size: float) -> np.ndarray:
    recent = frame[(frame.time <= anchor) & (frame.time > anchor - pd.Timedelta(days=30))]
    if recent.empty:
        return np.empty((0, 2))
    dense = recent.groupby(["cell_row", "cell_col"]).size()
    cells = [idx for idx, count in dense.items() if count >= 3]
    return np.array([cell_center((int(r), int(c)), grid_size) for r, c in cells]) if cells else np.empty((0, 2))


def build_hotspot_dataset(events: list[dict], magnitude_threshold: float = 4.5, grid_size: float = 2.0, feature_window_days: int = 30, prediction_window_days: int = 7) -> tuple[pd.DataFrame, pd.Series, pd.Series, list[dict]]:
    frame = _event_frame(events, grid_size)
    if frame.empty:
        raise ValueError("No events available for hotspot dataset")
    cells = candidate_cells(frame, grid_size)
    grouped = {(int(r), int(c)): group for (r, c), group in frame.groupby(["cell_row", "cell_col"])}
    start = frame.time.min() + pd.Timedelta(days=90)
    end = frame.time.max() - pd.Timedelta(days=prediction_window_days)
    anchors = pd.date_range(start=start, end=end, freq=f"{prediction_window_days}D", tz="UTC")
    rows, labels, times, identities = [], [], [], []
    empty = frame.iloc[0:0]
    for anchor in anchors:
        centers = _cluster_centers(frame, anchor, grid_size)
        future = frame[(frame.time > anchor) & (frame.time <= anchor + pd.Timedelta(days=prediction_window_days)) & (frame.magnitude >= magnitude_threshold)]
        active = {(int(r), int(c)) for r, c in future[["cell_row", "cell_col"]].itertuples(index=False, name=None)}
        for cell in cells:
            center = cell_center(cell, grid_size)
            rows.append(_features_for_cell(grouped.get(cell, empty), anchor, center, centers, grid_size))
            labels.append(1 if cell in active else 0)
            times.append(anchor)
            identities.append({"cell": cell, "center": center})
    return pd.DataFrame(rows, columns=FEATURES), pd.Series(labels, name="target"), pd.Series(times, name="anchor"), identities


def build_prediction_frame(events: list[dict], grid_size: float = 2.0) -> tuple[pd.DataFrame, list[dict]]:
    frame = _event_frame(events, grid_size)
    anchor = frame.time.max()
    centers = _cluster_centers(frame, anchor, grid_size)
    grouped = {(int(r), int(c)): group for (r, c), group in frame.groupby(["cell_row", "cell_col"])}
    empty = frame.iloc[0:0]
    rows, identities = [], []
    for cell in candidate_cells(frame, grid_size):
        center = cell_center(cell, grid_size)
        rows.append(_features_for_cell(grouped.get(cell, empty), anchor, center, centers, grid_size))
        west, south, east, north = cell_bounds(cell, grid_size)
        identities.append({"cell": cell, "center": center, "bounds": [west, south, east, north]})
    return pd.DataFrame(rows, columns=FEATURES), identities

