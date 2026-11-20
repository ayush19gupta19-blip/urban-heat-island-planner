import pandas as pd
import pytest

from src.scenario_planning import (
    COOLING_SCENARIOS,
    apply_cooling_scenario,
    compare_cities,
    compare_scenarios,
    equity_gap_report,
    portfolio_equity_metrics,
    rank_weight_sensitivity,
)
from src.recommendations import rank_interventions, select_budget_portfolio
from src.synthetic_data import create_city_grid


def test_apply_cooling_scenario_scales_effects_and_priority():
    grid = create_city_grid(rows=3, cols=3)
    base = rank_interventions(grid)
    optimistic = apply_cooling_scenario(base, "optimistic")
    conservative = apply_cooling_scenario(base, "conservative")
    assert optimistic["cooling_scenario"].eq("optimistic").all()
    assert optimistic["cooling_reduction_c"].iloc[0] == pytest.approx(
        round(base["cooling_reduction_c"].iloc[0] * COOLING_SCENARIOS["optimistic"], 2)
    )
    assert conservative["priority_score"].iloc[0] < base["priority_score"].iloc[0]
    assert optimistic["priority_score"].iloc[0] > base["priority_score"].iloc[0]


def test_apply_cooling_scenario_rejects_unknown_label():
    grid = create_city_grid(rows=2, cols=2)
    base = rank_interventions(grid)
    with pytest.raises(ValueError, match="Unknown scenario"):
        apply_cooling_scenario(base, "fantasy")


def test_portfolio_equity_metrics_report_coverage():
    grid = create_city_grid(rows=4, cols=4)
    candidates = rank_interventions(grid)
    portfolio = select_budget_portfolio(candidates, budget=150_000)
    metrics = portfolio_equity_metrics(grid, portfolio)
    assert metrics["n_cells"] == 16
    assert 0.0 <= metrics["high_risk_coverage"] <= 1.0
    assert 0.0 <= metrics["equity_coverage"] <= 1.0
    assert metrics["portfolio_cells"] == len(portfolio)
    assert metrics["total_cost"] <= 150_000


def test_compare_scenarios_returns_all_named_rows():
    grid = create_city_grid(rows=3, cols=3)
    table = compare_scenarios(grid, budget=120_000)
    assert set(table["scenario"]) == set(COOLING_SCENARIOS)
    assert (table["budget"] == 120_000).all()
    assert table["portfolio_cells"].ge(0).all()


def test_compare_cities_and_equity_gap():
    cities = pd.concat(
        [
            create_city_grid(city="Ahmedabad", rows=3, cols=3, seed=1),
            create_city_grid(city="Delhi", rows=3, cols=3, seed=2),
            create_city_grid(city="Kolkata", rows=3, cols=3, seed=3),
        ],
        ignore_index=True,
    )
    comparison = compare_cities(cities, budget_per_city=100_000, scenario="base")
    assert set(comparison["city"]) == {"Ahmedabad", "Delhi", "Kolkata"}
    gap = equity_gap_report(comparison)
    assert gap["n_cities"] == 3
    assert gap["lagging_city"] in set(comparison["city"])
    assert gap["leading_city"] in set(comparison["city"])
    assert gap["equity_spread"] >= 0


def test_rank_weight_sensitivity_marks_stable_cells():
    grid = create_city_grid(rows=4, cols=4)
    stability = rank_weight_sensitivity(grid, budget=200_000)
    assert not stability.empty
    assert stability["selection_share"].between(0, 1).all()
    assert set(stability["stable"]).issubset({True, False})
    # Stable rows must have been selected in every jitter run
    if stability["stable"].any():
        assert stability.loc[stability["stable"], "selection_share"].eq(1.0).all()


def test_empty_grid_paths_are_safe():
    empty = create_city_grid(rows=1, cols=1).iloc[0:0]
    metrics = portfolio_equity_metrics(empty, empty)
    assert metrics["n_cells"] == 0
    assert compare_cities(empty, budget_per_city=50_000).empty
    assert rank_weight_sensitivity(empty, budget=50_000).empty
