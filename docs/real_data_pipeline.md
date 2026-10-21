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

Population density is currently an explicit built-up-based proxy, elderly share is a temporary city-wide proxy, and water access is a surface-water/accessibility proxy. They are not presented as official demographic measurements. The next data milestone is to add WorldPop and municipal/ward layers before using the planner for real allocation decisions.

## Reproducibility

- Date window and cloud threshold are command-line arguments.
- STAC item IDs are saved to `data/raw/metadata/`.
- Raw downloads and generated CSVs are ignored by Git.
- The public repository contains the code and data-source documentation, not large raster assets.
