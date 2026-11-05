import json

import numpy as np

from src.ingestion.districts import attach_districts
from src.ingestion.nasa_power import fetch_daily_weather
from src.ingestion.osm_cooling import attach_osm_cooling


def test_osm_cooling_bins_features_to_grid(tmp_path):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.43, 22.91]},
                "properties": {"kind": "park"},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.43, 22.91]},
                "properties": {"kind": "hospital"},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[72.42, 22.90], [72.44, 22.90], [72.44, 22.92], [72.42, 22.92], [72.42, 22.90]]],
                },
                "properties": {"kind": "water"},
            },
        ],
    }
    osm_dir = tmp_path / "osm"
    osm_dir.mkdir()
    (osm_dir / "ahm_parks_water_amenities.geojson").write_text(json.dumps(payload), encoding="utf-8")
    result = attach_osm_cooling("Ahmedabad", rows=2, cols=2, raw_dir=tmp_path)
    assert result["park_feature_count"].sum() == 1
    assert result["amenity_feature_count"].sum() == 1
    assert result["water_feature_count"].sum() == 1


def test_osm_cooling_is_empty_without_local_file(tmp_path):
    result = attach_osm_cooling("Delhi", rows=3, cols=3, raw_dir=tmp_path)
    assert np.all(result["park_feature_count"] == 0)
    assert "no local OSM" in result["osm_cooling_data_source"]


def test_districts_label_nearest_adm2(tmp_path):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"shapeName": "West"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[76.84, 28.40], [77.05, 28.40], [77.05, 28.90], [76.84, 28.90], [76.84, 28.40]]],
                },
            },
            {
                "type": "Feature",
                "properties": {"shapeName": "East"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[77.15, 28.40], [77.35, 28.40], [77.35, 28.90], [77.15, 28.90], [77.15, 28.40]]],
                },
            },
        ],
    }
    dest = tmp_path / "boundaries"
    dest.mkdir()
    (dest / "del_adm2.geojson").write_text(json.dumps(payload), encoding="utf-8")
    latitude = np.array([[28.65, 28.65]])
    longitude = np.array([[76.90, 77.30]])
    result = attach_districts("Delhi", 1, 2, latitude, longitude, raw_dir=tmp_path)
    assert result["district_name"].tolist() == [["West", "East"]]


def test_fetch_daily_weather_uses_cache(tmp_path, monkeypatch):
    import pandas as pd

    from src.ingestion import nasa_power

    cache = tmp_path / "ahm_power_2024-04-01_2024-04-02.csv"
    pd.DataFrame({"city": ["Ahmedabad"], "date": ["2024-04-01"], "t2m": [31.0]}).to_csv(cache, index=False)

    def boom(*args, **kwargs):
        raise AssertionError("network should not be used when a weather cache exists")

    monkeypatch.setattr(nasa_power.requests.Session, "get", boom)
    frame = fetch_daily_weather("Ahmedabad", "2024-04-01", "2024-04-02", output_dir=tmp_path)
    assert frame["t2m"].tolist() == [31.0]
