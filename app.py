import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="KPI Dashboard", initial_sidebar_state="expanded")

PALETTE = px.colors.qualitative.Plotly

def parse_percent(series):
    if series.dtype == 'O':
        series = series.str.replace('%','').str.strip()
    series = pd.to_numeric(series, errors='coerce')
    median = series.median(skipna=True)
    if pd.isna(median):
        return series
    if median <= 1.05:  # assume 0-1 scale
        return series * 100
    return series

def load_excel(uploaded_file, sheet_name=None):
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
        # auto-clean headers: find first row with at least 2 non-null values
        header_row = df.notna().sum(axis=1).idxmax()
        df.columns = df.iloc[header_row]
        df = df.drop(index=list(range(0, header_row+1)))
        df = df.reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error reading Excel: {e}")
        return None

st.title("KPI Dashboard — Streamlit")
st.markdown("Upload an Excel file containing your KPI data. Then map the columns so the app knows which fields to use.")

with st.sidebar:
    st.header("Upload / Settings")
    uploaded = st.file_uploader("Upload Excel file", type=["xlsx","xls"])
    sheet = st.text_input("Sheet name (leave empty for first sheet)", value="")

    if uploaded:
        try:
            xls = pd.ExcelFile(uploaded)
            sheet_names = xls.sheet_names
            if not sheet:
                sheet = sheet_names[0]
            st.write("Available sheets:", sheet_names)
            df_preview = load_excel(uploaded, sheet_name=sheet)
        except Exception as e:
            st.error(f"Could not read uploaded Excel: {e}")
            st.stop()
    else:
        st.warning("Please upload an Excel file to continue.")
        st.stop()

if df_preview is None or df_preview.empty:
    st.error("No data found in the selected sheet. Please check your Excel format.")
    st.stop()

columns = list(df_preview.columns)

# Column mapping
member_col = st.sidebar.selectbox("Member / Assignee column", options=columns)
date_col = st.sidebar.selectbox("Date column", options=columns)
task_col = st.sidebar.selectbox("Task identifier column (optional)", options=[None]+columns)
quality_col = st.sidebar.selectbox("Quality Score column", options=columns)
revision_col = st.sidebar.selectbox("Revision Rate column", options=columns)
completed_col = st.sidebar.selectbox("Completed Task column", options=columns)
ontime_col = st.sidebar.selectbox("On-time delivery column", options=columns)
efficiency_col = st.sidebar.selectbox("Work Efficiency column", options=columns)
manhours_col = st.sidebar.selectbox("Man-hours Spent column", options=columns)
date_format_hint = st.sidebar.text_input("Date format (optional)", value="")

# Parse dates
def parse_dates(series, hint=""):
    s = series.astype(str).str.strip()
    # if values look like YYYYMMDD (8 digits), parse that
    if s.str.match(r"^\d{8}$").all():
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    if hint.strip():
        return pd.to_datetime(s, format=hint, errors="coerce")
    return pd.to_datetime(s, errors="coerce")

df_preview['__date__'] = parse_dates(df_preview[date_col], hint=date_format_hint)

if df_preview['__date__'].isna().all():
    st.error("Failed to parse any dates. Please check your date format or column selection.")
    st.stop()

# Build clean working DataFrame
work = pd.DataFrame({
    "member": df_preview[member_col].astype(str),
    "date": df_preview['__date__'],
    "task": df_preview[task_col] if task_col else None,
    "quality": parse_percent(df_preview[quality_col]),
    "revision": parse_percent(df_preview[revision_col]),
    "completed": pd.to_numeric(df_preview[completed_col], errors='coerce'),
    "ontime": parse_percent(df_preview[ontime_col]),
    "efficiency": parse_percent(df_preview[efficiency_col]),
    "manhours": pd.to_numeric(df_preview[manhours_col], errors='coerce')
})

work['month'] = work['date'].dt.to_period('M').dt.to_timestamp()
work['completed'] = work['completed'].fillna(1)
work['ontime_flag'] = np.where(work['ontime']>=0, work['ontime']/100.0, np.nan)

# Per-member monthly aggregates
per_member_month = work.groupby(['member','month']).agg(
    avg_quality=('quality','mean'),
    avg_revision=('revision','mean'),
    total_completed=('completed','sum'),
    ontime_pct=('ontime_flag','mean'),
    avg_efficiency=('efficiency','mean'),
    total_manhours=('manhours','sum')
).reset_index()

# Team monthly aggregates
team_month = per_member_month.groupby('month').agg(
    avg_quality=('avg_quality','mean'),
    avg_revision=('avg_revision','mean'),
    total_completed=('total_completed','sum'),
    ontime_pct=('ontime_pct','mean'),
    avg_efficiency=('avg_efficiency','mean'),
    total_manhours=('total_manhours','sum')
).reset_index()

# Display
st.header("Team — Monthly Averages")
st.dataframe(team_month.style.format({
    'avg_quality': '{:.2f}%',
    'avg_revision': '{:.2f}%',
    'ontime_pct': '{:.2f}%',
    'avg_efficiency': '{:.2f}%',
    'total_completed': '{:.0f}',
    'total_manhours': '{:.1f}'
}))

# Chart filters
st.sidebar.header("Charts / Filters")
members = sorted(per_member_month['member'].dropna().unique().tolist())
selected_members = st.sidebar.multiselect("Select members", options=members, default=members[:3])
show_team = st.sidebar.checkbox("Show Team average", value=True)
date_range = st.sidebar.date_input("Date range", [work['month'].min(), work['month'].max()])

# (the rest of your chart plotting code stays the same as before)
