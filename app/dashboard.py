"""Streamlit dashboard for the local cooling planner MVP."""

from pathlib import Path

import plotly.express as px
import streamlit as st

from src.pipeline import run_pipeline


st.set_page_config(page_title="Urban Heat Island Cooling Planner", layout="wide")
st.title("Urban Heat Island Cooling Planner")
st.caption("Ahmedabad · Delhi · Kolkata · synthetic baseline pending public-data calibration")

grid_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "heat_risk_grid.csv"
recommendations_path = grid_path.parent / "intervention_recommendations.csv"
if not grid_path.exists() or not recommendations_path.exists():
    run_pipeline()

import pandas as pd

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
