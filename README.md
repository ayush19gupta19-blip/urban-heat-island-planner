# Urban Heat Island Cooling Planner

[![Python checks](https://github.com/ayush19gupta19-blip/urban-heat-island-planner/actions/workflows/ci.yml/badge.svg)](https://github.com/ayush19gupta19-blip/urban-heat-island-planner/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An environmental decision-support project for identifying heat-vulnerable parts of Ahmedabad, Delhi, and Kolkata and prioritising cooling interventions such as tree planting, cool roofs, and cooling centres.

![Streamlit dashboard — synthetic demo, Ahmedabad heat-risk map and intervention table](docs/images/dashboard.png)

## Current milestone

This project has two reproducible modes. Synthetic mode is a fast demo. Real mode pulls NASA POWER weather, Landsat/Sentinel-2, WorldPop 2020 population and age-65+ estimates, optional OpenStreetMap parks/water/amenities, and geoBoundaries district labels onto a common city grid, then ranks cooling options in the dashboard.

## Product question

> If a city has a limited budget, which areas should receive cooling investment first to reduce heat exposure for vulnerable residents?

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.pipeline
streamlit run app/dashboard.py
```

To build the real remote-sensing feature tables for all three cities:

```bash
python -m src.pipeline --mode real --start-date 2024-04-01 --end-date 2024-06-30 --max-cloud-cover 30
```

The first real-mode run downloads WorldPop rasters under `data/raw/worldpop/india/`. NASA POWER weather, satellite metadata, and downsampled satellite grids are cached under `data/raw/` and reused on later runs.

Optional OSM and district layers:

```bash
python scripts/fetch_public_layers.py
```

The synthetic pipeline writes `data/processed/heat_risk_grid.csv` and `data/processed/intervention_recommendations.csv`. The real pipeline writes the corresponding `_real.csv` files. Population values are modeled 2020 estimates, not a current ward census.

## Pilot cities

- Ahmedabad
- Delhi
- Kolkata

The local baseline generates a separate 20x20 analysis grid for each city and provides a city selector in the dashboard. These city profiles are synthetic and must be calibrated against local observations before operational use.

## Architecture

```text
Raw/provider data -> ingestion -> feature engineering -> heat-risk model
                                      |                    |
                                      v                    v
                                geospatial grid -> intervention ranking -> dashboard
```

## Data currently used

- NASA POWER daily weather
- Landsat Collection 2 land-surface temperature and built-up proxy
- Sentinel-2 NDVI and water-surface proxy
- WorldPop 2020 population and age 65+
- OpenStreetMap parks, water, hospitals/clinics/community centres (local cache)
- geoBoundaries India ADM2 district labels (local cache)

The public repository contains code, documentation, and synthetic/aggregated tables only.

The confirmed dataset inventory is in [`docs/dataset_inventory.md`](docs/dataset_inventory.md).
Scoring and limits are in [`docs/methodology.md`](docs/methodology.md).

## Project status

- [x] Scope and pilot city selected
- [x] Reproducible synthetic grid baseline
- [x] Explainable heat-risk scoring
- [x] Budget-aware intervention ranking
- [x] Initial dashboard
- [x] Public dataset availability confirmed for Ahmedabad, Delhi, and Kolkata
- [x] NASA POWER weather ingestion
- [x] Landsat land-surface-temperature and built-up proxy ingestion
- [x] Sentinel-2 NDVI and water-surface proxy ingestion
- [x] Real-data feature builder with city-wide weather summaries
- [x] WorldPop 2020 population counts and age-65+ vulnerability grid
- [x] OSM cooling-layer counts and geoBoundaries district labels
- [ ] Municipal ward-level vulnerability join (Census ward tables and matching boundaries)
- [ ] Spatial model validation against observed temperature
- [ ] Historical trend and uncertainty analysis

## Checks

```bash
pytest -q
```

## Limitations

The current baseline is a planning prototype, not a public-health warning system. Its coefficients and intervention effects are assumptions until calibrated against local observations and domain-expert review.
