from datetime import datetime, timedelta, timezone
from ml.hotspot_dataset import FEATURES, build_hotspot_dataset, build_prediction_frame


def synthetic_events():
    start = datetime.now(timezone.utc) - timedelta(days=180)
    events = []
    for i in range(90):
        when = start + timedelta(days=i * 2)
        events.append({"id": f"e{i}", "magnitude": 4.6 + (i % 5) * .1, "depth_km": 10 + i % 40,
                       "time": when, "location": "test", "place": "test, Region",
                       "longitude": 140.2 + (i % 3) * .1, "latitude": 35.2 + (i % 2) * .1, "region": "Region"})
    return events


def test_time_window_dataset_and_schema():
    X, y, times, identities = build_hotspot_dataset(synthetic_events())
    assert list(X.columns) == FEATURES
    assert len(X) == len(y) == len(times) == len(identities)
    assert y.sum() > 0
    assert times.is_monotonic_increasing


def test_prediction_grid_has_polygon_bounds():
    X, identities = build_prediction_frame(synthetic_events())
    assert len(X) == len(identities)
    assert len(identities[0]["bounds"]) == 4

def test_grid_population_context_is_cell_centered():
    from ml.predict_hotspots import population_context
    context = population_context(35.676, 139.650)
    assert context["population"] > 0
    assert any("Tokyo" in place for place in context["matched_places"])
