from datetime import datetime, timedelta, timezone
from app.clustering import cluster_earthquakes
from app.population import population_exposure


def event(i, lat, lon, days=1):
    return {"id":str(i),"magnitude":5+i/10,"depth_km":20,"time":datetime.now(timezone.utc)-timedelta(days=days),"location":"test","place":"test, Japan","longitude":lon,"latitude":lat,"region":"Japan"}


def test_dbscan_cluster_and_status():
    clusters = cluster_earthquakes([event(1,35,140),event(2,35.2,140.2),event(3,35.1,140.1,10)])
    assert len(clusters) == 1
    assert clusters[0]["status"] == "Persistent hotspot"


def test_population_has_three_buffers():
    row = population_exposure([event(1,35.676,139.650)])[0]
    assert row["population_50km"] > 0
    assert row["population_50km"] <= row["population_100km"] <= row["population_200km"]

