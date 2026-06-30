from datetime import datetime, timedelta, timezone
import httpx
from .config import settings


def region_from_place(place: str) -> str:
    if not place:
        return "Open ocean / unspecified"
    return place.split(",")[-1].strip() if "," in place else place


async def fetch_usgs(days: int, min_magnitude: float) -> tuple[list[dict], datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    params = {
        "format": "geojson",
        "starttime": start.isoformat(),
        "endtime": end.isoformat(),
        "minmagnitude": min_magnitude,
        "orderby": "time",
        "limit": 20000,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(settings.usgs_base_url, params=params)
        response.raise_for_status()
        payload = response.json()
    events = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 3 or props.get("mag") is None:
            continue
        place = props.get("place") or "Unspecified location"
        events.append({
            "id": feature["id"],
            "magnitude": round(float(props["mag"]), 1),
            "depth_km": round(float(coords[2]), 1),
            "time": datetime.fromtimestamp(props["time"] / 1000, timezone.utc),
            "location": place,
            "place": place,
            "longitude": float(coords[0]),
            "latitude": float(coords[1]),
            "region": region_from_place(place),
        })
    return events, datetime.fromtimestamp(payload.get("metadata", {}).get("generated", int(end.timestamp()*1000)) / 1000, timezone.utc)

