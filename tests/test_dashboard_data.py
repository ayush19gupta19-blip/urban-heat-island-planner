import pandas as pd

from src.dashboard_data import osm_cooling_totals, population_quality


def test_population_quality_handles_stale_real_csv_without_coverage():
    grid = pd.DataFrame(
        {
            "population_count": [100.0, 200.0],
            "elderly_share": [0.1, 0.2],
        }
    )
    stats = population_quality(grid)
    assert stats is not None
    assert stats["has_coverage_columns"] is False
    assert stats["total_population"] == 300.0
    assert stats["elderly_population"] == 50.0
    assert stats["population_coverage"] == 1.0


def test_population_quality_none_without_counts():
    assert population_quality(pd.DataFrame({"heat_risk_score": [10.0]})) is None


def test_osm_totals_tolerate_missing_water_column():
    grid = pd.DataFrame({"park_feature_count": [2, 3]})
    totals = osm_cooling_totals(grid)
    assert totals is not None
    assert totals["park_feature_count"] == 5
    assert totals["water_feature_count"] == 0
    assert totals["amenity_feature_count"] == 0
