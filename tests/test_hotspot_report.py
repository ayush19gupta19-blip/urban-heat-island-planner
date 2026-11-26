"""Tests for heat hotspot tail reporting."""

import pandas as pd
import pytest

from src.hotspot_report import city_hotspot_summary, select_hotspot_cells
from src.synthetic_data import create_city_grid


def test_select_hotspot_cells_top_quartile_by_risk():
    grid = create_city_grid(rows=4, cols=4, seed=7)
    hot = select_hotspot_cells(grid, percentile=75)
    assert len(hot) >= 1
    assert hot["heat_risk_score"].min() >= grid["heat_risk_score"].quantile(0.75) - 1e-9
    assert set(hot.columns) >= {"city", "grid_id", "heat_risk_score"}


def test_city_hotspot_summary_has_expected_metrics():
    grid = pd.concat(
        [
            create_city_grid(city="Ahmedabad", rows=3, cols=3, seed=1),
            create_city_grid(city="Delhi", rows=3, cols=3, seed=2),
        ],
        ignore_index=True,
    )
    summary = city_hotspot_summary(grid, percentile=75)
    assert set(summary["city"]) == {"Ahmedabad", "Delhi"}
    for col in (
        "n_hotspot_cells",
        "hotspot_share",
        "mean_hotspot_risk",
        "mean_hotspot_lst_c",
        "mean_hotspot_elderly_share",
        "mean_hotspot_vegetation",
    ):
        assert col in summary.columns
    assert summary["hotspot_share"].between(0, 1).all()


def test_rejects_bad_percentile_and_empty():
    grid = create_city_grid(rows=2, cols=2)
    with pytest.raises(ValueError):
        select_hotspot_cells(grid, percentile=120)
    empty = grid.iloc[0:0]
    assert select_hotspot_cells(empty, percentile=75).empty
    assert city_hotspot_summary(empty).empty
