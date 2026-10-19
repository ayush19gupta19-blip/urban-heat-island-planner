"""Budget-aware, explainable intervention recommendations."""

import pandas as pd


def rank_interventions(grid: pd.DataFrame, budget: float = 1_000_000) -> pd.DataFrame:
    if budget < 0:
        raise ValueError("budget must be non-negative")
    required = {"city", "grid_id", "latitude", "longitude", "heat_risk_score", "population_density", "elderly_share", "vegetation_index", "built_up_fraction", "water_access"}
    missing = required.difference(grid.columns)
    if missing:
        raise ValueError(f"grid is missing required columns: {sorted(missing)}")
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
            item["priority_score"] = round(
                100 * risk * (0.65 * vulnerable_people / max(grid["population_density"].max() * 0.18, 1) + 0.35 * item["feasibility"])
                * item["cooling_reduction_c"] / item["cost"],
                4,
            )
            item["population_benefited"] = round(record["population_density"] * (0.35 + 0.65 * item["feasibility"]))
            item["reason"] = _reason(record, item["intervention"])
            rows.append(item)
    result = pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    result["cumulative_city_cost"] = result.groupby("city")["cost"].cumsum()
    result["within_demo_budget"] = result["cumulative_city_cost"] <= budget
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
