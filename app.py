
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(layout="wide", page_title="KPI Dashboard", initial_sidebar_state="expanded")

PALETTE = px.colors.qualitative.Plotly

def parse_percent(series):
    # handle strings with % or numbers 0-1 or 0-100
    if series.dtype == 'O':
        series = series.str.replace('%','').str.strip()
    series = pd.to_numeric(series, errors='coerce')
    # infer scale
    median = series.median(skipna=True)
    if pd.isna(median):
        return series
    if median <= 1.05:  # assume 0-1
        return series * 100
    return series

def load_excel(uploaded_file, sheet_name=None):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    except Exception as e:
        st.error(f"Error reading Excel: {e}")
        return None
    return df

st.title("KPI Dashboard — Streamlit")
st.markdown("Upload an Excel file containing your KPI data. Then map the columns so the app knows which fields to use. The app will compute per-member and team KPIs with monthly line graphs and summary tables.")

with st.sidebar:
    st.header("Upload / Settings")
    uploaded = st.file_uploader("Upload Excel file (or leave empty to try default / example)", type=["xlsx","xls"], accept_multiple_files=False)
    sheet = st.text_input("Sheet name (leave empty for first sheet)", value="")
    st.markdown("**Column mapping** (select the column in your file that matches each KPI).")

    # Load sample or uploaded file to get columns
    sample_path = "KPI METRICS 2.xlsx"
    df_preview = None
    if uploaded is None:
        try:
            df_preview = pd.read_excel(sample_path, sheet_name=0)
            st.caption("Using uploaded project file from /mnt/data as default.")
        except Exception:
            df_preview = None
    else:
        df_preview = load_excel(uploaded, sheet_name=sheet if sheet else None)
    if df_preview is None:
        st.warning("No file available yet. Upload your Excel file to continue.")
        st.stop()
    columns = list(df_preview.columns)
    member_col = st.selectbox("Member / Assignee column", options=columns, index=0 if len(columns)>0 else None)
    date_col = st.selectbox("Date column (task date / completed date)", options=columns, index=1 if len(columns)>1 else None)
    task_col = st.selectbox("Task identifier column (optional)", options=[None]+columns, index=0)
    quality_col = st.selectbox("Quality Score column (e.g. 95 or 0.95 or '95%')", options=columns, index=columns.index("Quality Score") if "Quality Score" in columns else 2 if len(columns)>2 else 0)
    revision_col = st.selectbox("Revision Rate column (percentage)", options=columns, index=columns.index("Revision Rate") if "Revision Rate" in columns else 3 if len(columns)>3 else 0)
    completed_col = st.selectbox("Completed Task column (count or 1/0)", options=columns, index=columns.index("Completed") if "Completed" in columns else 0)
    ontime_col = st.selectbox("On-time delivery column (1/0 or %)", options=columns, index=columns.index("On-time") if "On-time" in columns else 0)
    efficiency_col = st.selectbox("Actual Work Efficiency column (percentage)", options=columns, index=columns.index("Efficiency") if "Efficiency" in columns else 0)
    manhours_col = st.selectbox("Man-hours Spent column (numeric)", options=columns, index=columns.index("Man-hours") if "Man-hours" in columns else 0)
    date_format_hint = st.text_input("If dates don't parse, provide format (e.g. %Y-%m-%d) or leave empty", value="")

# Read the actual dataframe using chosen uploaded or default file
df = load_excel(uploaded if uploaded is not None else "KPI METRICS 2.xlsx", sheet_name=sheet if sheet else None)
if df is None:
    st.stop()

# Basic preprocessing
if date_col not in df.columns:
    st.error(f"Date column '{date_col}' not found in file.")
    st.stop()

# Parse dates
try:
    if date_format_hint.strip():
        df['__date__'] = pd.to_datetime(df[date_col], format=date_format_hint, errors='coerce')
    else:
        df['__date__'] = pd.to_datetime(df[date_col], errors='coerce')
except Exception:
    df['__date__'] = pd.to_datetime(df[date_col], errors='coerce')

if df['__date__'].isna().all():
    st.error("Failed to parse any dates. Check your date column or provide a date format.")
    st.stop()

# Fill mapping missing columns gracefully
def get_series(col):
    return df[col] if (col and col in df.columns) else pd.Series([np.nan]*len(df))

member_s = get_series(member_col).astype(str)
task_s = get_series(task_col)
quality_s = parse_percent(get_series(quality_col))
revision_s = parse_percent(get_series(revision_col))
completed_s = pd.to_numeric(get_series(completed_col), errors='coerce')
ontime_s = parse_percent(get_series(ontime_col))
eff_s = parse_percent(get_series(efficiency_col))
mh_s = pd.to_numeric(get_series(manhours_col), errors='coerce')

# create working df
work = pd.DataFrame({
    "member": member_s,
    "date": df['__date__'],
    "task": task_s,
    "quality": quality_s,
    "revision": revision_s,
    "completed": completed_s,
    "ontime": ontime_s,
    "efficiency": eff_s,
    "manhours": mh_s
})

work['month'] = work['date'].dt.to_period('M').dt.to_timestamp()

# Aggregate per task row: if completed is NaN but exists as tasks, infer completed=1
work['completed'] = work['completed'].fillna(1)
work['ontime_flag'] = np.where(work['ontime']>=0, work['ontime']/100.0, np.nan)  # store as fraction for averaging; NaN if not provided

# Per-member monthly aggregates
per_member_month = work.groupby(['member','month']).agg(
    avg_quality = ('quality', 'mean'),
    avg_revision = ('revision', 'mean'),
    total_completed = ('completed', 'sum'),
    ontime_pct = ('ontime_flag', 'mean'),
    avg_efficiency = ('efficiency', 'mean'),
    total_manhours = ('manhours', 'sum')
).reset_index()

# Team (all members averaged) monthly aggregates — average the member averages per month
team_month = per_member_month.groupby('month').agg(
    avg_quality = ('avg_quality','mean'),
    avg_revision = ('avg_revision','mean'),
    total_completed = ('total_completed','sum'),
    ontime_pct = ('ontime_pct','mean'),
    avg_efficiency = ('avg_efficiency','mean'),
    total_manhours = ('total_manhours','sum')
).reset_index()

# Monthly Average table (team)
st.header("Team — Monthly Averages")
st.dataframe(team_month.style.format({
    'avg_quality': '{:.2f}%',
    'avg_revision': '{:.2f}%',
    'ontime_pct': '{:.2f}%',
    'avg_efficiency': '{:.2f}%',
    'total_completed': '{:.0f}',
    'total_manhours': '{:.1f}'
}))

# Controls for visualization
st.sidebar.header("Charts / Filters")
members = sorted(per_member_month['member'].dropna().unique().tolist())
selected_members = st.sidebar.multiselect("Select members to show (leave empty = show all)", options=members, default=members[:3])
show_team = st.sidebar.checkbox("Show Team average", value=True)
date_range = st.sidebar.date_input("Date range (month-wise)", [work['month'].min(), work['month'].max()])

# Filter data
start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
pm_filtered = per_member_month[(per_member_month['month']>=start) & (per_member_month['month']<=end)]
team_filtered = team_month[(team_month['month']>=start) & (team_month['month']<=end)]

if selected_members:
    pm_filtered = pm_filtered[pm_filtered['member'].isin(selected_members)]

# Helper to draw line charts
def line_chart(df_plot, y, title, y_label, percentage=True):
    fig = px.line(df_plot, x='month', y=y, color='member' if 'member' in df_plot.columns else None,
                 markers=True)
    fig.update_layout(title=title, xaxis_title="Month", yaxis_title=y_label, template='plotly_white')
    if percentage:
        fig.update_yaxes(tickformat=".2f")
    return fig

st.header("Per-member KPI Trends (Line charts)")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Average Quality Score (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        # add team as a synthetic member
        team_temp = team_filtered[['month','avg_quality']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        team_temp = team_temp.rename(columns={'avg_quality':'avg_quality'})
        plot_df = pd.concat([plot_df.rename(columns={'avg_quality':'avg_quality'})[['member','month','avg_quality']], team_temp[['member','month','avg_quality']]])
    fig = px.line(plot_df, x='month', y='avg_quality', color='member', markers=True)
    fig.update_layout(yaxis_title='Avg Quality (%)', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Average Revision Rate (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        team_temp = team_filtered[['month','avg_revision']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        plot_df = pd.concat([plot_df.rename(columns={'avg_revision':'avg_revision'})[['member','month','avg_revision']], team_temp[['member','month','avg_revision']]])
    fig = px.line(plot_df, x='month', y='avg_revision', color='member', markers=True)
    fig.update_layout(yaxis_title='Avg Revision (%)', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Total Completed Task (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        team_temp = team_filtered[['month','total_completed']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        plot_df = pd.concat([plot_df[['member','month','total_completed']], team_temp[['member','month','total_completed']]])
    fig = px.line(plot_df, x='month', y='total_completed', color='member', markers=True)
    fig.update_layout(yaxis_title='Total Completed', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("On-time delivery (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        team_temp = team_filtered[['month','ontime_pct']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        plot_df = pd.concat([plot_df.rename(columns={'ontime_pct':'ontime_pct'})[['member','month','ontime_pct']], team_temp[['member','month','ontime_pct']]])
    fig = px.line(plot_df, x='month', y='ontime_pct', color='member', markers=True)
    fig.update_layout(yaxis_title='On-time (fraction)', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

st.header("Other KPIs")
col3, col4 = st.columns(2)
with col3:
    st.subheader("Actual Work Efficiency (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        team_temp = team_filtered[['month','avg_efficiency']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        plot_df = pd.concat([plot_df.rename(columns={'avg_efficiency':'avg_efficiency'})[['member','month','avg_efficiency']], team_temp[['member','month','avg_efficiency']]])
    fig = px.line(plot_df, x='month', y='avg_efficiency', color='member', markers=True)
    fig.update_layout(yaxis_title='Avg Efficiency (%)', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("Man-hours Spent (per member)")
    plot_df = pm_filtered.copy()
    if show_team:
        team_temp = team_filtered[['month','total_manhours']].copy()
        team_temp['member'] = 'TEAM AVERAGE'
        plot_df = pd.concat([plot_df[['member','month','total_manhours']], team_temp[['member','month','total_manhours']]])
    fig = px.line(plot_df, x='month', y='total_manhours', color='member', markers=True)
    fig.update_layout(yaxis_title='Total Man-hours', xaxis_title='Month', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

# Per-member-per-task average
st.header("Per-member-per-task average (summary)")
if task_col and task_col in df.columns:
    per_member_task = work.groupby(['member','task']).agg(
        avg_quality = ('quality','mean'),
        avg_revision = ('revision','mean'),
        total_completed = ('completed','sum'),
        ontime_pct = ('ontime_flag','mean'),
        avg_efficiency = ('efficiency','mean'),
        total_manhours = ('manhours','sum'),
        observations = ('date','count')
    ).reset_index()
    st.dataframe(per_member_task.style.format({
        'avg_quality':'{:.2f}%',
        'avg_revision':'{:.2f}%',
        'ontime_pct':'{:.2f}',
        'avg_efficiency':'{:.2f}%',
        'total_manhours':'{:.1f}'
    }))
else:
    st.info("No task column mapped — per-member-per-task averages require a task identifier column.")

st.markdown("---")
st.caption("Tips: If percentage columns show very small numbers (e.g. 0.95), they were interpreted as fractions and scaled to percentages automatically. Adjust column mapping if results seem off.")
