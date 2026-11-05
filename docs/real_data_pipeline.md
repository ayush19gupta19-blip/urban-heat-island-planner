# Real-data pipeline

## What is implemented

Run:

```bash
python -m src.pipeline --mode real --start-date 2024-04-01 --end-date 2024-06-30 --max-cloud-cover 30
```

The command processes Ahmedabad, Delhi, and Kolkata.

### NASA POWER

`src/ingestion/nasa_power.py` requests daily `T2M`, `RH2M`, `WS10M`, `PRECTOTCORR`, and `ALLSKY_SFC_SW_DWN`. The response is saved as a small CSV in `data/raw/weather/` and summarized into the feature grid.

### Landsat Collection 2 Level-2

`src/ingestion/stac_satellite.py` searches the public Planetary Computer STAC for the least-cloudy Landsat item in the city bbox and date window. It reads the thermal (`lwir`) asset and applies the Collection 2 surface-temperature scale/offset to produce Celsius values. It also reads `nir08` and `swir16` to create an NDBI-based built-up proxy. QA_PIXEL bits are used to mask fill/cloud/shadow/snow pixels.

### Sentinel-2 Level-2A

The same module searches the public STAC for the least-cloudy Sentinel-2 item. It reads B04, B08, and SCL to compute cloud-masked NDVI and a water-surface proxy from scene-classification water pixels.

### Grid builder

`src/real_features.py` converts those observations to the same 20x20 grid contract used by the recommendation engine. Each row contains coordinates, real thermal/vegetation/built-up features, weather summaries, risk score, risk category, and source metadata.

## Current boundary of the real mode

Population count and density now come from WorldPop Global2 R2025A v1 India 2020 rasters at approximately 1 km resolution. The 65+ population count and share are aggregated from WorldPop age bands (65-69 through 90+). The first run downloads and caches roughly 113 MB under `data/raw/worldpop/india/`; subsequent runs reuse those files. These are modeled 2020 estimates, not current ward census counts.

OpenStreetMap park, water, and amenity counts are binned onto the same grid when `data/raw/osm/<city>_parks_water_amenities.geojson` is present. geoBoundaries ADM2 names are attached from `data/raw/boundaries/<city>_adm2.geojson`. Refresh both with `python scripts/fetch_public_layers.py`. NASA POWER CSVs and satellite `.npz` grids are read from cache on later runs.

Water access is a surface-water / OSM-water proxy, not household tap access. Municipal ward-level Census 2011 joins are still pending.

## Reproducibility

- Date window and cloud threshold are command-line arguments.
- STAC item IDs are saved to `data/raw/metadata/`.
- Raw downloads and generated CSVs are ignored by Git.
- The public repository contains the code and data-source documentation, not large raster assets.
