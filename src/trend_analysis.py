"""Period-over-period heat-risk trend helpers.

Compare two grids that share city+grid_id keys (e.g. two seasons or two
pipeline runs) and summarize where risk rose or fell.
"""

from __future__ import annotations

import pandas as pd

KEY = ["city", "grid_id"]


def compare_grid_periods(
    frame_a: pd.DataFrame,
    frame_b: pd.DataFrame,
    *,
    period_a: str = "period_a",
    period_b: str = "period_b",
) -> pd.DataFrame:
    """Join two grids on city+grid_id and compute risk/LST deltas."""
    for label, frame in ((period_a, frame_a), (period_b, frame_b)):
        missing = set(KEY).difference(frame.columns)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
        if "heat_risk_score" not in frame.columns:
            raise ValueError(f"{label} missing heat_risk_score")

    left = frame_a.copy()
    right = frame_b.copy()

    def _unique_key_frame(frame: pd.DataFrame, label: str) -> pd.DataFrame:
        key_frame = frame.copy()
        key_frame["_key"] = list(
            zip(key_frame["city"].astype(str), key_frame["grid_id"].astype(str))
        )
        if key_frame["_key"].duplicated().any():
            raise ValueError(f"{label} has duplicate city+grid_id rows")
        return key_frame

    left = _unique_key_frame(left, period_a)
    right = _unique_key_frame(right, period_b)
    keys_a = set(left["_key"])
    keys_b = set(right["_key"])
    if keys_a != keys_b:
        raise ValueError("period grids must share the same city+grid_id set")

    left = left.drop(columns=["_key"])
    right = right.drop(columns=["_key"])
    keep_a = KEY + [c for c in left.columns if c not in KEY]
    keep_b = KEY + [c for c in right.columns if c not in KEY]
    merged = left.loc[:, keep_a].merge(right.loc[:, keep_b], on=KEY, suffixes=("_a", "_b"))

    risk_a = pd.to_numeric(merged["heat_risk_score_a"], errors="coerce")
    risk_b = pd.to_numeric(merged["heat_risk_score_b"], errors="coerce")
    merged["delta_heat_risk"] = (risk_b - risk_a).round(2)

    if "land_surface_temp_c_a" in merged.columns and "land_surface_temp_c_b" in merged.columns:
        lst_a = pd.to_numeric(merged["land_surface_temp_c_a"], errors="coerce")
        lst_b = pd.to_numeric(merged["land_surface_temp_c_b"], errors="coerce")
        merged["delta_lst_c"] = (lst_b - lst_a).round(2)
    else:
        merged["delta_lst_c"] = float("nan")

    merged["period_a"] = period_a
    merged["period_b"] = period_b
    merged["risk_up"] = (merged["delta_heat_risk"] > 0).astype(int)
    merged["risk_down"] = (merged["delta_heat_risk"] < 0).astype(int)
    return merged


def city_trend_summary(
    frame_a: pd.DataFrame,
    frame_b: pd.DataFrame,
    *,
    period_a: str = "period_a",
    period_b: str = "period_b",
) -> pd.DataFrame:
    """City-level mean deltas and share of cells with rising risk."""
    delta = compare_grid_periods(frame_a, frame_b, period_a=period_a, period_b=period_b)
    rows = []
    for city, part in delta.groupby("city", sort=True):
        rows.append(
            {
                "city": city,
                "n_cells": int(len(part)),
                "mean_delta_heat_risk": round(float(part["delta_heat_risk"].mean()), 3),
                "mean_delta_lst_c": (
                    round(float(part["delta_lst_c"].mean()), 3)
                    if part["delta_lst_c"].notna().any()
                    else float("nan")
                ),
                "share_risk_up": round(float(part["risk_up"].mean()), 4),
                "share_risk_down": round(float(part["risk_down"].mean()), 4),
                "period_a": period_a,
                "period_b": period_b,
            }
        )
    return pd.DataFrame(rows)
