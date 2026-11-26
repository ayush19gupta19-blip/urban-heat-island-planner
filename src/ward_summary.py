"""Nearest-ward aggregation for heat-risk grids (no geopandas required).

Loads ward GeoJSON, computes polygon centroids, assigns each grid cell to the
nearest ward centre, and summarizes mean risk. Screening aid only — not a
formal cadastral join.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _ring_centroid(ring: list) -> tuple[float, float]:
    """Centroid of a simple ring [[lon, lat], ...] (exclude closing point)."""
    coords = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    if not coords:
        return (float("nan"), float("nan"))
    lons = [float(p[0]) for p in coords]
    lats = [float(p[1]) for p in coords]
    return (sum(lons) / len(lons), sum(lats) / len(lats))


def _geometry_centroid(geometry: dict) -> tuple[float, float]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon":
        return _ring_centroid(coords[0])
    if gtype == "MultiPolygon":
        # area-unweighted mean of outer rings — fine for nearest-label screening
        cents = [_ring_centroid(poly[0]) for poly in coords]
        lons = [c[0] for c in cents if c[0] == c[0]]
        lats = [c[1] for c in cents if c[1] == c[1]]
        if not lons:
            return (float("nan"), float("nan"))
        return (sum(lons) / len(lons), sum(lats) / len(lats))
    if gtype == "Point":
        return (float(coords[0]), float(coords[1]))
    return (float("nan"), float("nan"))


def load_ward_centroids(path: str | Path) -> pd.DataFrame:
    """Read a ward GeoJSON FeatureCollection into centroid rows."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    rows = []
    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        lon, lat = _geometry_centroid(geometry)
        ward_id = props.get("ward_id") or props.get("id") or props.get("name")
        label = props.get("ward_label") or props.get("name") or str(ward_id)
        rows.append(
            {
                "ward_id": str(ward_id),
                "ward_label": str(label),
                "city": props.get("city"),
                "longitude": lon,
                "latitude": lat,
            }
        )
    return pd.DataFrame(rows)


def nearest_ward(
    latitude: float,
    longitude: float,
    centroids: pd.DataFrame,
    *,
    city: str | None = None,
) -> dict:
    """Return the centroid row nearest to the point (equirectangular metres approx).

    When ``city`` is set and the centroid table has a city column, only wards
    for that city are considered so multi-city GeoJSON cannot cross-assign.
    """
    if centroids.empty:
        raise ValueError("centroids is empty")
    pool = centroids
    if city is not None and "city" in centroids.columns and centroids["city"].notna().any():
        city_pool = centroids[centroids["city"].astype(str) == str(city)]
        if city_pool.empty:
            raise ValueError(f"no ward centroids for city {city!r}")
        pool = city_pool
    lat0 = np.radians(float(latitude))
    dlat = np.radians(pool["latitude"].to_numpy(dtype=float) - float(latitude))
    dlon = np.radians(pool["longitude"].to_numpy(dtype=float) - float(longitude)) * np.cos(lat0)
    dist2 = dlat**2 + dlon**2
    idx = int(np.nanargmin(dist2))
    row = pool.iloc[idx]
    return {
        "ward_id": str(row["ward_id"]),
        "ward_label": str(row["ward_label"]),
        "city": row.get("city"),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
    }


def aggregate_risk_by_ward(grid: pd.DataFrame, ward_geojson: str | Path) -> pd.DataFrame:
    """Assign grid cells to nearest ward centroids and aggregate risk."""
    required = {"city", "grid_id", "latitude", "longitude", "heat_risk_score"}
    missing = required.difference(grid.columns)
    if missing:
        raise ValueError(f"grid missing columns: {sorted(missing)}")
    centroids = load_ward_centroids(ward_geojson)
    if centroids.empty:
        return pd.DataFrame(
            columns=["ward_id", "ward_label", "n_cells", "mean_heat_risk", "high_risk_cells"]
        )

    assignments = []
    for record in grid.to_dict("records"):
        match = nearest_ward(
            float(record["latitude"]),
            float(record["longitude"]),
            centroids,
            city=str(record["city"]),
        )
        assignments.append(
            {
                "ward_id": match["ward_id"],
                "ward_label": match["ward_label"],
                "heat_risk_score": float(record["heat_risk_score"]),
            }
        )
    assigned = pd.DataFrame(assignments)
    grouped = (
        assigned.groupby(["ward_id", "ward_label"], sort=False)
        .agg(
            n_cells=("heat_risk_score", "size"),
            mean_heat_risk=("heat_risk_score", "mean"),
            high_risk_cells=("heat_risk_score", lambda s: int((s >= 60).sum())),
        )
        .reset_index()
    )
    grouped["mean_heat_risk"] = grouped["mean_heat_risk"].round(2)
    return grouped.sort_values("mean_heat_risk", ascending=False).reset_index(drop=True)
