"""Budget-aware, explainable intervention recommendations."""

import numpy as np
import pandas as pd


def rank_interventions(grid: pd.DataFrame, budget: float = 1_000_000) -> pd.DataFrame:
    if budget < 0:
        raise ValueError("budget must be non-negative")
    required = {
        "city",
        "grid_id",
        "latitude",
        "longitude",
        "heat_risk_score",
        "population_density",
        "elderly_share",
        "vegetation_index",
        "built_up_fraction",
        "water_access",
    }
    missing = required.difference(grid.columns)
    if missing:
        raise ValueError(f"grid is missing required columns: {sorted(missing)}")

    extra = ["population_count"] if "population_count" in grid.columns else []
    base = grid.loc[:, list(required) + extra].copy()
    city_max = np.maximum(base.groupby("city")["population_density"].transform("max").to_numpy() * 0.18, 1)
    specs = (
        ("Tree planting", 18000, 1.4, 1 - base["vegetation_index"].to_numpy()),
        ("Cool roofs", 32000, 1.8, base["built_up_fraction"].to_numpy()),
        ("Cooling centre", 50000, 0.8, 1 - base["water_access"].to_numpy()),
    )
    frames = []
    for name, cost, cooling, feasibility in specs:
        part = base.copy()
        part["intervention"] = name
        part["cost"] = cost
        part["feasibility"] = np.clip(feasibility, 0.05, 1).round(3)
        part["cooling_reduction_c"] = (cooling * (0.7 + 0.3 * part["heat_risk_score"] / 100)).round(2)
        part["_city_max_population"] = city_max
        frames.append(part)

    result = pd.concat(frames, ignore_index=True)
    risk = result["heat_risk_score"] / 100
    vulnerable_people = result["population_density"] * result["elderly_share"]
    result["priority_score"] = (
        100
        * risk
        * (0.65 * vulnerable_people / result["_city_max_population"] + 0.35 * result["feasibility"])
        * result["cooling_reduction_c"]
        / result["cost"]
    ).round(4)
    exposure = result["population_count"] if "population_count" in result.columns else result["population_density"]
    result["population_benefited"] = (exposure * (0.35 + 0.65 * result["feasibility"])).round()
    result["reason"] = [_reason(record, record["intervention"]) for record in result.to_dict("records")]
    result = (
        result.drop(columns=["_city_max_population"])
        .sort_values("priority_score", ascending=False)
        .reset_index(drop=True)
    )
    result["cumulative_city_cost"] = result.groupby("city", sort=False)["cost"].cumsum()
    result["within_demo_budget"] = result["cumulative_city_cost"] <= budget
    return result


def select_budget_portfolio(recommendations: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Greedily select affordable, highest-priority interventions, at most one per grid cell.

    This is a transparent planning heuristic, not an optimal knapsack solution.
    """
    if budget < 0:
        raise ValueError("budget must be non-negative")
    required = {"city", "grid_id", "cost", "priority_score"}
    missing = required.difference(recommendations.columns)
    if missing:
        raise ValueError(f"recommendations are missing required columns: {sorted(missing)}")
    if recommendations.empty or budget == 0:
        return recommendations.iloc[0:0].copy()

    selected = []
    spent = 0.0
    covered_cells: set[tuple[str, str]] = set()
    ordered = recommendations.sort_values("priority_score", ascending=False, kind="stable")
    for _, candidate in ordered.iterrows():
        cell = (str(candidate["city"]), str(candidate["grid_id"]))
        cost = float(candidate["cost"])
        if cell in covered_cells or cost <= 0 or spent + cost > budget:
            continue
        selected.append(candidate)
        covered_cells.add(cell)
        spent += cost
    if not selected:
        return recommendations.iloc[0:0].copy()
    result = pd.DataFrame(selected).reset_index(drop=True)
    result["portfolio_cumulative_cost"] = result["cost"].cumsum()
    result["portfolio_budget"] = budget
    return result


def _candidate(record: dict, intervention: str, cost: int, cooling: float, feasibility: float) -> dict:
    return {
        "city": record["city"],
        "grid_id": record["grid_id"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "intervention": intervention,
        "cost": cost,
        "cooling_reduction_c": round(cooling * (0.7 + 0.3 * record["heat_risk_score"] / 100), 2),
        "feasibility": round(max(0.05, min(1, feasibility)), 3),
    }


def _reason(record: dict, intervention: str) -> str:
    reasons = []
    if record["heat_risk_score"] >= 60:
        reasons.append("high heat exposure")
    if record["vegetation_index"] < 0.25:
        reasons.append("limited vegetation")
    if record["built_up_fraction"] > 0.7:
        reasons.append("dense built-up area")
    if record["elderly_share"] > 0.11:
        reasons.append("higher elderly vulnerability")
    return f"{intervention}: " + (", ".join(reasons) or "feasible improvement opportunity")
