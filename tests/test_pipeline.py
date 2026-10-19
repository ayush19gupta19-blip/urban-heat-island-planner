import pandas as pd

from src.recommendations import rank_interventions
from src.pipeline import run_pipeline
from src.synthetic_data import create_city_grid


def test_grid_is_reproducible_and_has_expected_features():
    first = create_city_grid(rows=4, cols=5)
    second = create_city_grid(rows=4, cols=5)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 20
    assert first["heat_risk_score"].between(0, 100).all()
    assert set(first["risk_category"]) <= {"Low", "Moderate", "High", "Critical"}
    assert first["city"].eq("Ahmedabad").all()


def test_supported_cities_have_distinct_coordinates():
    cities = {city: create_city_grid(city=city, rows=2, cols=2) for city in ["Ahmedabad", "Delhi", "Kolkata"]}
    assert set(cities) == {"Ahmedabad", "Delhi", "Kolkata"}
    assert len({round(frame["latitude"].mean(), 1) for frame in cities.values()}) == 3
    assert len(create_city_grid(city="Delhi", rows=1, cols=1)) == 1


def test_recommendations_are_ranked_and_explainable():
    grid = create_city_grid(rows=3, cols=3)
    recommendations = rank_interventions(grid)
    assert len(recommendations) == 27
    assert recommendations["priority_score"].is_monotonic_decreasing
    assert recommendations["reason"].str.len().gt(0).all()
    assert recommendations.groupby("city")["cumulative_city_cost"].max().eq(900000).all()


def test_pipeline_writes_all_three_cities():
    grid_path, recommendations_path = run_pipeline()
    grid = pd.read_csv(grid_path)
    recommendations = pd.read_csv(recommendations_path)
    assert set(grid["city"]) == {"Ahmedabad", "Delhi", "Kolkata"}
    assert set(recommendations["city"]) == {"Ahmedabad", "Delhi", "Kolkata"}
