"""Column-safe summaries for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd


def population_quality(grid: pd.DataFrame) -> dict[str, float] | None:
    """Return WorldPop coverage stats, or None if this grid has no population counts."""
    if "population_count" not in grid.columns:
        return None
    total_population = float(pd.to_numeric(grid["population_count"], errors="coerce").fillna(0).sum())
    if "elderly_population_65_plus" in grid.columns:
        elderly_population = float(pd.to_numeric(grid["elderly_population_65_plus"], errors="coerce").fillna(0).sum())
    elif "elderly_share" in grid.columns:
        elderly_population = float(
            (
                pd.to_numeric(grid["population_count"], errors="coerce").fillna(0)
                * pd.to_numeric(grid["elderly_share"], errors="coerce").fillna(0)
            ).sum()
        )
    else:
        elderly_population = 0.0
    def mean_coverage(column: str) -> float:
        if column not in grid.columns:
            return 1.0
        coverage = pd.to_numeric(grid[column], errors="coerce").mean()
        # An all-null coverage column has no measured coverage; avoid leaking
        # NaN into dashboard metrics and formatted percentages.
        return float(coverage) if pd.notna(coverage) else 0.0

    population_coverage = mean_coverage("population_data_coverage")
    elderly_coverage = mean_coverage("elderly_data_coverage")
    return {
        "total_population": total_population,
        "elderly_population": elderly_population,
        "population_coverage": population_coverage,
        "elderly_coverage": elderly_coverage,
        "elderly_share": (elderly_population / total_population) if total_population else 0.0,
        "has_coverage_columns": "population_data_coverage" in grid.columns,
    }


def osm_cooling_totals(grid: pd.DataFrame) -> dict[str, float] | None:
    """Return OSM feature totals when at least one cooling-layer column exists."""
    columns = ("park_feature_count", "water_feature_count", "amenity_feature_count")
    if not any(name in grid.columns for name in columns):
        return None
    totals = {}
    for name in columns:
        totals[name] = float(pd.to_numeric(grid[name], errors="coerce").fillna(0).sum()) if name in grid.columns else 0.0
    source = "OpenStreetMap"
    if "osm_cooling_data_source" in grid.columns and len(grid):
        source = str(grid["osm_cooling_data_source"].iloc[0])
    totals["source"] = source
    return totals
