"""Equity-aware cooling portfolio scenarios and multi-city comparison.

Extends the greedy budget planner with:
- cooling-effect scenarios (conservative / base / optimistic)
- coverage of high-risk and high-elderly cells (equity metrics)
- multi-city comparison under a shared or per-city budget

These helpers are planning screens, not calibrated impact models.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from src.recommendations import rank_interventions, select_budget_portfolio

# Multipliers applied to modeled cooling_reduction_c for scenario labels.
COOLING_SCENARIOS: dict[str, float] = {
    "conservative": 0.7,
    "base": 1.0,
    "optimistic": 1.3,
}

HIGH_RISK_THRESHOLD = 60.0
HIGH_ELDERLY_SHARE = 0.11


def apply_cooling_scenario(
    recommendations: pd.DataFrame,
    scenario: str = "base",
) -> pd.DataFrame:
    """Scale cooling effects and recompute priority under a named scenario."""
    if scenario not in COOLING_SCENARIOS:
        raise ValueError(
            f"Unknown scenario {scenario!r}. Choose from {sorted(COOLING_SCENARIOS)}"
        )
    if recommendations.empty:
        return recommendations.copy()
    required = {"cooling_reduction_c", "priority_score", "cost"}
    missing = required.difference(recommendations.columns)
    if missing:
        raise ValueError(f"recommendations are missing required columns: {sorted(missing)}")

    factor = COOLING_SCENARIOS[scenario]
    frame = recommendations.copy()
    base_cooling = pd.to_numeric(frame["cooling_reduction_c"], errors="coerce")
    # Recover the pre-scenario priority contribution of cooling when possible.
    frame["cooling_reduction_c"] = (base_cooling * factor).round(2)
    # Priority is proportional to cooling_reduction_c in rank_interventions.
    frame["priority_score"] = (
        pd.to_numeric(frame["priority_score"], errors="coerce") * factor
    ).round(4)
    frame["cooling_scenario"] = scenario
    frame["cooling_scenario_factor"] = factor
    return frame.sort_values("priority_score", ascending=False, kind="stable").reset_index(
        drop=True
    )


def portfolio_equity_metrics(
    grid: pd.DataFrame,
    portfolio: pd.DataFrame,
    *,
    high_risk_threshold: float = HIGH_RISK_THRESHOLD,
    high_elderly_share: float = HIGH_ELDERLY_SHARE,
) -> dict[str, float]:
    """Measure how well a selected portfolio covers vulnerable high-risk cells."""
    required_grid = {"city", "grid_id", "heat_risk_score", "elderly_share"}
    missing = required_grid.difference(grid.columns)
    if missing:
        raise ValueError(f"grid is missing required columns: {sorted(missing)}")

    if grid.empty:
        return {
            "n_cells": 0,
            "high_risk_cells": 0,
            "high_elderly_high_risk_cells": 0,
            "portfolio_cells": 0,
            "high_risk_coverage": 0.0,
            "equity_coverage": 0.0,
            "mean_cooling_c": 0.0,
            "total_cost": 0.0,
            "population_reached": 0.0,
        }

    high_risk = pd.to_numeric(grid["heat_risk_score"], errors="coerce") >= high_risk_threshold
    elderly = pd.to_numeric(grid["elderly_share"], errors="coerce") >= high_elderly_share
    priority_mask = high_risk & elderly

    selected_ids: set[str] = set()
    if not portfolio.empty and {"grid_id"}.issubset(portfolio.columns):
        selected_ids = set(portfolio["grid_id"].astype(str))

    covered_high = int(
        grid.loc[high_risk, "grid_id"].astype(str).isin(selected_ids).sum()
    ) if high_risk.any() else 0
    covered_equity = int(
        grid.loc[priority_mask, "grid_id"].astype(str).isin(selected_ids).sum()
    ) if priority_mask.any() else 0

    n_high = int(high_risk.sum())
    n_equity = int(priority_mask.sum())
    mean_cooling = (
        float(pd.to_numeric(portfolio["cooling_reduction_c"], errors="coerce").mean())
        if not portfolio.empty and "cooling_reduction_c" in portfolio.columns
        else 0.0
    )
    total_cost = (
        float(pd.to_numeric(portfolio["cost"], errors="coerce").sum())
        if not portfolio.empty and "cost" in portfolio.columns
        else 0.0
    )
    population_reached = 0.0
    if not portfolio.empty and "population_benefited" in portfolio.columns:
        population_reached = float(
            pd.to_numeric(portfolio["population_benefited"], errors="coerce").fillna(0).sum()
        )

    return {
        "n_cells": int(len(grid)),
        "high_risk_cells": n_high,
        "high_elderly_high_risk_cells": n_equity,
        "portfolio_cells": int(len(selected_ids)),
        "high_risk_coverage": round(covered_high / n_high, 4) if n_high else 0.0,
        "equity_coverage": round(covered_equity / n_equity, 4) if n_equity else 0.0,
        "mean_cooling_c": round(mean_cooling, 3),
        "total_cost": round(total_cost, 2),
        "population_reached": round(population_reached, 1),
    }


def compare_scenarios(
    grid: pd.DataFrame,
    budget: float,
    scenarios: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Build portfolios under each cooling scenario and report equity metrics."""
    if budget < 0:
        raise ValueError("budget must be non-negative")
    scenario_names = list(scenarios) if scenarios is not None else list(COOLING_SCENARIOS)
    base_candidates = rank_interventions(grid, budget=max(budget, 1_000_000))
    rows = []
    for name in scenario_names:
        scaled = apply_cooling_scenario(base_candidates, scenario=name)
        portfolio = select_budget_portfolio(scaled, budget=budget)
        metrics = portfolio_equity_metrics(grid, portfolio)
        rows.append(
            {
                "scenario": name,
                "scenario_factor": COOLING_SCENARIOS[name],
                "budget": budget,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def compare_cities(
    grid: pd.DataFrame,
    budget_per_city: float,
    *,
    scenario: str = "base",
) -> pd.DataFrame:
    """Run the scenario planner independently for every city in the grid."""
    if budget_per_city < 0:
        raise ValueError("budget_per_city must be non-negative")
    if "city" not in grid.columns:
        raise ValueError("grid is missing required column: city")
    if grid.empty:
        return pd.DataFrame(
            columns=[
                "city",
                "scenario",
                "budget",
                "n_cells",
                "high_risk_cells",
                "high_elderly_high_risk_cells",
                "portfolio_cells",
                "high_risk_coverage",
                "equity_coverage",
                "mean_cooling_c",
                "total_cost",
                "population_reached",
            ]
        )

    rows = []
    for city, part in grid.groupby("city", sort=True):
        scenario_table = compare_scenarios(part, budget=budget_per_city, scenarios=[scenario])
        record = scenario_table.iloc[0].to_dict()
        record["city"] = city
        rows.append(record)
    frame = pd.DataFrame(rows)
    # Stable column order with city first.
    ordered = ["city"] + [c for c in frame.columns if c != "city"]
    return frame.loc[:, ordered]


def equity_gap_report(city_comparison: pd.DataFrame) -> dict[str, object]:
    """Summarize which city lags on equity coverage under a shared budget rule."""
    if city_comparison.empty or "equity_coverage" not in city_comparison.columns:
        return {
            "n_cities": 0,
            "mean_equity_coverage": 0.0,
            "min_equity_coverage": 0.0,
            "max_equity_coverage": 0.0,
            "lagging_city": None,
            "leading_city": None,
            "equity_spread": 0.0,
        }
    frame = city_comparison.copy()
    frame["equity_coverage"] = pd.to_numeric(frame["equity_coverage"], errors="coerce").fillna(0.0)
    lagging_idx = frame["equity_coverage"].idxmin()
    leading_idx = frame["equity_coverage"].idxmax()
    return {
        "n_cities": int(len(frame)),
        "mean_equity_coverage": round(float(frame["equity_coverage"].mean()), 4),
        "min_equity_coverage": round(float(frame["equity_coverage"].min()), 4),
        "max_equity_coverage": round(float(frame["equity_coverage"].max()), 4),
        "lagging_city": str(frame.loc[lagging_idx, "city"]) if "city" in frame.columns else None,
        "leading_city": str(frame.loc[leading_idx, "city"]) if "city" in frame.columns else None,
        "equity_spread": round(
            float(frame["equity_coverage"].max() - frame["equity_coverage"].min()), 4
        ),
    }


def rank_weight_sensitivity(
    grid: pd.DataFrame,
    *,
    budget: float = 1_000_000,
    jitters: tuple[float, ...] = (0.85, 1.0, 1.15),
) -> pd.DataFrame:
    """Jitter heat-risk scores and measure portfolio cell stability.

    This is a lightweight robustness screen: cells that remain selected across
    jittered risk scores are more stable planning candidates.
    """
    if budget < 0:
        raise ValueError("budget must be non-negative")
    if "heat_risk_score" not in grid.columns:
        raise ValueError("grid is missing required column: heat_risk_score")
    if grid.empty:
        return pd.DataFrame(columns=["grid_id", "city", "selection_count", "selection_share", "stable"])

    selection_counts: dict[tuple[str, str], int] = {}
    n_runs = 0
    base_risk = pd.to_numeric(grid["heat_risk_score"], errors="coerce").fillna(0.0)
    for factor in jitters:
        n_runs += 1
        trial = grid.copy()
        trial["heat_risk_score"] = np.clip(base_risk * factor, 0, 100).round(2)
        candidates = rank_interventions(trial, budget=max(budget, 1_000_000))
        portfolio = select_budget_portfolio(candidates, budget=budget)
        if portfolio.empty:
            continue
        for _, row in portfolio.iterrows():
            key = (str(row["city"]), str(row["grid_id"]))
            selection_counts[key] = selection_counts.get(key, 0) + 1

    if not selection_counts:
        return pd.DataFrame(columns=["grid_id", "city", "selection_count", "selection_share", "stable"])

    rows = [
        {
            "city": city,
            "grid_id": grid_id,
            "selection_count": count,
            "selection_share": round(count / n_runs, 3),
            "stable": count == n_runs,
        }
        for (city, grid_id), count in selection_counts.items()
    ]
    return (
        pd.DataFrame(rows)
        .sort_values(["selection_share", "city", "grid_id"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
