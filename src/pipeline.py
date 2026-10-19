"""Build the reproducible local baseline for the cooling planner."""

from pathlib import Path

import pandas as pd

from src.recommendations import rank_interventions
from src.synthetic_data import CITY_PROFILES, create_city_grid


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "processed"


def run_pipeline() -> tuple[Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    grids = [create_city_grid(city=city, seed=42 + index) for index, city in enumerate(CITY_PROFILES)]
    grid = pd.concat(grids, ignore_index=True)
    recommendations = rank_interventions(grid)
    grid_path = OUTPUT / "heat_risk_grid.csv"
    recommendations_path = OUTPUT / "intervention_recommendations.csv"
    grid.to_csv(grid_path, index=False)
    recommendations.to_csv(recommendations_path, index=False)
    return grid_path, recommendations_path


if __name__ == "__main__":
    grid_file, recommendations_file = run_pipeline()
    print(f"Wrote {grid_file}")
    print(f"Wrote {recommendations_file}")
