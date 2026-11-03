"""Streamlit dashboard for the local cooling planner MVP."""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Streamlit Cloud may launch this script with ``app/`` as the import root.
# Add the repository root explicitly so the sibling ``src`` package resolves
# consistently both locally and in the hosted app.
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.pipeline import run_pipeline
from src.recommendations import rank_interventions, select_budget_portfolio


@st.cache_data(show_spinner=False)
def load_grid(path: str, modified_ns: int) -> pd.DataFrame:
    """Read each generated grid once, and refresh the cache when it changes."""
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def get_recommendations(grid: pd.DataFrame) -> pd.DataFrame:
    """Reuse the city ranking across Streamlit reruns and budget adjustments."""
    return rank_interventions(grid)


@st.cache_data(show_spinner=False)
def get_portfolio(candidates: pd.DataFrame, budget: float) -> pd.DataFrame:
    return select_budget_portfolio(candidates, budget)


@st.cache_data(show_spinner=False)
def make_heat_map(grid: pd.DataFrame) -> object:
    """Cache Plotly's map figure because Streamlit reruns on every control change."""
    fig = px.scatter_map(
        grid,
        lat="latitude",
        lon="longitude",
        color="heat_risk_score",
        size="heat_risk_score",
        size_max=18,
        opacity=0.82,
        hover_name="grid_id",
        hover_data=["risk_category", "land_surface_temp_c", "vegetation_index", "population_density"],
        color_continuous_scale="RdYlBu_r",
        zoom=10,
        height=460,
    )
    fig.update_layout(
        map_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar={"title": "Risk", "thickness": 12},
    )
    return fig


st.set_page_config(page_title="Urban Heat Island Cooling Planner", layout="wide")
st.title("Urban Heat Island Cooling Planner")
st.caption("Ahmedabad | Delhi | Kolkata | decision-support prototype")

processed_dir = root / "data" / "processed"
synthetic_grid_path = processed_dir / "heat_risk_grid.csv"
synthetic_recommendations_path = processed_dir / "intervention_recommendations.csv"
real_grid_path = processed_dir / "heat_risk_grid_real.csv"
real_recommendations_path = processed_dir / "intervention_recommendations_real.csv"
if not synthetic_grid_path.exists() or not synthetic_recommendations_path.exists():
    run_pipeline()

mode = st.sidebar.selectbox(
    "Data mode",
    ["Synthetic demo", "Real remote sensing"] if real_grid_path.exists() else ["Synthetic demo"],
)
if mode == "Real remote sensing":
    grid_path, recommendations_path = real_grid_path, real_recommendations_path
    st.sidebar.success("NASA POWER, Landsat, Sentinel-2, and WorldPop 2020")
else:
    grid_path, recommendations_path = synthetic_grid_path, synthetic_recommendations_path
    st.sidebar.info("Run `python -m src.pipeline --mode real` to build real-data outputs")

grid_all = load_grid(str(grid_path), grid_path.stat().st_mtime_ns)
city = st.selectbox("City", sorted(grid_all["city"].unique()))
grid = grid_all[grid_all["city"] == city].copy()

with st.expander("How to read the heat-risk score", expanded=False):
    st.markdown(
        """
        The 0–100 score is a **screening index**, not a temperature, probability, or health forecast. """
        """The current method combines normalized land-surface temperature (42%), built-up fraction (22%), """
        """population density (18%), age-65+ share (10%), and limited water access (8%). """
        """Synthetic mode uses generated demographic proxies; real mode uses modeled WorldPop 2020 population and age estimates. """
        """These weights and intervention effects are planning assumptions, not locally calibrated estimates. """
        """Normalization is performed within each city's grid for the selected input data, so scores should not """
        """be compared across cities or dates as if they were on a calibrated common scale. See """
        """[the methodology](https://github.com/ayush19gupta19-blip/urban-heat-island-planner/blob/master/docs/methodology.md) """
        """for details. This prototype is not an emergency alert."""
    )

st.subheader("Data quality and coverage")
if mode == "Real remote sensing":
    if "landsat_valid" in grid and "sentinel_valid" in grid:
        landsat_pct = 100 * grid["landsat_valid"].astype(bool).mean()
        sentinel_pct = 100 * grid["sentinel_valid"].astype(bool).mean()
        joint_pct = 100 * grid.get("remote_sensing_valid", pd.Series(False, index=grid.index)).astype(bool).mean()
        q1, q2, q3 = st.columns(3)
        q1.metric("Landsat valid grid cells", f"{landsat_pct:.1f}%")
        q2.metric("Sentinel-2 valid grid cells", f"{sentinel_pct:.1f}%")
        q3.metric("Both sources valid", f"{joint_pct:.1f}%")
        imputed = int(grid.get("remote_sensing_imputed", pd.Series(False, index=grid.index)).astype(bool).sum())
        st.caption(f"{imputed} of {len(grid)} cells have at least one imputed satellite feature. Missing values are median-filled for the current score.")
    else:
        st.warning("This real-data output has no per-cell satellite quality flags. Rebuild it with the current pipeline to see coverage.")

    weather_cols = [name for name in ["weather_observation_days", "weather_missing_days"] if name in grid]
    if weather_cols:
        observed = int(grid["weather_observation_days"].iloc[0])
        missing = int(grid["weather_missing_days"].iloc[0])
        st.caption(f"NASA POWER daily temperature observations: {observed} available day(s), {missing} missing day(s) in the selected period.")

    if "population_count" in grid:
        population_coverage = 100 * grid["population_data_coverage"].mean()
        elderly_coverage = 100 * grid["elderly_data_coverage"].mean()
        total_population = float(grid["population_count"].sum())
        elderly_population = float(grid["elderly_population_65_plus"].sum())
        estimated_elderly_share = elderly_population / total_population if total_population else 0
        p1, p2, p3 = st.columns(3)
        p1.metric("WorldPop grid coverage", f"{population_coverage:.1f}%")
        p2.metric("Age 65+ grid coverage", f"{elderly_coverage:.1f}%")
        p3.metric("Estimated age 65+ share", f"{estimated_elderly_share:.1%}")
        st.caption("WorldPop population and age estimates represent 2020 at about 1 km resolution; they are modeled estimates, not current ward census counts.")

    metadata_path = root / "data" / "raw" / "metadata" / f"{city[:3].lower()}_satellite.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            with st.expander("Satellite scenes used"):
                st.json(metadata)
        except (OSError, json.JSONDecodeError):
            st.caption("Satellite scene metadata could not be read. Rebuild the real-data output to refresh it.")
    else:
        st.caption("Scene metadata is not present. Rebuild the real-data pipeline to record the selected scenes.")
else:
    st.info("Synthetic demo mode: every value is generated for demonstration. Its coverage indicators are not observations of real conditions.")

population_sources = grid.get("population_data_source", pd.Series("unspecified proxy", index=grid.index)).dropna().unique()
population_note = "; ".join(map(str, population_sources))

left, middle, right = st.columns(3)
high_cells = grid["heat_risk_score"] >= 60
left.metric("Grid cells", f"{len(grid):,}")
middle.metric("High/Critical cells", f"{high_cells.sum():,}")
if mode == "Real remote sensing" and "population_count" in grid:
    right.metric("Estimated population in high/critical cells", f"{grid.loc[high_cells, 'population_count'].sum():,.0f}")
    st.caption(f"Modeled WorldPop 2020 estimate, not a current headcount. Source: {population_note}.")
else:
    right.metric("Population proxy in high/critical cells", f"{grid.loc[high_cells, 'population_density'].sum():,.0f}")
    st.caption(f"Exposure proxy only, not a count of people. Source: {population_note}.")

st.subheader("Heat-risk map")
st.plotly_chart(make_heat_map(grid), use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})

st.subheader("Budget planner")
budget = st.number_input(
    "Available budget for this city (INR)",
    min_value=0,
    max_value=10_000_000,
    value=1_000_000,
    step=50_000,
    help="Illustrative intervention costs are used. The planner greedily selects the highest-priority affordable option, at most one intervention per grid cell.",
)
candidates = get_recommendations(grid)
portfolio = get_portfolio(candidates, float(budget))
spent = float(portfolio["cost"].sum()) if not portfolio.empty else 0
remaining = float(budget) - spent
estimated_sites = len(portfolio)
mean_cooling = float(portfolio["cooling_reduction_c"].mean()) if estimated_sites and "cooling_reduction_c" in portfolio else 0

m1, m2, m3 = st.columns(3)
m1.metric("Illustrative budget used (INR)", f"{spent:,.0f}")
m2.metric("Grid cells selected", f"{estimated_sites:,}")
m3.metric("Mean modeled cooling effect", f"{mean_cooling:.2f} C" if estimated_sites else "- ")
st.caption(f"Unallocated: INR {remaining:,.0f}. Cooling effects and costs are assumptions; this greedy ranking is not a validated cost-benefit model or an optimal budget solution.")

st.markdown("**Compare intervention options**")
option_summary = candidates.groupby("intervention", as_index=False).agg(
    illustrative_cost_inr=("cost", "first"),
    candidate_locations=("grid_id", "nunique"),
    mean_modeled_cooling_c=("cooling_reduction_c", "mean"),
    median_priority_score=("priority_score", "median"),
)
st.dataframe(option_summary, use_container_width=True, hide_index=True)

st.markdown("**Selected budget portfolio**")
if portfolio.empty:
    st.info("No intervention fits the selected budget.")
else:
    selected_intervention = st.selectbox("Show selected locations for", sorted(portfolio["intervention"].unique()))
    selected_rows = portfolio[portfolio["intervention"] == selected_intervention]
    display_columns = {
        "grid_id": "Grid cell",
        "priority_score": "Priority score",
        "cost": "Illustrative cost (INR)",
        "cooling_reduction_c": "Modeled cooling effect (C)",
        "population_benefited": "Potential population reached (estimate)" if mode == "Real remote sensing" and "population_count" in grid else "Exposure proxy potentially reached (not people)",
        "reason": "Reason",
    }
    st.dataframe(
        selected_rows[list(display_columns)].rename(columns=display_columns),
        use_container_width=True,
        hide_index=True,
    )
    spend_by_type = portfolio.groupby("intervention", as_index=False)["cost"].sum()
    spend_fig = px.bar(spend_by_type, x="intervention", y="cost", labels={"intervention": "Intervention", "cost": "Illustrative spend (INR)"})
    st.plotly_chart(spend_fig, use_container_width=True)
