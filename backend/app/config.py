from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://seismic:seismic@localhost:5432/seismic"
    usgs_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    default_days: int = 30
    default_min_magnitude: float = 4.5


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "cache").mkdir(parents=True, exist_ok=True)

