from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from .config import settings
from .ingestion import fetch_usgs
from .clustering import cluster_earthquakes
from .population import population_exposure
from .osm import fetch_infrastructure


def _seed_events() -> list[dict]:
    now = datetime.now(timezone.utc)
    seeds = [
        ("seed-jp-1", 6.4, 32, "near the east coast of Honshu, Japan", 141.4, 37.4, 1),
        ("seed-jp-2", 5.8, 44, "near the east coast of Honshu, Japan", 141.8, 37.8, 4),
        ("seed-jp-3", 5.1, 28, "off the coast of Honshu, Japan", 142.1, 36.9, 12),
        ("seed-id-1", 6.1, 63, "south of Java, Indonesia", 107.1, -8.4, 2),
        ("seed-id-2", 5.6, 48, "south of Java, Indonesia", 106.5, -8.0, 8),
        ("seed-id-3", 5.0, 70, "Java, Indonesia", 107.5, -7.5, 18),
        ("seed-cl-1", 6.7, 35, "Atacama, Chile", -70.2, -23.5, 10),
        ("seed-cl-2", 5.4, 52, "Antofagasta, Chile", -69.8, -24.1, 16),
        ("seed-cl-3", 4.9, 40, "Atacama, Chile", -70.5, -23.1, 24),
        ("seed-nz-1", 5.7, 21, "Kermadec Islands, New Zealand", -177.8, -29.5, 3),
    ]
    return [{"id": i, "magnitude": m, "depth_km": d, "time": now-timedelta(days=age), "location": p, "place": p, "longitude": lon, "latitude": lat, "region": p.split(",")[-1].strip()} for i,m,d,p,lon,lat,age in seeds]


class DataStore:
    def __init__(self):
        self.events = _seed_events()
        self.clusters = cluster_earthquakes(self.events)
        self.population = population_exposure(self.events)
        self.infrastructure = []
        self.updated_at = datetime.now(timezone.utc)
        self.source_status = "Bundled open-data-shaped fallback; refresh pending"

    async def refresh(self, days: int = 30, min_magnitude: float = 4.5, include_osm: bool = True):
        try:
            self.events, self.updated_at = await fetch_usgs(days, min_magnitude)
            self.source_status = "Live USGS"
        except Exception as exc:
            self.source_status = f"USGS unavailable; bundled fallback active ({type(exc).__name__})"
        self.clusters = cluster_earthquakes(self.events)
        self.population = population_exposure(self.events)
        self.infrastructure = []
        if include_osm and self.events:
            try:
                recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                recent_events = [event for event in self.events if event["time"] >= recent_cutoff]
                target = max(recent_events or self.events, key=lambda event: event["magnitude"])
                live_assets, _ = await fetch_infrastructure(target)
                if live_assets:
                    self.infrastructure = live_assets
            except Exception:
                pass
        return {"events": len(self.events), "clusters": len(self.clusters), "assets": len(self.infrastructure), "source_status": self.source_status, "updated_at": self.updated_at}


store = DataStore()




