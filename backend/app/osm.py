from datetime import datetime, timezone
import httpx
from .config import settings

CATEGORIES = {
    "hospital": ('["amenity"="hospital"]', "Hospital"),
    "power_plant": ('["power"="plant"]', "Power plant"),
    "substation": ('["power"="substation"]', "Substation"),
    "dam": ('["waterway"="dam"]', "Dam"),
    "dam_man_made": ('["man_made"="dam"]', "Dam"),
    "airport": ('["aeroway"="aerodrome"]', "Airport"),
    "fire_station": ('["amenity"="fire_station"]', "Fire station"),
    "police": ('["amenity"="police"]', "Police"),
}


def _query(lat: float, lon: float, radius_m: int = 200000) -> str:
    clauses = "".join(f"nwr{selector}(around:{radius_m},{lat},{lon});" for selector, _ in CATEGORIES.values())
    return f"[out:json][timeout:45];({clauses});out center tags;"


async def fetch_infrastructure(event: dict) -> tuple[list[dict], datetime]:
    headers = {"User-Agent": "EarthquakeExposureIntelligence/1.0", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=90, headers=headers) as client:
        response = await client.get(settings.overpass_url, params={"data": _query(event["latitude"], event["longitude"])})
        response.raise_for_status()
        payload = response.json()
    assets, seen = [], set()
    from .population import distance_km
    for element in payload.get("elements", []):
        key = (element.get("type"), element.get("id"))
        if key in seen:
            continue
        seen.add(key)
        tags = element.get("tags", {})
        lat = element.get("lat", element.get("center", {}).get("lat"))
        lon = element.get("lon", element.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        category = next((label for selector, label in CATEGORIES.values() if selector.strip('[]').replace('"','').split('=') == [next(iter(tags.keys()), ''), next(iter(tags.values()), '')]), None)
        if not category:
            if tags.get("amenity") == "hospital": category = "Hospital"
            elif tags.get("power") == "plant": category = "Power plant"
            elif tags.get("power") == "substation": category = "Substation"
            elif tags.get("waterway") == "dam" or tags.get("man_made") == "dam": category = "Dam"
            elif tags.get("aeroway") == "aerodrome": category = "Airport"
            elif tags.get("amenity") == "fire_station": category = "Fire station"
            elif tags.get("amenity") == "police": category = "Police"
        if category:
            distance = round(distance_km(event["latitude"], event["longitude"], lat, lon), 1)
            assets.append({"id": f"osm-{element['type']}-{element['id']}", "earthquake_id": event["id"], "category": category, "name": tags.get("name", f"Unnamed {category.lower()}"), "longitude": lon, "latitude": lat, "distance_km": distance})
    return assets, datetime.now(timezone.utc)


def fallback_infrastructure(events: list[dict]) -> list[dict]:
    categories = ["Hospital", "Power plant", "Substation", "Dam", "Airport", "Fire station", "Police"]
    assets = []
    for i, event in enumerate(events[:12]):
        for j in range(2 + (i % 4)):
            assets.append({"id": f"fallback-{i}-{j}", "earthquake_id": event["id"], "category": categories[(i+j)%len(categories)], "name": f"OpenStreetMap asset {i+1}-{j+1}", "longitude": event["longitude"] + .12*(j+1), "latitude": event["latitude"] + .08*(j+1), "distance_km": round(18 + 31*j + 3*i, 1), "is_fallback": True})
    return assets


