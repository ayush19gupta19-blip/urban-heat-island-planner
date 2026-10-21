import numpy as np
import pandas as pd

import src.real_features as real_features
from src.ingestion.nasa_power import parse_power_payload


def test_parse_power_payload_returns_tidy_rows():
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"20240401": 30.0, "20240402": 31.0},
                "RH2M": {"20240401": 40.0, "20240402": 42.0},
            }
        }
    }
    frame = parse_power_payload(payload, "Delhi")
    assert frame["city"].eq("Delhi").all()
    assert frame["date"].tolist() == ["2024-04-01", "2024-04-02"]
    assert frame["t2m"].tolist() == [30.0, 31.0]


def test_real_feature_builder_preserves_quality_flags(monkeypatch):
    weather = pd.DataFrame(
        {
            "city": ["Ahmedabad", "Ahmedabad"],
            "date": ["2024-04-01", "2024-04-02"],
            "t2m": [30.0, 32.0],
            "rh2m": [40.0, 42.0],
            "ws10m": [2.0, 2.5],
            "prectotcorr": [0.0, 1.0],
            "allsky_sfc_sw_dwn": [200.0, 210.0],
        }
    )
    monkeypatch.setattr(real_features, "fetch_daily_weather", lambda *args, **kwargs: weather)
    monkeypatch.setattr(
        real_features,
        "extract_city_satellite_features",
        lambda *args, **kwargs: {
            "land_surface_temp_c": np.array([[40.0, np.nan], [42.0, 41.0]], dtype="float32"),
            "vegetation_index": np.array([[0.2, 0.3], [0.1, np.nan]], dtype="float32"),
            "built_up_fraction": np.array([[0.7, 0.6], [0.8, 0.5]], dtype="float32"),
            "ndbi": np.array([[0.2, 0.1], [0.3, 0.0]], dtype="float32"),
            "water_surface_fraction": np.zeros((2, 2), dtype="float32"),
            "landsat_valid": np.array([[True, False], [True, True]]),
            "sentinel_valid": np.array([[True, True], [True, False]]),
        },
    )

    frame = real_features.build_real_city_grid("Ahmedabad", "2024-04-01", "2024-04-02", rows=2, cols=2)
    assert len(frame) == 4
    assert frame["data_mode"].eq("real_weather_and_remote_sensing").all()
    assert frame["remote_sensing_imputed"].sum() == 2
    assert frame["heat_risk_score"].between(0, 100).all()
    assert not frame[["land_surface_temp_c", "vegetation_index", "built_up_fraction"]].isna().any().any()
