"""Synthetic city grids used until public data ingestion is added."""

import numpy as np
import pandas as pd


CITY_PROFILES = {
    "Ahmedabad": {"lat": 23.02, "lon": 72.50, "base_temp": 31.5, "vegetation": 0.18, "population": 1800, "water": 0.75, "code": "AHM"},
    "Delhi": {"lat": 28.61, "lon": 77.20, "base_temp": 32.0, "vegetation": 0.22, "population": 2200, "water": 0.62, "code": "DEL"},
    "Kolkata": {"lat": 22.57, "lon": 88.36, "base_temp": 30.5, "vegetation": 0.28, "population": 2400, "water": 0.84, "code": "KOL"},
}


def create_city_grid(city: str = "Ahmedabad", rows: int = 20, cols: int = 20, seed: int = 42) -> pd.DataFrame:
    """Create explainable grid features and a normalized heat-risk score."""
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must both be positive")
    profile = CITY_PROFILES[city]
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:rows, 0:cols]
    centre_distance = np.sqrt((x - cols / 2) ** 2 + (y - rows / 2) ** 2)
    max_distance = centre_distance.max()
    centrality = 1 - centre_distance / max_distance if max_distance else np.zeros_like(centre_distance)

    vegetation = np.clip(profile["vegetation"] + 0.28 * rng.random((rows, cols)) - 0.08 * centrality, 0.03, 0.65)
    built_up = np.clip(0.35 + 0.45 * centrality + 0.12 * rng.random((rows, cols)), 0.15, 0.98)
    population_density = np.clip(profile["population"] + 7000 * centrality + rng.normal(0, 500, (rows, cols)), 700, None)
    elderly_share = np.clip(rng.normal(0.09, 0.025, (rows, cols)), 0.04, 0.18)
    water_access = np.clip(profile["water"] - 0.45 * centrality + rng.normal(0, 0.08, (rows, cols)), 0.05, 0.95)
    land_surface_temp = profile["base_temp"] + 7.0 * built_up - 5.5 * vegetation + rng.normal(0, 0.7, (rows, cols))

    risk = (
        0.42 * _normalize(land_surface_temp)
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
            "latitude": (profile["lat"] + y.ravel() * 0.006).round(6),
            "longitude": (profile["lon"] + x.ravel() * 0.006).round(6),
            "vegetation_index": vegetation.ravel().round(4),
            "built_up_fraction": built_up.ravel().round(4),
            "population_density": population_density.ravel().round(1),
            "elderly_share": elderly_share.ravel().round(4),
            "water_access": water_access.ravel().round(4),
            "land_surface_temp_c": land_surface_temp.ravel().round(2),
            "heat_risk_score": heat_risk.ravel().round(2),
        }
    )
    frame["risk_category"] = pd.cut(
        frame["heat_risk_score"], bins=[-1, 35, 60, 80, 101], labels=["Low", "Moderate", "High", "Critical"]
    ).astype(str)
    return frame


def _normalize(values: np.ndarray) -> np.ndarray:
    spread = values.max() - values.min()
    return (values - values.min()) / spread if spread else np.zeros_like(values)
