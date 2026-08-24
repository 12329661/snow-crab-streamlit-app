import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Alaskan Snow Crab Catch Explorer", layout="wide")

sns.set_theme(style="whitegrid")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


df = load_data("mfsnowcrab.csv")

st.title("Alaskan Snow Crab Catch Data (1975-2018)")
st.caption("Explore survey catch records: locations, temperatures, depths, and sex ratios.")

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider(
    "Year range",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
)

sex_options = sorted(df["sex"].dropna().unique().tolist())
selected_sexes = st.sidebar.multiselect("Sex", options=sex_options, default=sex_options)

filtered = df[
    (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
    & (df["sex"].isin(selected_sexes))
]

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
st.header("2. Catch Locations Map")

color_by = st.radio("Color points by", options=["sex", "year"], horizontal=True)

map_df = filtered.dropna(subset=["latitude", "longitude"])

fig_map = px.scatter_mapbox(
    map_df,
    lat="latitude",
    lon="longitude",
    color=color_by,
    hover_data=["name", "sex", "year", "bottom_depth", "bottom_temperature"],
    zoom=3,
    height=550,
    opacity=0.6,
)
fig_map.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig_map, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Line chart by year
# ---------------------------------------------------------------------------
st.header("3. Trends by Year")

metric = st.radio(
    "Metric",
    options=["Catch count", "Average bottom temperature"],
    horizontal=True,
)

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
# 4. Histograms
# ---------------------------------------------------------------------------
st.header("4. Distributions")

hist_col1, hist_col2 = st.columns(2)

with hist_col1:
    st.subheader("Bottom depth")
    fig, ax = plt.subplots()
    sns.histplot(filtered["bottom_depth"].dropna(), bins=30, kde=True, ax=ax, color="steelblue")
    ax.set_xlabel("Bottom depth")
    st.pyplot(fig)

with hist_col2:
    st.subheader("Bottom temperature")
    fig, ax = plt.subplots()
    sns.histplot(filtered["bottom_temperature"].dropna(), bins=30, kde=True, ax=ax, color="indianred")
    ax.set_xlabel("Bottom temperature (°C)")
    st.pyplot(fig)

# ---------------------------------------------------------------------------
# 5. Sex ratio
# ---------------------------------------------------------------------------
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
