"""Tests for period-over-period heat-risk trend analysis."""

import pandas as pd
import pytest

from src.synthetic_data import create_city_grid
from src.trend_analysis import city_trend_summary, compare_grid_periods


def test_compare_grid_periods_delta_risk():
    base = create_city_grid(city="Ahmedabad", rows=3, cols=3, seed=1)
    later = base.copy()
    later["heat_risk_score"] = (later["heat_risk_score"] + 5).clip(0, 100)
    later["land_surface_temp_c"] = later["land_surface_temp_c"] + 0.8
    delta = compare_grid_periods(base, later, period_a="t0", period_b="t1")
    assert len(delta) == len(base)
    assert (delta["delta_heat_risk"] == pytest.approx(5.0)).all() or (
        delta["delta_heat_risk"] - 5.0
    ).abs().max() < 1e-6
    assert "delta_lst_c" in delta.columns
    assert delta["period_a"].eq("t0").all()


def test_city_trend_summary_aggregates():
    base = pd.concat(
        [
            create_city_grid(city="Ahmedabad", rows=2, cols=2, seed=1),
            create_city_grid(city="Delhi", rows=2, cols=2, seed=2),
        ],
        ignore_index=True,
    )
    later = base.copy()
    delhi_mask = base["city"] == "Delhi"
    base.loc[delhi_mask, "heat_risk_score"] = 40.0
    later.loc[delhi_mask, "heat_risk_score"] = 45.0
    summary = city_trend_summary(base, later)
    assert set(summary["city"]) == {"Ahmedabad", "Delhi"}
    delhi = summary.loc[summary["city"] == "Delhi"].iloc[0]
    assert delhi["mean_delta_heat_risk"] == pytest.approx(5.0)
    assert delhi["share_risk_up"] == pytest.approx(1.0)
    assert "share_risk_up" in summary.columns


def test_mismatched_ids_raise():
    a = create_city_grid(rows=2, cols=2, seed=1)
    b = create_city_grid(rows=2, cols=2, seed=1).iloc[1:].copy()
    with pytest.raises(ValueError):
        compare_grid_periods(a, b)


def test_duplicate_keys_raise():
    a = create_city_grid(rows=2, cols=2, seed=1)
    dup = pd.concat([a, a.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        compare_grid_periods(dup, dup)
