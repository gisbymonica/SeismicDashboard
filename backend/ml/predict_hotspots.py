from __future__ import annotations
from functools import lru_cache
import geopandas as gpd
import numpy as np
from .hotspot_dataset import build_prediction_frame
from .train_random_forest import load_artifact
from .explainability import local_contributions
from app.config import settings
from app.population import PLACES, distance_km


@lru_cache(maxsize=1)
def _population_places() -> tuple[list[tuple], str]:
    path = settings.data_dir / "raw" / "ne_10m_populated_places.zip"
    if path.exists():
        frame = gpd.read_file(f"zip://{path}")
        places = [(str(row.NAME), str(row.ADM0NAME), max(0, int(row.POP_MAX or 0)),
                   float(row.LATITUDE), float(row.LONGITUDE)) for row in frame.itertuples()]
        return places, "Natural Earth 1:10m populated-places point-sum around grid-cell center"
    return PLACES, "Bundled Natural Earth populated-places subset point-sum around grid-cell center"


def population_context(lat: float, lon: float, radius_km: float = 200) -> dict:
    places, method = _population_places()
    matched = [(city, country, population) for city, country, population, place_lat, place_lon in places
               if population > 0 and distance_km(lat, lon, place_lat, place_lon) <= radius_km]
    matched.sort(key=lambda item: item[2], reverse=True)
    return {"population": int(sum(item[2] for item in matched)),
            "matched_places": [f"{item[0]}, {item[1]}" for item in matched[:8]],
            "place_count": len(matched), "radius_km": radius_km, "approximate": True,
            "method": method}

def _polygon(bounds: list[float]) -> dict:
    west, south, east, north = bounds
    return {"type": "Polygon", "coordinates": [[[west,south],[east,south],[east,north],[west,north],[west,south]]]}


def predict_hotspots(events: list[dict], population: list[dict], infrastructure: list[dict], limit: int = 500) -> list[dict]:
    artifact = load_artifact()
    grid_size = float(artifact["metadata"]["grid_size_degrees"])
    X, identities = build_prediction_frame(events, grid_size)
    probabilities = artifact["model"].predict_proba(X[artifact["features"]])[:, 1]
    importance = artifact["importance"]
    event_cells = {}
    for event in events:
        cell = (int((event["latitude"] + 90)//grid_size), int((event["longitude"] + 180)//grid_size))
        event_cells.setdefault(cell, []).append(event)
    order = np.argsort(probabilities)[::-1][:limit]
    predictions = []
    for rank, idx in enumerate(order):
        identity, row, probability = identities[int(idx)], X.iloc[int(idx)], float(probabilities[int(idx)])
        lat, lon = identity["center"]
        cell_events = event_cells.get(tuple(identity["cell"]), [])
        region = max(cell_events, key=lambda event: event["magnitude"])["region"] if cell_events else "Adjacent seismic grid cell"
        pop_context = population_context(lat, lon)
        category = "High" if probability > .65 else "Medium" if probability >= .35 else "Low"
        predictions.append({
            "id": f"grid-{identity['cell'][0]}-{identity['cell'][1]}", "rank": rank + 1,
            "likelihood_score": round(probability, 4), "category": category, "region": region,
            "center_latitude": lat, "center_longitude": lon, "bounds": identity["bounds"],
            "geometry": _polygon(identity["bounds"]), "recent_event_count": int(row["event_count_30d"]),
            "max_recent_magnitude": round(float(row["max_magnitude_30d"]), 1),
            "nearby_exposed_population": pop_context["population"], "population_matched_places": pop_context["matched_places"],
            "nearby_critical_infrastructure": None, "infrastructure_exposure_status": "not_loaded",
            "top_contributing_features": local_contributions(row, importance, artifact["means"], artifact["stds"]),
        })
    return predictions


