"""Hotspot tail metrics for heat-risk grids.

Peer cooling tools plan on the hot tail, not only the city mean. This module
selects high-percentile cells and summarizes LST, elderly share, and vegetation.
"""

from __future__ import annotations

import pandas as pd

REQUIRED = {"city", "grid_id", "heat_risk_score"}


def select_hotspot_cells(grid: pd.DataFrame, percentile: float = 75.0) -> pd.DataFrame:
    """Return cells at or above the given heat-risk percentile (per whole frame)."""
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")
    missing = REQUIRED.difference(grid.columns)
    if missing:
        raise ValueError(f"grid missing columns: {sorted(missing)}")
    if grid.empty:
        return grid.copy()

    risk = pd.to_numeric(grid["heat_risk_score"], errors="coerce")
    threshold = float(risk.quantile(percentile / 100.0))
    return grid.loc[risk >= threshold].copy()


def city_hotspot_summary(grid: pd.DataFrame, percentile: float = 75.0) -> pd.DataFrame:
    """Per-city hotspot counts and mean exposure traits."""
    if grid.empty:
        return pd.DataFrame(
            columns=[
                "city",
                "n_cells",
                "n_hotspot_cells",
                "hotspot_share",
                "mean_hotspot_risk",
                "mean_hotspot_lst_c",
                "mean_hotspot_elderly_share",
                "mean_hotspot_vegetation",
                "percentile",
            ]
        )
    missing = REQUIRED.difference(grid.columns)
    if missing:
        raise ValueError(f"grid missing columns: {sorted(missing)}")

    rows = []
    for city, part in grid.groupby("city", sort=True):
        hot = select_hotspot_cells(part, percentile=percentile)
        n = len(part)
        nh = len(hot)

        def _mean(frame: pd.DataFrame, column: str) -> float:
            if column not in frame.columns or frame.empty:
                return float("nan")
            series = pd.to_numeric(frame[column], errors="coerce")
            return float(series.mean()) if series.notna().any() else float("nan")

        rows.append(
            {
                "city": city,
                "n_cells": n,
                "n_hotspot_cells": nh,
                "hotspot_share": round(nh / n, 4) if n else 0.0,
                "mean_hotspot_risk": round(_mean(hot, "heat_risk_score"), 2),
                "mean_hotspot_lst_c": round(_mean(hot, "land_surface_temp_c"), 2),
                "mean_hotspot_elderly_share": round(_mean(hot, "elderly_share"), 4),
                "mean_hotspot_vegetation": round(_mean(hot, "vegetation_index"), 4),
                "percentile": percentile,
            }
        )
    return pd.DataFrame(rows)
