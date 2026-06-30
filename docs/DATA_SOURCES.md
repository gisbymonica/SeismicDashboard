# Data sources

Earthquake Exposure Intelligence uses only public, open data.

| Dataset | Use | URL | License / terms | Attribution | Refresh |
|---|---|---|---|---|---|
| USGS Earthquake Catalog | Recent global M4.5+ events | https://earthquake.usgs.gov/fdsnws/event/1/ | U.S. Government work; public domain | U.S. Geological Survey | On application startup and manual API refresh |
| Natural Earth populated places | MVP population point-sum approximation | https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-populated-places/ | Public domain | Natural Earth | Bundled MVP reference values; versioned with the application |
| OpenStreetMap / Overpass API | Critical infrastructure locations | https://overpass-api.de/api/interpreter | Open Database License 1.0 | © OpenStreetMap contributors | At startup or explicit refresh for the leading event; results remain empty if unavailable |

The dashboard footer displays source URLs, license labels, attribution, and the latest catalog update timestamp. The API repeats this metadata in `/api/summary` and relevant dataset responses.



## Exploratory Hotspot Likelihood Model

The model uses the same public-domain USGS Earthquake Catalog listed above for training features, time-window labels, evaluation, and current grid-cell scoring. No proprietary or paid data is used. Population and OpenStreetMap data are used only to add approximate exposure context after scoring; they are not model-training features.

PB2002/Bird plate boundaries were considered as an optional open feature, but are not included in the MVP because a version-pinned boundary file has not been bundled. The API and feature schema therefore do not claim a plate-boundary-distance feature.
