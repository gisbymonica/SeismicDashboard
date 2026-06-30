from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from geoalchemy2 import Geometry


class Base(DeclarativeBase):
    pass


class EarthquakeRecord(Base):
    __tablename__ = "earthquakes"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    magnitude: Mapped[float] = mapped_column(Float)
    depth_km: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    place: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String)
    geom = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))

