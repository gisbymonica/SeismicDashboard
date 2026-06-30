# Earthquake Exposure Intelligence

A production-shaped, open-data-only geospatial dashboard for three explainable analyses: earthquake clustering, approximate population exposure, and critical infrastructure exposure.

## Run with Docker

```bash
docker compose up --build
```

Open http://localhost:5173. The backend API and Swagger UI are available at http://localhost:8000/docs.

The backend attempts a live USGS refresh at startup. It remains usable with a clearly labelled bundled fallback if the source is temporarily unavailable. Use `POST /api/refresh-data?days=30&min_magnitude=4.5&include_osm=true` for an explicit USGS and Overpass refresh.

## Local development

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Architecture

- `backend/app`: FastAPI, USGS ingestion, haversine DBSCAN, population approximation, Overpass client, and PostGIS model
- `frontend/src`: React/TypeScript dashboard, MapLibre map, Plotly analytics, and filters
- `data`: cache mount for raw/processed open data
- `docs`: sources, methodology, and limitations

PostGIS is provisioned in Docker Compose and the spatial model is defined for durable deployments. The clean MVP keeps a memory-resident analytical store so source outages do not prevent startup.


## Exploratory hotspot likelihood

The optional fourth module classifies 2° grid cells with a time-split `RandomForestClassifier` trained on the latest 365-day USGS catalog. It exposes:

- `GET /api/ml/hotspot-predictions`
- `GET /api/ml/feature-importance`
- `GET /api/ml/model-metadata`
- `POST /api/ml/train?magnitude_threshold=4.5&grid_size=2`

The trained artifact is persisted at `backend/models/random_forest_hotspot.pkl`; its schema and metadata are stored beside it. Scores are exploratory historical-pattern likelihoods, not earthquake predictions, early warnings, or prediction certainty.
