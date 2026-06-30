# Methodology

## Scope

The dashboard implements exactly three analytical modules: earthquake clustering, approximate population exposure, and critical infrastructure exposure. It is historical pattern analysis, not an earthquake prediction system.

## 1. Earthquake clustering

Recent global events are requested from the USGS FDSN Event API with a default minimum magnitude of M4.5 and selectable 30, 90, or 365-day windows. The stored event fields are USGS event ID, magnitude, depth, occurrence time, place/location, longitude, latitude, and a region label derived from the place string.

DBSCAN is applied to latitude/longitude coordinates using a haversine metric. The MVP parameters are `eps = 500 km` and `min_samples = 3`. A relatively broad radius is intentional for global-scale screenshot legibility and regional seismic-zone grouping. Noise points remain visible as earthquakes but do not receive cluster hulls. A Shapely convex hull with a small display buffer becomes each cluster polygon.

The most recent seven days form the recent window; all earlier events in the selected catalog form the baseline:

- **Emerging hotspot:** recent events exist, with no baseline members.
- **Persistent hotspot:** both recent and baseline events exist.
- **Dying hotspot:** baseline members exist, with no recent events.

These labels describe observed catalog activity only. They do not estimate future earthquake probability.

## 2. Population exposure

Each earthquake has 50, 100, and 200 km geodesic-distance exposure bands. The clean MVP uses the permitted Natural Earth populated-places fallback: reference population values for populated-place points falling inside a radius are summed. Values are cumulative, so the 100 km result includes the 50 km result and the 200 km result includes both.

This is an approximate screening indicator, not a population raster zonal statistic. It can undercount dispersed rural populations and can differ from WorldPop. A production raster extension should pin the WorldPop year and resolution, reproject each local buffer to an appropriate equal-distance CRS, run zonal sums, and record raster vintage and nodata behavior.

## 3. Critical infrastructure exposure

The Overpass query is restricted to the required OpenStreetMap tags:

- `amenity=hospital`
- `power=plant`
- `power=substation`
- `waterway=dam` or `man_made=dam`
- `aeroway=aerodrome`
- `amenity=fire_station`
- `amenity=police`

Nodes, ways, and relations are normalized to points using their coordinates or Overpass-provided centers. Duplicate OSM element IDs are removed. Haversine distance from an earthquake determines cumulative membership in 50, 100, and 200 km bands. If Overpass is unavailable, the service returns an empty infrastructure result rather than inserting synthetic assets or blocking the dashboard.

## Interpretation

- Exposure does not mean damage, service interruption, or casualty.
- Results do not model shaking intensity, ground motion, building vulnerability, tsunami impact, or travel access.
- OSM infrastructure coverage and tagging completeness vary by location.
- Population exposure is approximate in the MVP.
- WorldPop raster results, when integrated, depend on the selected year and resolution.
- Catalog completeness varies by magnitude, time, and location.
- Cluster parameters are analytical choices, not physical boundaries.



## Exploratory Hotspot Likelihood Model

### Purpose and wording

The Random Forest module estimates which 2° × 2° spatial grid cells have a higher **exploratory next-hotspot likelihood based on historical USGS patterns**. It classifies cells; it does not predict a single latitude/longitude, exact time, exact magnitude, or epicenter. **This is not an earthquake prediction or public warning system.**

### Why Random Forest

Earthquake occurrence is non-linear, clustered, and tectonically constrained. A Random Forest classifier can represent non-linear thresholds and interactions between recent counts, magnitude, depth, energy, recency, and proximity features without fitting a smooth global surface. It also supplies auditable global feature importances. Polynomial regression was explicitly rejected because a smooth polynomial curve is not a defensible representation of spatial earthquake occurrence and would encourage a misleading single-location forecast.

### Grid, windows, and labels

The default model uses the latest 365 days of the open USGS catalog and a configurable 2° grid. Weekly anchor times are created after a 90-day warm-up. For every candidate grid cell and anchor:

- Features use only events at or before the anchor.
- The label is `1` when at least one USGS event at or above M4.5 occurs in that cell during the following seven days.
- The label is `0` otherwise.
- Candidate negatives include the four cells adjacent to historically active cells so the model sees meaningful inactive examples without treating every empty ocean cell as equally informative.

The training/test split is chronological: the earliest 80% of anchor windows train the model and the latest 20% form the holdout set. Rows are never randomly split across time. The classifier uses `class_weight="balanced"`, 220 trees, a maximum depth of 14, and a minimum leaf size of two. The MVP reports uncalibrated classifier likelihood scores; they are not prediction certainty.

### Features

The implemented feature schema is saved to `backend/models/hotspot_features.json` and contains:

- event counts over 7, 30, and 90 days;
- maximum and mean magnitude over 30 days;
- maximum and mean depth over 30 days;
- log-scaled summed seismic energy over 30 days using `log10(E) = 1.5M + 4.8`;
- days since the last event;
- distance to the nearest recent dense grid-cell concentration;
- 365-day historical event density; and
- encoded emerging, persistent, fading, or inactive recent activity.

Distance to a plate boundary is intentionally omitted from this MVP because no version-pinned PB2002 geometry is bundled yet. It must not be represented as available until a documented open boundary dataset is integrated and versioned.

### Explainability and exposure context

Global importance is the fitted forest's impurity-based feature importance. The API exposes the five highest-ranked features with plain-language interpretations. Cell-level contributing features are an exploratory explanation obtained by weighting each global importance by the cell feature's standardized deviation from the training mean; this is not a causal attribution.

Clicking a cell shows its likelihood score, bounds/center, recent activity, the strongest local feature signals, approximate nearby population from the existing population module, and nearby OSM infrastructure from the existing infrastructure module.

### What the model can and cannot say

The output can compare historical-pattern similarity among grid cells for exploratory analysis. It cannot forecast an exact event, estimate public-safety risk, replace an operational seismic forecast, or support emergency response. Apparent skill can reflect catalog persistence, aftershock sequences, spatial sampling, class imbalance, and the arbitrary grid/window choices.

### Hotspot-cell exposure enrichment

Population context for each likelihood cell is calculated directly from Natural Earth populated-place points within 200 km of the grid-cell center; it no longer depends on whether an earthquake exposure row happens to overlap that cell. Critical infrastructure is intentionally loaded on demand when a user selects a likelihood cell. The backend runs the same required OpenStreetMap/Overpass tag query around that cell center, caches the result by cell ID, and returns category counts with OSM attribution. Until the query completes, the UI displays a loading state rather than a misleading zero. If Overpass is unavailable, it displays “Unavailable”; a numeric zero is shown only after a successful query returns no matching assets.
