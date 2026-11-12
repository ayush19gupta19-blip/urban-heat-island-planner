import pandas as pd
import pytest

from src.validation import city_lst_air_gap


def test_lst_air_gap_rejects_missing_columns():
    grid = pd.DataFrame(
        {
            "city": ["Ahmedabad"],
            "land_surface_temp_c": [48.0],
        }
    )
    with pytest.raises(ValueError, match="missing required columns"):
        city_lst_air_gap(grid)


def test_lst_air_gap_empty_grid_returns_schema():
    grid = pd.DataFrame(columns=[
        "city", "land_surface_temp_c", "weather_mean_temp_c", "heat_risk_score"
    ])

    summary = city_lst_air_gap(grid)

    assert summary.empty
    assert list(summary.columns) == [
        "city", "n_cells", "mean_lst_c", "air_temp_c", "lst_minus_air_c",
        "high_critical_share", "validated", "note",
    ]


def test_lst_air_gap_is_never_marked_validated():
    grid = pd.DataFrame(
        {
            "city": ["Ahmedabad", "Ahmedabad", "Delhi", "Delhi"],
            "land_surface_temp_c": [48.0, 50.0, 52.0, 54.0],
            "weather_mean_temp_c": [34.0, 34.0, 36.0, 36.0],
            "heat_risk_score": [40.0, 70.0, 20.0, 80.0],
        }
    )
    summary = city_lst_air_gap(grid)
    assert set(summary["city"]) == {"Ahmedabad", "Delhi"}
    assert summary["validated"].eq(False).all()
    ahm = summary.set_index("city").loc["Ahmedabad"]
    assert ahm["mean_lst_c"] == 49.0
    assert ahm["air_temp_c"] == 34.0
    assert ahm["lst_minus_air_c"] == 15.0
    assert ahm["high_critical_share"] == 0.5
