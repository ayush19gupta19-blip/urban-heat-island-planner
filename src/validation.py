"""Compare satellite LST to NASA POWER 2 m air temperature.

This is a screening check, not scientific validation. LST is skin temperature;
POWER T2M is air temperature at one city point.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REQUIRED = {"city", "land_surface_temp_c", "weather_mean_temp_c", "heat_risk_score"}


def city_lst_air_gap(grid: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED.difference(grid.columns)
    if missing:
        raise ValueError(f"grid is missing required columns: {sorted(missing)}")
    rows = []
    for city, part in grid.groupby("city", sort=True):
        lst = pd.to_numeric(part["land_surface_temp_c"], errors="coerce")
        air = pd.to_numeric(part["weather_mean_temp_c"], errors="coerce")
        risk = pd.to_numeric(part["heat_risk_score"], errors="coerce")
        rows.append(
            {
                "city": city,
                "n_cells": int(len(part)),
                "mean_lst_c": round(float(lst.mean()), 2) if lst.notna().any() else float("nan"),
                "air_temp_c": round(float(air.mean()), 2) if air.notna().any() else float("nan"),
                "lst_minus_air_c": round(float((lst - air).mean()), 2) if lst.notna().any() and air.notna().any() else float("nan"),
                "high_critical_share": round(float((risk >= 60).mean()), 3),
                "validated": False,
                "note": "LST is satellite skin temperature; air_temp_c is NASA POWER T2M at the city point",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize LST vs NASA POWER air temperature by city.")
    parser.add_argument("grid", nargs="?", default="data/processed/heat_risk_grid_real.csv")
    parser.add_argument("--out", default="data/processed/lst_air_gap.csv")
    args = parser.parse_args()
    path = Path(args.grid)
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run python -m src.pipeline --mode real first.")
    summary = city_lst_air_gap(pd.read_csv(path))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False)
    print(summary.to_string(index=False))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
