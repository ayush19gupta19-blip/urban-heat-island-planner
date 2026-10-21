"""Streamlit dashboard for the local cooling planner MVP."""

from pathlib import Path

import plotly.express as px
import streamlit as st

from src.pipeline import run_pipeline


st.set_page_config(page_title="Urban Heat Island Cooling Planner", layout="wide")
st.title("Urban Heat Island Cooling Planner")
st.caption("Ahmedabad · Delhi · Kolkata · decision-support prototype")

processed_dir = Path(__file__).resolve().parents[1] / "data" / "processed"
synthetic_grid_path = processed_dir / "heat_risk_grid.csv"
synthetic_recommendations_path = processed_dir / "intervention_recommendations.csv"
real_grid_path = processed_dir / "heat_risk_grid_real.csv"
real_recommendations_path = processed_dir / "intervention_recommendations_real.csv"
if not synthetic_grid_path.exists() or not synthetic_recommendations_path.exists():
    run_pipeline()

import pandas as pd

mode = st.sidebar.selectbox("Data mode", ["Synthetic demo", "Real remote sensing"] if real_grid_path.exists() else ["Synthetic demo"])
if mode == "Real remote sensing":
    grid_path, recommendations_path = real_grid_path, real_recommendations_path
    st.sidebar.success("Using NASA POWER, Landsat, and Sentinel-2 features")
else:
    grid_path, recommendations_path = synthetic_grid_path, synthetic_recommendations_path
    st.sidebar.info("Run `python -m src.pipeline --mode real` to build real-data outputs")

grid = pd.read_csv(grid_path)
recommendations = pd.read_csv(recommendations_path)

city = st.selectbox("City", sorted(grid["city"].unique()))
grid = grid[grid["city"] == city].copy()
recommendations = recommendations[recommendations["city"] == city].copy()

left, middle, right = st.columns(3)
left.metric("Grid cells", f"{len(grid):,}")
middle.metric("High/Critical cells", f"{(grid['heat_risk_score'] >= 60).sum():,}")
right.metric("Population exposed", f"{grid.loc[grid['heat_risk_score'] >= 60, 'population_density'].sum():,.0f}")

st.subheader("Heat-risk map")
fig = px.scatter_mapbox(
    grid,
    lat="latitude",
    lon="longitude",
    color="heat_risk_score",
    hover_name="grid_id",
    hover_data=["risk_category", "land_surface_temp_c", "vegetation_index", "population_density"],
    color_continuous_scale="RdYlBu_r",
    zoom=10,
    height=560,
)
fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Recommended cooling interventions")
intervention = st.selectbox("Intervention", sorted(recommendations["intervention"].unique()))
view = recommendations[recommendations["intervention"] == intervention].head(10)
st.dataframe(view[["grid_id", "priority_score", "cost", "cooling_reduction_c", "population_benefited", "reason"]], use_container_width=True)
