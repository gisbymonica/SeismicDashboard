# Limitations and responsible use

This is **not an earthquake prediction system**. Cluster statuses summarize historical catalog patterns and must not be interpreted as forecasts.

Exposure does not mean damage. Distance buffers do not represent measured shaking, vulnerability, loss, accessibility, or operational status.

Population exposure is approximate. The MVP populated-place method omits people outside represented settlements and can aggregate metropolitan estimates differently from gridded population products. Future WorldPop results must state the selected year and resolution.

OpenStreetMap infrastructure coverage may be incomplete, uneven, duplicated through tagging, or out of date. Presence in OSM does not establish current operating status.

USGS event solutions can be revised. Network availability may delay refreshes; the UI reports whether live USGS data or a bundled fallback is active.


## Exploratory Hotspot Likelihood Model

The grid-cell scores are exploratory classifier outputs based on historical USGS patterns. They are not calibrated probabilities of an earthquake, prediction certainty, an early-warning signal, or a public-safety risk estimate.

The model does not predict exact timing, magnitude, or epicenter. It must not be used for emergency response, evacuation, public warnings, insurance decisions, or infrastructure operations. The 2° grid, seven-day label window, negative-cell sampling, magnitude threshold, and 365-day training horizon are analytical choices that can materially change results. Nearby population and infrastructure are approximate context only and do not turn a likelihood score into a damage or risk estimate.

Random Forest feature importance is associative, not causal. Correlated features can divide or exchange importance. Cell-level contributing features are standardized heuristic explanations rather than SHAP values. Probability calibration is not applied in the MVP, so scores should only be compared as low, medium, and high exploratory likelihood bands.

Plate-boundary distance is not included until a versioned open plate-boundary dataset is bundled and documented.
