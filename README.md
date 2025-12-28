# Analyst Track Abstract

### Introduction
This project turns match event and tracking data into clear, actionable insights through a lightweight analysis pipeline, designed for fast understanding and effective communication.

### Usecases
- Player profiling: highlight player contributions through a small set of well-defined KPIs.
- Coaching/scouting support: provide quick comparisons to identify strengths, weaknesses, and notable outliers.

### Potential Audience
- Performance analysts and coaching staff looking for fast, readable match insights.
- Scouts and recruitment analysts needing player-level KPI summaries.

---

## Video URL

Video: https://drive.google.com/file/d/1QQ223KgpuJVBT5qqYVCnZbMcrCgoVAmi/view?usp=sharing

---

## Run Instructions

#### Current project structure

The codebase is organized as a small package under `src/skillcorner_dash/`, with a thin `main.py` entry point that orchestrates the pipeline end-to-end. 

| Module | Role | Key elements |
|---|---|---|
| `src/skillcorner_dash/config.py` | Configuration constants | `BASE_URL`, `BASE_URL_LFS`, `COLORS` |
| `src/skillcorner_dash/data_loading.py` | Data loading (network I/O) | `load_match_files(match_id)` |
| `src/skillcorner_dash/dynamic_events_aggregator.py` | Core aggregation engine | `DynamicEventAggregator` |
| `src/skillcorner_dash/aggregation.py` | KPI aggregation logic | `aggregate_player_match(events_df)` (uses `DynamicEventAggregator`) |
| `src/skillcorner_dash/kpis.py` | KPI selection/formatting | `select_dashboard_kpis_v2(agg_df)` |
| `src/skillcorner_dash/report_html.py` | Report generation (Plotly + HTML) | `create_match_report_html_10tabs(...)` + helper functions |

`main.py` is responsible for selecting a `match_id`, calling the package functions, and exporting the final HTML report.

### 1) Create and activate a virtual environment
python -m venv .venv

Windows:
.venv\Scripts\activate

macOS / Linux:
source .venv/bin/activate

### 2) Install dependencies

pip install -r requirements.txt

### 3) Run the project
If the entry point is a Python script: python main.py. You can choose the match ID and the output path of the saved report.

### 4) Output
The project generates: an HTML report and/or analysis outputs saved locally.

