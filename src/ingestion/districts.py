"""Assign geoBoundaries ADM2 district names to analysis-grid cells."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.synthetic_data import CITY_PROFILES


def _empty(rows: int, cols: int) -> dict[str, np.ndarray | str]:
    labels = np.full((rows, cols), "unassigned", dtype=object)
    return {
        "district_name": labels,
        "district_data_source": "no local geoBoundaries ADM2 layer",
    }


def _ring_centroid(ring: list) -> tuple[float, float] | None:
    if not ring:
        return None
    return sum(pt[0] for pt in ring) / len(ring), sum(pt[1] for pt in ring) / len(ring)


def _geometry_centroid(geometry: dict) -> tuple[float, float] | None:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Polygon" and coordinates:
        return _ring_centroid(coordinates[0])
    if kind == "MultiPolygon" and coordinates:
        return _ring_centroid(coordinates[0][0])
    if kind == "Point" and coordinates:
        return float(coordinates[0]), float(coordinates[1])
    return None


def attach_districts(
    city: str,
    rows: int,
    cols: int,
    latitude: np.ndarray,
    longitude: np.ndarray,
    raw_dir: Path | None = None,
) -> dict[str, np.ndarray | str]:
    """Label each grid cell with the nearest clipped ADM2 district centroid."""
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must both be positive")
    if raw_dir is None:
        return _empty(rows, cols)

    code = CITY_PROFILES[city]["code"].lower()
    path = raw_dir / "boundaries" / f"{code}_adm2.geojson"
    if not path.exists():
        return _empty(rows, cols)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty(rows, cols)

    centres: list[tuple[float, float, str]] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        name = (
            properties.get("shapeName")
            or properties.get("shapeNameEn")
            or properties.get("name")
            or "unnamed"
        )
        centroid = _geometry_centroid(feature.get("geometry") or {})
        if centroid is None:
            continue
        centres.append((centroid[0], centroid[1], str(name)))
    if not centres:
        return _empty(rows, cols)

    lon = np.asarray(longitude, dtype="float64").ravel()
    lat = np.asarray(latitude, dtype="float64").ravel()
    labels = np.empty(lon.size, dtype=object)
    cx = np.array([item[0] for item in centres])
    cy = np.array([item[1] for item in centres])
    names = [item[2] for item in centres]
    for i, (x, y) in enumerate(zip(lon, lat)):
        dist = (cx - x) ** 2 + (cy - y) ** 2
        labels[i] = names[int(dist.argmin())]
    return {
        "district_name": labels.reshape(rows, cols),
        "district_data_source": "geoBoundaries gbOpen India ADM2 (ODbL)",
    }
