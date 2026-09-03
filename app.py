import os

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "snow_crab")

st.set_page_config(page_title="Alaskan Snow Crab Catch Explorer", layout="wide")

sns.set_theme(style="whitegrid")


@st.cache_data
def load_data(table: str) -> pd.DataFrame:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    rows = []
    page_size = 1000
    start = 0
    while True:
        response = (
            client.table(table)
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = response.data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size

    return pd.DataFrame(rows)


df = load_data(SUPABASE_TABLE)

st.title("Alaskan Snow Crab Catch Data")
st.caption(f"Live data from Supabase table `{SUPABASE_TABLE}`: locations, temperatures, depths, and sex ratios.")

if df.empty:
    st.warning(f"No rows returned from the `{SUPABASE_TABLE}` table.")
    st.stop()

has_year = "year" in df.columns
has_sex = "sex" in df.columns
has_latlon = {"latitude", "longitude"}.issubset(df.columns)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

filtered = df.copy()

if has_year:
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    year_range = st.sidebar.slider(
        "Year range",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
    )
    filtered = filtered[(filtered["year"] >= year_range[0]) & (filtered["year"] <= year_range[1])]

if has_sex:
    sex_options = sorted(df["sex"].dropna().unique().tolist())
    selected_sexes = st.sidebar.multiselect("Sex", options=sex_options, default=sex_options)
    filtered = filtered[filtered["sex"].isin(selected_sexes)]

st.sidebar.markdown(f"**{len(filtered):,}** of {len(df):,} records match the current filters.")

# ---------------------------------------------------------------------------
# 1. Basic info
# ---------------------------------------------------------------------------
st.header("1. Dataset Overview")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Shape")
    st.write(f"Rows: {df.shape[0]:,} | Columns: {df.shape[1]}")

    st.subheader("Data types")
    st.dataframe(df.dtypes.astype(str).rename("dtype"))

with col2:
    st.subheader("Missing values")
    missing = df.isna().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({"missing_count": missing, "missing_pct": missing_pct})
    st.dataframe(missing_df)

st.subheader("Summary statistics")
st.dataframe(df.describe(include="all").transpose())

# ---------------------------------------------------------------------------
# 2. Map of catch locations
# ---------------------------------------------------------------------------
if has_latlon:
    st.header("2. Catch Locations Map")

    color_options = [c for c in ["sex", "year"] if c in df.columns]
    color_by = st.radio("Color points by", options=color_options, horizontal=True) if color_options else None

    map_df = filtered.dropna(subset=["latitude", "longitude"])
    hover_cols = [c for c in ["name", "sex", "year", "bottom_depth", "bottom_temperature"] if c in df.columns]

    fig_map = px.scatter_mapbox(
        map_df,
        lat="latitude",
        lon="longitude",
        color=color_by,
        hover_data=hover_cols,
        zoom=3,
        height=550,
        opacity=0.6,
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_map, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Trends over time
# ---------------------------------------------------------------------------
if has_year:
    st.header("3. Trends by Year")

    metric_options = ["Catch count"]
    if "bottom_temperature" in df.columns:
        metric_options.append("Average bottom temperature")

    metric = st.radio("Metric", options=metric_options, horizontal=True)

    if metric == "Catch count":
        yearly = filtered.groupby("year").size().reset_index(name="catch_count")
        fig_line = px.line(yearly, x="year", y="catch_count", markers=True)
        fig_line.update_layout(yaxis_title="Catch count")
    else:
        yearly = filtered.groupby("year")["bottom_temperature"].mean().reset_index()
        fig_line = px.line(yearly, x="year", y="bottom_temperature", markers=True)
        fig_line.update_layout(yaxis_title="Avg bottom temperature (°C)")

    st.plotly_chart(fig_line, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Distributions
# ---------------------------------------------------------------------------
numeric_cols = [c for c in ["bottom_depth", "bottom_temperature", "surface_temperature", "cpue"] if c in df.columns]

if numeric_cols:
    st.header("4. Distributions")

    hist_cols = st.columns(min(2, len(numeric_cols)))

    for i, col_name in enumerate(numeric_cols[:2]):
        with hist_cols[i]:
            st.subheader(col_name.replace("_", " ").title())
            fig, ax = plt.subplots()
            sns.histplot(
                filtered[col_name].dropna(),
                bins=30,
                kde=True,
                ax=ax,
                color=["steelblue", "indianred"][i],
            )
            ax.set_xlabel(col_name.replace("_", " ").title())
            st.pyplot(fig)

# ---------------------------------------------------------------------------
# 5. Sex ratio
# ---------------------------------------------------------------------------
if has_sex:
    st.header("5. Sex Ratio")

    sex_counts = filtered["sex"].value_counts().reset_index()
    sex_counts.columns = ["sex", "count"]

    chart_type = st.radio("Chart type", options=["Pie", "Bar"], horizontal=True)

    if chart_type == "Pie":
        fig_sex = px.pie(sex_counts, names="sex", values="count")
    else:
        fig_sex = px.bar(sex_counts, x="sex", y="count", color="sex")

    st.plotly_chart(fig_sex, use_container_width=True)

# ---------------------------------------------------------------------------
# Raw data
# ---------------------------------------------------------------------------
with st.expander("View filtered raw data"):
    st.dataframe(filtered)
