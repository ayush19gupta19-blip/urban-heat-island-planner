"""Budget-aware, explainable intervention recommendations."""

import pandas as pd


def rank_interventions(grid: pd.DataFrame, budget: float = 1_000_000) -> pd.DataFrame:
    if budget < 0:
        raise ValueError("budget must be non-negative")
    required = {"city", "grid_id", "latitude", "longitude", "heat_risk_score", "population_density", "elderly_share", "vegetation_index", "built_up_fraction", "water_access"}
    missing = required.difference(grid.columns)
    if missing:
        raise ValueError(f"grid is missing required columns: {sorted(missing)}")
    city_population_max = grid.groupby("city")["population_density"].max().to_dict()
    rows: list[dict] = []
    for record in grid.to_dict("records"):
        risk = record["heat_risk_score"] / 100
        vulnerable_people = record["population_density"] * record["elderly_share"]
        candidates = [
            _candidate(record, "Tree planting", cost=18000, cooling=1.4, feasibility=1 - record["vegetation_index"]),
            _candidate(record, "Cool roofs", cost=32000, cooling=1.8, feasibility=record["built_up_fraction"]),
            _candidate(record, "Cooling centre", cost=50000, cooling=0.8, feasibility=1 - record["water_access"]),
        ]
        for item in candidates:
            city_max_population = max(city_population_max[record["city"]] * 0.18, 1)
            item["priority_score"] = round(
                100 * risk * (0.65 * vulnerable_people / city_max_population + 0.35 * item["feasibility"])
                * item["cooling_reduction_c"] / item["cost"],
                4,
            )
            exposure = record.get("population_count", record["population_density"])
            item["population_benefited"] = round(exposure * (0.35 + 0.65 * item["feasibility"]))
            item["reason"] = _reason(record, item["intervention"])
            rows.append(item)
    result = pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    result["cumulative_city_cost"] = result.groupby("city")["cost"].cumsum()
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
