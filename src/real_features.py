"""Build analysis-grid features from real weather and satellite observations."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.ingestion.nasa_power import fetch_daily_weather
from src.ingestion.stac_satellite import extract_city_satellite_features
from src.synthetic_data import CITY_PROFILES


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype="float32")
    finite = np.isfinite(values)
    if not finite.any():
        return np.zeros_like(values)
    low, high = np.nanmin(values), np.nanmax(values)
    return np.zeros_like(values) if high == low else np.nan_to_num((values - low) / (high - low), nan=0.0)


def build_real_city_grid(
    city: str,
    start_date: str,
    end_date: str,
    rows: int = 20,
    cols: int = 20,
    max_cloud_cover: float = 30.0,
    raw_dir: Path | None = None,
    metadata_dir: Path | None = None,
) -> pd.DataFrame:
    """Build one city grid from NASA POWER, Landsat, and Sentinel-2 data.

    Population, elderly share, and water access remain explicitly labelled
    proxies until WorldPop/municipal layers are added in the next ingestion
    milestone. Thermal, vegetation, built-up, and weather fields are real.
    """
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must both be positive")

    profile = CITY_PROFILES[city]
    weather_dir = raw_dir / "weather" if raw_dir else None
    weather = fetch_daily_weather(city, start_date, end_date, weather_dir)
    satellite = extract_city_satellite_features(
        city,
        start_date,
        end_date,
        rows=rows,
        cols=cols,
        max_cloud_cover=max_cloud_cover,
        metadata_dir=metadata_dir,
    )

    y, x = np.mgrid[0:rows, 0:cols]
    bbox = profile["bbox"]
    latitude = bbox[1] + (y + 0.5) * (bbox[3] - bbox[1]) / rows
    longitude = bbox[0] + (x + 0.5) * (bbox[2] - bbox[0]) / cols
    temperature = satellite["land_surface_temp_c"]
    vegetation = satellite["vegetation_index"]
    built_up = satellite["built_up_fraction"]
    water_surface = satellite["water_surface_fraction"]
    ndbi = satellite["ndbi"]
    landsat_valid = satellite["landsat_valid"]
    sentinel_valid = satellite["sentinel_valid"]
    remote_sensing_valid = landsat_valid & sentinel_valid

    def fill_nan(values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype="float32")
        replacement = float(np.nanmedian(values)) if np.isfinite(values).any() else 0.0
        return np.where(np.isfinite(values), values, replacement)

    temperature = fill_nan(temperature)
    vegetation = fill_nan(vegetation)
    built_up = fill_nan(built_up)
    ndbi = fill_nan(ndbi)

    weather_summary = {
        "weather_mean_temp_c": weather["t2m"].replace(-999, np.nan).mean(),
        "weather_max_temp_c": weather["t2m"].replace(-999, np.nan).max(),
        "relative_humidity_pct": weather["rh2m"].replace(-999, np.nan).mean(),
        "wind_speed_m_s": weather["ws10m"].replace(-999, np.nan).mean(),
        "precipitation_mm": weather["prectotcorr"].replace(-999, np.nan).sum(),
        "solar_radiation_kwh_m2_day": weather["allsky_sfc_sw_dwn"].replace(-999, np.nan).mean(),
    }

    # These are temporary, clearly named proxies for the recommendation layer.
    population_density = profile["population"] + 7000 * np.nan_to_num(_normalize(built_up), nan=0.0)
    elderly_share = np.full((rows, cols), 0.09, dtype="float32")
    water_access = np.clip(0.25 + 0.65 * water_surface + 0.2 * (1 - built_up), 0.05, 0.95)
    risk = (
        0.42 * _normalize(temperature)
        + 0.22 * _normalize(built_up)
        + 0.18 * _normalize(population_density)
        + 0.10 * _normalize(elderly_share)
        + 0.08 * (1 - water_access)
    )
    heat_risk = np.clip(risk * 100, 0, 100)

    frame = pd.DataFrame(
        {
            "city": city,
            "grid_id": [f"{profile['code']}-{i:04d}" for i in range(rows * cols)],
            "row": y.ravel(),
            "col": x.ravel(),
            "latitude": latitude.ravel().round(6),
            "longitude": longitude.ravel().round(6),
            "vegetation_index": vegetation.ravel(),
            "built_up_fraction": built_up.ravel(),
            "ndbi": ndbi.ravel(),
            "water_surface_fraction": water_surface.ravel(),
            "landsat_valid": landsat_valid.ravel(),
            "sentinel_valid": sentinel_valid.ravel(),
            "remote_sensing_valid": remote_sensing_valid.ravel(),
            "remote_sensing_imputed": (~remote_sensing_valid).ravel(),
            "population_density": population_density.ravel(),
            "population_data_source": "built-up proxy; add WorldPop next",
            "elderly_share": elderly_share.ravel(),
            "elderly_data_source": "temporary city-wide proxy",
            "water_access": water_access.ravel(),
            "land_surface_temp_c": temperature.ravel(),
            "heat_risk_score": heat_risk.ravel(),
            "data_mode": "real_weather_and_remote_sensing",
        }
    )
    for key, value in weather_summary.items():
        frame[key] = value
    risk_categories = pd.cut(
        frame["heat_risk_score"], bins=[-1, 35, 60, 80, 101], labels=["Low", "Moderate", "High", "Critical"]
    )
    frame["risk_category"] = [str(value) for value in risk_categories]
    return frame
