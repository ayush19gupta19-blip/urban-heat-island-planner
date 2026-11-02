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

Population count and density now come from WorldPop Global2 R2025A v1 India 2020 rasters at approximately 1 km resolution. The 65+ population count and share are aggregated from WorldPop age bands (65-69 through 90+). The first run downloads and caches roughly 113 MB under `data/raw/worldpop/india/`; subsequent runs reuse those files. These are modeled 2020 estimates, not current ward census counts. Water access remains a surface-water/accessibility proxy.

Municipal ward-level vulnerability attributes are still pending. Census 2011 provides ward-level indicators, but they should only be joined after ward codes and compatible municipal boundaries are verified for each pilot city. Do not treat the current 1 km demographic grid as a ward-level measurement or use it for individual-level decisions.

## Reproducibility

- Date window and cloud threshold are command-line arguments.
- STAC item IDs are saved to `data/raw/metadata/`.
- Raw downloads and generated CSVs are ignored by Git.
- The public repository contains the code and data-source documentation, not large raster assets.
