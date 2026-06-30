from math import asin, cos, radians, sin, sqrt

# Natural Earth populated-places MVP subset, population values are approximate.
PLACES = [
    ("Tokyo", "Japan", 35676000, 35.676, 139.650), ("Jakarta", "Indonesia", 30539000, -6.208, 106.846),
    ("Manila", "Philippines", 24922000, 14.600, 120.984), ("Mexico City", "Mexico", 21581000, 19.433, -99.133),
    ("Delhi", "India", 31870000, 28.614, 77.209), ("Lima", "Peru", 10320000, -12.046, -77.043),
    ("Santiago", "Chile", 6269000, -33.449, -70.669), ("Istanbul", "Türkiye", 15154000, 41.008, 28.978),
    ("Los Angeles", "United States", 13200000, 34.052, -118.244), ("Tehran", "Iran", 9141000, 35.689, 51.389),
    ("Kathmandu", "Nepal", 1442000, 27.717, 85.324), ("Port Moresby", "Papua New Guinea", 383000, -9.443, 147.180),
    ("Wellington", "New Zealand", 419000, -41.286, 174.776), ("Quito", "Ecuador", 2781000, -0.180, -78.468),
    ("Athens", "Greece", 3154000, 37.984, 23.728), ("Taipei", "Taiwan", 7047000, 25.033, 121.565),
]


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371.0088 * 2 * asin(sqrt(a))


def population_exposure(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        cumulative = {50: 0, 100: 0, 200: 0}
        country = event["region"]
        matched_places = []
        for city, city_country, population, lat, lon in PLACES:
            distance = distance_km(event["latitude"], event["longitude"], lat, lon)
            if distance <= 200:
                matched_places.append(city)
                country = city_country
                for radius in cumulative:
                    if distance <= radius:
                        cumulative[radius] += population
        rows.append({
            "earthquake_id": event["id"], "place": event["place"], "magnitude": event["magnitude"],
            "country_region": country, "longitude": event["longitude"], "latitude": event["latitude"],
            "population_50km": cumulative[50], "population_100km": cumulative[100], "population_200km": cumulative[200],
            "matched_places": matched_places, "method": "Natural Earth populated places point-sum approximation",
        })
    return rows

