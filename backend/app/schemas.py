from datetime import datetime
from pydantic import BaseModel


class Earthquake(BaseModel):
    id: str
    magnitude: float
    depth_km: float
    time: datetime
    location: str
    place: str
    longitude: float
    latitude: float
    region: str


class Cluster(BaseModel):
    id: int
    status: str
    event_count: int
    max_magnitude: float
    average_depth_km: float
    latest_event_time: datetime
    region: str
    recent_count: int
    baseline_count: int
    geometry: dict
    event_ids: list[str]


class Attribution(BaseModel):
    name: str
    url: str
    license: str
    attribution: str
    updated_at: datetime | None = None

