# Methodology

## Current baseline

The current implementation is a synthetic, deterministic prototype. It is used to validate the project workflow and dashboard before downloading large geospatial rasters and municipal data.

For each city, the pipeline creates a 20x20 grid and generates these features:

- Vegetation index proxy
- Built-up fraction proxy
- Population-density proxy
- Elderly-population share proxy
- Water-access proxy
- Land-surface-temperature proxy

The seed is fixed so the same inputs produce the same output. This makes tests and local demonstrations reproducible.

## Heat-risk score

The baseline score is a 0–100 index based on normalized features:

```text
heat risk =
    0.42 * normalized land-surface temperature
  + 0.22 * normalized built-up fraction
  + 0.18 * normalized population density
  + 0.10 * normalized elderly share
  + 0.08 * (1 - water access)
```

The score is then grouped into Low, Moderate, High, and Critical categories. These weights are planning assumptions, not a validated public-health model.

## Intervention ranking

Each grid cell receives candidate recommendations for tree planting, cool roofs, and cooling centres. A candidate is ranked using heat exposure, estimated vulnerable population, intervention feasibility, cooling effect, and cost.

```text
priority = exposure × vulnerability × feasibility × cooling effect / cost
```

The default demonstration budget is INR 1,000,000 per city. Costs and cooling effects are illustrative assumptions and must be replaced with locally sourced estimates before real planning use.

## Real-data calibration plan

The synthetic features will be replaced in stages:

1. Establish and validate city boundaries.
2. Aggregate NASA POWER weather data to the analysis period.
3. Compute cloud-filtered Landsat land-surface temperature.
4. Compute Sentinel-2 vegetation and land-cover indicators.
5. Aggregate OSM buildings, roads, parks, water, and public facilities.
6. Add WorldPop or official demographic data.
7. Compare predictions against independent observations or a documented reference product.
8. Re-estimate weights and uncertainty before presenting recommendations as city evidence.

## Responsible-use constraints

- Do not use this prototype as a medical alert or emergency warning system.
- Do not infer individual characteristics from aggregated population data.
- Preserve source attribution and license requirements.
- Report data gaps and uncertainty alongside maps and recommendations.
