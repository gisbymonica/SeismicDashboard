from datetime import datetime, timedelta, timezone
import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint, mapping

EARTH_RADIUS_KM = 6371.0088


def _hull(events: list[dict]) -> dict:
    points = [(e["longitude"], e["latitude"]) for e in events]
    longitudes = [point[0] for point in points]
    if max(longitudes) - min(longitudes) > 180:
        points = [(longitude + 360 if longitude < 0 else longitude, latitude) for longitude, latitude in points]
    geom = MultiPoint(points).convex_hull
    if geom.geom_type != "Polygon":
        geom = geom.buffer(1.25)
    else:
        geom = geom.buffer(0.35)
    return mapping(geom)


def cluster_earthquakes(events: list[dict], eps_km: float = 500, min_samples: int = 3) -> list[dict]:
    if len(events) < min_samples:
        return []
    coords = np.radians([[e["latitude"], e["longitude"]] for e in events])
    labels = DBSCAN(eps=eps_km / EARTH_RADIUS_KM, min_samples=min_samples, metric="haversine").fit_predict(coords)
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    clusters = []
    for label in sorted(set(labels)):
        if label == -1:
            continue
        members = [e for e, lab in zip(events, labels) if lab == label]
        recent = [e for e in members if e["time"] >= recent_cutoff]
        baseline = [e for e in members if e["time"] < recent_cutoff]
        if recent and baseline:
            status = "Persistent hotspot"
        elif recent:
            status = "Emerging hotspot"
        else:
            status = "Dying hotspot"
        regions = sorted({e["region"] for e in members})
        clusters.append({
            "id": int(label) + 1,
            "status": status,
            "event_count": len(members),
            "max_magnitude": max(e["magnitude"] for e in members),
            "average_depth_km": round(sum(e["depth_km"] for e in members) / len(members), 1),
            "latest_event_time": max(e["time"] for e in members),
            "region": " / ".join(regions[:2]),
            "recent_count": len(recent),
            "baseline_count": len(baseline),
            "geometry": _hull(members),
            "event_ids": [e["id"] for e in members],
        })
    return sorted(clusters, key=lambda c: (c["status"] != "Emerging hotspot", -c["event_count"]))


