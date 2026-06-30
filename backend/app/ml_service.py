from __future__ import annotations
from datetime import datetime, timezone
from threading import Lock
from ml.train_random_forest import train_random_forest, load_artifact, MODEL_PATH
from ml.predict_hotspots import predict_hotspots, population_context
from app.osm import fetch_infrastructure


class HotspotService:
    def __init__(self):
        self.status = "not_trained"
        self.last_error: str | None = None
        self.predictions: list[dict] = []
        self.exposure_cache: dict[str, dict] = {}
        self._lock = Lock()

    def train(self, events: list[dict], population: list[dict], infrastructure: list[dict], magnitude_threshold: float = 4.5, grid_size: float = 2.0) -> dict:
        if not self._lock.acquire(blocking=False):
            return {"status": "training", "message": "A training run is already in progress."}
        try:
            self.status, self.last_error = "training", None
            metadata = train_random_forest(events, magnitude_threshold=magnitude_threshold, grid_size=grid_size)
            self.predictions = predict_hotspots(events, population, infrastructure)
            self.status = "ready"
            return {"status": self.status, **metadata, "prediction_cells": len(self.predictions)}
        except Exception as exc:
            self.status, self.last_error = "error", f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._lock.release()

    def load_or_train(self, events: list[dict], population: list[dict], infrastructure: list[dict]) -> dict:
        if MODEL_PATH.exists():
            artifact = load_artifact()
            self.predictions = predict_hotspots(events, population, infrastructure)
            self.status, self.last_error = "ready", None
            return {"status": self.status, **artifact["metadata"], "prediction_cells": len(self.predictions)}
        return self.train(events, population, infrastructure)
    async def enrich_exposure(self, cell_id: str) -> dict:
        prediction = next((item for item in self.predictions if item["id"] == cell_id), None)
        if prediction is None:
            raise KeyError(cell_id)
        if cell_id in self.exposure_cache:
            return self.exposure_cache[cell_id]
        event = {"id": cell_id, "latitude": prediction["center_latitude"],
                 "longitude": prediction["center_longitude"]}
        pop = population_context(event["latitude"], event["longitude"])
        try:
            assets, updated_at = await fetch_infrastructure(event)
            categories: dict[str, int] = {}
            for asset in assets:
                categories[asset["category"]] = categories.get(asset["category"], 0) + 1
            result = {"cell_id": cell_id, "nearby_exposed_population": pop["population"],
                      "population_matched_places": pop["matched_places"],
                      "nearby_critical_infrastructure": len(assets),
                      "infrastructure_by_category": categories, "infrastructure_exposure_status": "loaded",
                      "radius_km": 200, "updated_at": updated_at.isoformat(),
                      "population_approximate": True, "osm_attribution": "© OpenStreetMap contributors"}
        except Exception as exc:
            result = {"cell_id": cell_id, "nearby_exposed_population": pop["population"],
                      "population_matched_places": pop["matched_places"],
                      "nearby_critical_infrastructure": None, "infrastructure_by_category": {},
                      "infrastructure_exposure_status": "unavailable", "radius_km": 200,
                      "error": type(exc).__name__, "population_approximate": True}
        self.exposure_cache[cell_id] = result
        prediction.update(result)
        return result
    def metadata(self) -> dict:
        if self.status == "ready" and MODEL_PATH.exists():
            return {"status": self.status, **load_artifact()["metadata"]}
        return {"status": self.status, "error": self.last_error,
                "title": "Exploratory next-hotspot likelihood based on historical USGS patterns",
                "disclaimer": "This is not an earthquake prediction or public warning system."}

    def importance(self) -> list[dict]:
        return load_artifact()["importance"][:5] if self.status == "ready" and MODEL_PATH.exists() else []


hotspot_service = HotspotService()


