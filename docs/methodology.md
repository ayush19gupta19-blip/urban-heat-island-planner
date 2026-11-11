# Methodology

## Synthetic baseline

The current implementation is a synthetic, deterministic prototype. It is used to validate the project workflow and dashboard before downloading large geospatial rasters and municipal data.

For each city, the pipeline creates a 20x20 grid and generates these features:

- Vegetation index proxy
- Built-up fraction proxy
- Population-density proxy
- Elderly-population share proxy
- Water-access proxy
- Land-surface-temperature proxy

The seed is fixed so the same inputs produce the same output. This makes tests and local demonstrations reproducible.

## Real-data demographic features

The real pipeline uses WorldPop Global2 R2025A v1 India rasters for 2020 at approximately 1 km resolution. It aggregates population counts and age-specific counts to each analysis cell using count-preserving raster resampling. Population density is derived from the geodesic area of each analysis cell. The age-65+ feature sums the 65-69, 70-74, 75-79, 80-84, 85-89, and 90+ groups, then divides by the total population estimate in that cell.

The rasters are cached in `data/raw/worldpop/india/`; they are downloaded once and are not committed to the repository. Source citations and license details are in [the dataset inventory](dataset_inventory.md).

These are modeled 2020 estimates, not current census counts. The approximately 1 km source cells cannot support street- or household-level conclusions. Census 2011 ward-level indicators remain a separate pending layer until ward codes and compatible municipal boundaries are matched.

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
6. Add and check WorldPop 2020 population and age-65+ estimates on the analysis grid.
7. Match Census 2011 ward-level indicators to compatible municipal boundaries.
8. Compare predictions against independent observations or a documented reference product.
9. Re-estimate weights and uncertainty before presenting recommendations as city evidence.

Land-surface temperature from Landsat is **skin** temperature. NASA POWER `T2M` is **2 m air** temperature at one city coordinate. `python -m src.validation` reports the city-level LST−air gap and the share of high/critical cells. That check does not validate the 0–100 score and never sets a validated flag. IMD 1° gridded air temperature is coarser than the 20×20 city grid and is not used as a cell-level truth layer.

## Responsible-use constraints

- Do not use this prototype as a medical alert or emergency warning system.
- Do not infer individual characteristics from aggregated population data.
- Preserve source attribution and license requirements.
- Report data gaps and uncertainty alongside maps and recommendations.
