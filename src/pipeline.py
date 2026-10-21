"""Build the reproducible local baseline for the cooling planner."""

import argparse
from pathlib import Path

import pandas as pd

from src.real_features import build_real_city_grid
from src.recommendations import rank_interventions
from src.synthetic_data import CITY_PROFILES, create_city_grid


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed"


def run_pipeline(
    mode: str = "synthetic",
    start_date: str = "2024-04-01",
    end_date: str = "2024-06-30",
    max_cloud_cover: float = 30.0,
    cities: list[str] | None = None,
) -> tuple[Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    selected_cities = cities or list(CITY_PROFILES)
    unknown = set(selected_cities).difference(CITY_PROFILES)
    if unknown:
        raise ValueError(f"Unsupported cities: {sorted(unknown)}")
    if mode == "synthetic":
        grids = [create_city_grid(city=city, seed=42 + index) for index, city in enumerate(selected_cities)]
        suffix = ""
    elif mode == "real":
        grids = [
            build_real_city_grid(
                city,
                start_date=start_date,
                end_date=end_date,
                max_cloud_cover=max_cloud_cover,
                raw_dir=ROOT / "data" / "raw",
                metadata_dir=ROOT / "data" / "raw" / "metadata",
            )
            for city in selected_cities
        ]
        suffix = "_real"
    else:
        raise ValueError("mode must be 'synthetic' or 'real'")
    grid = pd.concat(grids, ignore_index=True)
    recommendations = rank_interventions(grid)
    grid_path = OUTPUT / f"heat_risk_grid{suffix}.csv"
    recommendations_path = OUTPUT / f"intervention_recommendations{suffix}.csv"
    grid.to_csv(grid_path, index=False)
    recommendations.to_csv(recommendations_path, index=False)
    return grid_path, recommendations_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the cooling-planner feature and recommendation datasets.")
    parser.add_argument("--mode", choices=["synthetic", "real"], default="synthetic")
    parser.add_argument("--start-date", default="2024-04-01")
    parser.add_argument("--end-date", default="2024-06-30")
    parser.add_argument("--max-cloud-cover", type=float, default=30.0)
    parser.add_argument("--cities", nargs="+", choices=sorted(CITY_PROFILES), default=None)
    args = parser.parse_args()
    grid_file, recommendations_file = run_pipeline(
        mode=args.mode,
        start_date=args.start_date,
        end_date=args.end_date,
        max_cloud_cover=args.max_cloud_cover,
        cities=args.cities,
    )
    print(f"Wrote {grid_file}")
    print(f"Wrote {recommendations_file}")
