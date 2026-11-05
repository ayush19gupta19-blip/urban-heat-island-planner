"""Bin OpenStreetMap parks, water, and amenities onto the city analysis grid."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.synthetic_data import CITY_PROFILES

PARK_KINDS = {"park"}
WATER_KINDS = {"water", "reservoir"}
AMENITY_KINDS = {"hospital", "clinic", "community_centre"}


def _empty(rows: int, cols: int) -> dict[str, np.ndarray | str]:
    zeros = np.zeros((rows, cols), dtype="float32")
    return {
        "park_feature_count": zeros.copy(),
        "water_feature_count": zeros.copy(),
        "amenity_feature_count": zeros.copy(),
        "osm_cooling_data_source": "no local OSM cooling layer",
    }


def _feature_point(geometry: dict) -> tuple[float, float] | None:
    if not geometry:
        return None
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Point" and coordinates and len(coordinates) >= 2:
        return float(coordinates[0]), float(coordinates[1])
    if kind == "Polygon" and coordinates and coordinates[0]:
        ring = coordinates[0]
        return sum(pt[0] for pt in ring) / len(ring), sum(pt[1] for pt in ring) / len(ring)
    if kind == "MultiPolygon" and coordinates and coordinates[0] and coordinates[0][0]:
        ring = coordinates[0][0]
        return sum(pt[0] for pt in ring) / len(ring), sum(pt[1] for pt in ring) / len(ring)
    return None


def _cell_index(lon: float, lat: float, bbox: list[float], rows: int, cols: int) -> tuple[int, int] | None:
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
        return None
    col = min(cols - 1, max(0, int((lon - min_lon) / (max_lon - min_lon) * cols)))
    row = min(rows - 1, max(0, int((lat - min_lat) / (max_lat - min_lat) * rows)))
    return row, col


def attach_osm_cooling(
    city: str,
    rows: int,
    cols: int,
    raw_dir: Path | None = None,
) -> dict[str, np.ndarray | str]:
    """Count OSM parks, water bodies, and cooling-related amenities per grid cell."""
    if city not in CITY_PROFILES:
        raise ValueError(f"Unsupported city: {city}. Choose from {sorted(CITY_PROFILES)}")
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must both be positive")
    if raw_dir is None:
        return _empty(rows, cols)

    code = CITY_PROFILES[city]["code"].lower()
    path = raw_dir / "osm" / f"{code}_parks_water_amenities.geojson"
    if not path.exists():
        return _empty(rows, cols)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty(rows, cols)

    parks = np.zeros((rows, cols), dtype="float32")
    water = np.zeros((rows, cols), dtype="float32")
    amenities = np.zeros((rows, cols), dtype="float32")
    bbox = CITY_PROFILES[city]["bbox"]
    for feature in payload.get("features", []):
        point = _feature_point(feature.get("geometry") or {})
        if point is None:
            continue
        index = _cell_index(point[0], point[1], bbox, rows, cols)
        if index is None:
            continue
        row, col = index
        kind = str((feature.get("properties") or {}).get("kind") or "").lower()
        if kind in PARK_KINDS:
            parks[row, col] += 1
        elif kind in WATER_KINDS:
            water[row, col] += 1
        elif kind in AMENITY_KINDS:
            amenities[row, col] += 1

    return {
        "park_feature_count": parks,
        "water_feature_count": water,
        "amenity_feature_count": amenities,
        "osm_cooling_data_source": "OpenStreetMap parks, water, and amenities (ODbL)",
    }
