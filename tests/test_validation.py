import pandas as pd

from src.validation import city_lst_air_gap


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
