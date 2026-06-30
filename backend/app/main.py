from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import asyncio
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .store import store
from .clustering import cluster_earthquakes
from .ml_service import hotspot_service


async def bootstrap_data_and_model():
    await store.refresh(365, 4.5, include_osm=True)
    await asyncio.to_thread(hotspot_service.load_or_train, store.events, store.population, store.infrastructure)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bootstrap_data_and_model())
    yield


app = FastAPI(title="Earthquake Exposure Intelligence API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"] , allow_methods=["*"] , allow_headers=["*"])


def filtered_events(days: int, min_magnitude: float, min_depth: float, max_depth: float, region: str | None):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [e for e in store.events if e["time"] >= cutoff and e["magnitude"] >= min_magnitude and min_depth <= e["depth_km"] <= max_depth and (not region or region.lower() in e["region"].lower())]


def sources():
    return [
        {"name":"USGS Earthquake Catalog", "url":"https://earthquake.usgs.gov/fdsnws/event/1/", "license":"Public domain (U.S. Government work)", "attribution":"U.S. Geological Survey", "updated_at":store.updated_at},
        {"name":"Natural Earth Populated Places", "url":"https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-populated-places/", "license":"Public domain", "attribution":"Natural Earth", "updated_at":None},
        {"name":"OpenStreetMap", "url":"https://www.openstreetmap.org/copyright", "license":"ODbL 1.0", "attribution":"© OpenStreetMap contributors", "updated_at":store.updated_at if store.infrastructure else None},
    ]


@app.get("/api/health")
def health(): return {"status": "ok", "source_status": store.source_status}


@app.get("/api/earthquakes")
def earthquakes(days: int = Query(30, enum=[30,90,365]), min_magnitude: float = 4.5, min_depth: float = 0, max_depth: float = 700, region: str | None = None):
    return {"items": filtered_events(days,min_magnitude,min_depth,max_depth,region), "updated_at":store.updated_at, "source_status":store.source_status, "sources":sources()}


@app.get("/api/clusters")
def clusters(days: int = Query(30, enum=[30,90,365])):
    events = filtered_events(days, 4.5, 0, 700, None)
    items = store.clusters if days == 365 else cluster_earthquakes(events)
    return {"items":items, "method":{"algorithm":"DBSCAN","eps_km":500,"min_samples":3,"recent_window_days":7}, "disclaimer":"Historical pattern analysis only. This is not earthquake prediction."}


@app.get("/api/exposure/population")
def population(days: int = Query(30, enum=[30,90,365])):
    ids = {e["id"] for e in filtered_events(days, 4.5, 0, 700, None)}
    return {"items":[p for p in store.population if p["earthquake_id"] in ids], "approximate":True, "method":"Natural Earth populated-place point-sum MVP fallback", "sources":sources()[1:2]}


@app.get("/api/exposure/infrastructure")
def infrastructure(days: int = Query(30, enum=[30,90,365])):
    ids = {e["id"] for e in filtered_events(days, 4.5, 0, 700, None)}
    return {"items":[a for a in store.infrastructure if a["earthquake_id"] in ids], "categories":["Hospital","Power plant","Substation","Dam","Airport","Fire station","Police"], "sources":sources()[2:3]}


@app.get("/api/summary")
def summary():
    active = sum(c["status"] in ("Emerging hotspot","Persistent hotspot") for c in store.clusters)
    exposed_pop = sum(p["population_200km"] for p in store.population)
    highest = max(store.events, key=lambda e:e["magnitude"], default=None)
    return {"total_earthquakes":len(store.events),"active_clusters":active,"estimated_exposed_population":exposed_pop,"exposed_critical_assets":len(store.infrastructure),"highest_risk_recent_event":highest,"updated_at":store.updated_at,"source_status":store.source_status,"sources":sources(),"disclaimer":"Exposure does not mean damage. Historical analysis only; not earthquake prediction."}


@app.post("/api/refresh-data")
async def refresh_data(days: int = 30, min_magnitude: float = 4.5, include_osm: bool = True): return await store.refresh(days,min_magnitude,include_osm)








@app.get("/api/ml/hotspot-predictions")
def hotspot_predictions():
    return {"items": hotspot_service.predictions, "status": hotspot_service.status,
            "title": "Exploratory next-hotspot likelihood based on historical USGS patterns",
            "thresholds": {"low": "< 0.35", "medium": "0.35–0.65", "high": "> 0.65"},
            "disclaimer": "This is not an earthquake prediction or public warning system."}

@app.get("/api/ml/feature-importance")
def feature_importance():
    return {"items": hotspot_service.importance(), "status": hotspot_service.status,
            "method": "Random Forest impurity-based global feature importance"}

@app.get("/api/ml/model-metadata")
def model_metadata():
    return hotspot_service.metadata()

@app.post("/api/ml/train")
async def train_hotspot_model(magnitude_threshold: float = 4.5, grid_size: float = 2.0):
    if hotspot_service.status == "training":
        return {"status": "training", "message": "A training run is already in progress."}
    return await asyncio.to_thread(hotspot_service.train, store.events, store.population, store.infrastructure, magnitude_threshold, grid_size)


@app.get("/api/ml/hotspot-predictions/{cell_id}/exposure")
async def hotspot_cell_exposure(cell_id: str):
    try:
        return await hotspot_service.enrich_exposure(cell_id)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Hotspot grid cell not found")
