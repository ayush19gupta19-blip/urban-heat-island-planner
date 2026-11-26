"""Tests for lightweight ward-level heat risk aggregation."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.synthetic_data import create_city_grid
from src.ward_summary import aggregate_risk_by_ward, load_ward_centroids, nearest_ward


def _tiny_wards(tmp_path: Path) -> Path:
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "ward_id": "W1",
                    "ward_label": "North",
                    "name": "North",
                    "city": "Ahmedabad",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [72.49, 23.01],
                            [72.51, 23.01],
                            [72.51, 23.03],
                            [72.49, 23.03],
                            [72.49, 23.01],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "ward_id": "W2",
                    "ward_label": "South",
                    "name": "South",
                    "city": "Ahmedabad",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [72.49, 22.99],
                            [72.51, 22.99],
                            [72.51, 23.01],
                            [72.49, 23.01],
                            [72.49, 22.99],
                        ]
                    ],
                },
            },
        ],
    }
    path = tmp_path / "wards.geojson"
    path.write_text(json.dumps(geo), encoding="utf-8")
    return path


def test_load_ward_centroids_and_nearest(tmp_path):
    path = _tiny_wards(tmp_path)
    centroids = load_ward_centroids(path)
    assert len(centroids) == 2
    assert {"ward_id", "ward_label", "latitude", "longitude"}.issubset(centroids.columns)
    label = nearest_ward(23.02, 72.50, centroids)
    assert label["ward_id"] in {"W1", "W2"}


def test_aggregate_risk_by_ward(tmp_path):
    path = _tiny_wards(tmp_path)
    grid = create_city_grid(city="Ahmedabad", rows=3, cols=3, seed=3)
    # Force coordinates near the toy wards
    grid = grid.copy()
    grid["latitude"] = 23.02
    grid["longitude"] = 72.50
    summary = aggregate_risk_by_ward(grid, path)
    assert not summary.empty
    assert summary["n_cells"].sum() == len(grid)
    assert {"ward_id", "mean_heat_risk", "high_risk_cells"}.issubset(summary.columns)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ward_centroids(tmp_path / "nope.geojson")


def test_nearest_ward_respects_city_filter(tmp_path):
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "ward_id": "A1",
                    "ward_label": "A-North",
                    "name": "A-North",
                    "city": "CityA",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "ward_id": "B1",
                    "ward_label": "B-Near",
                    "name": "B-Near",
                    "city": "CityB",
                },
                "geometry": {
                    "type": "Polygon",
                    # Closer to the query point than A1's centroid, but different city.
                    "coordinates": [[[9.0, 9.0], [11.0, 9.0], [11.0, 11.0], [9.0, 11.0], [9.0, 9.0]]],
                },
            },
        ],
    }
    path = tmp_path / "multi.geojson"
    path.write_text(json.dumps(geo), encoding="utf-8")
    centroids = load_ward_centroids(path)
    # Point near B1 geometrically (~10,10), but city filter must keep CityA (~0.5,0.5).
    match = nearest_ward(9.5, 9.5, centroids, city="CityA")
    assert match["ward_id"] == "A1"
    global_match = nearest_ward(9.5, 9.5, centroids)
    assert global_match["ward_id"] == "B1"
