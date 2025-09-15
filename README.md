
# KPI Dashboard (Streamlit)

A user-friendly KPI dashboard built with Streamlit and Plotly. Upload your Excel file and map columns to visualize both per-member and team KPI trends with monthly averages.

## Features
- Upload Excel (.xlsx / .xls)
- Map columns in your file to the expected KPI fields using a simple sidebar
- Per-member monthly line charts for:
  - Average Quality Score (%)
  - Average Revision Rate (%)
  - Total Completed Task
  - On-time delivery (%)
  - Actual Work Efficiency (%)
  - Man-hours Spent (total)
- Team (all members averaged) monthly metrics
- Monthly average table and per-member-per-task average table (if Task column provided)
- Automatically handles percentages in formats like `95`, `0.95`, or `95%`

## How to run
1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run Streamlit:
```
streamlit run /mnt/data/app.py
```

3. In the app:
- Upload your Excel file or use the bundled `KPI METRICS 2.xlsx` placed in `/mnt/data`.
- Select the sheet (optional) and map your columns in the sidebar.
- Use filters to choose members and date range.

## Expected columns (but app is flexible)
- A date column (task date / completed date)
- A member/assignee column
- Quality score (number or percent)
- Revision rate (number or percent)
- Completed tasks (count, or blank = inferred 1 per row)
- On-time delivery (1/0 or percent)
- Actual efficiency (number or percent)
- Man-hours (numeric)
- Task identifier (optional; required for per-member-per-task summary)

## Files created
- `app.py` — Streamlit application (in `/mnt/data`)
- `README.md` — This file
- `requirements.txt` — Python dependencies

## Notes & Tips
- If your dates don't parse, provide an explicit date format in the sidebar (e.g. `%Y-%m-%d`).
- If percentages look too small, the app automatically scales 0-1 to 0-100.
- The app treats missing "completed" values as 1 (one completed task per row) by default — change your data if you use different semantics.

Enjoy — feel free to ask for customizations (custom color palette, export functions, PDF/PowerPoint export, or KPI formula changes).
