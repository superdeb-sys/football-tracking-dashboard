# -*- coding: utf-8 -*-
"""
"""

from src.skillcorner_dash.data_loading import load_match_files
from src.skillcorner_dash.config import BASE_URL
from src.skillcorner_dash.config import BASE_URL_LFS
from src.skillcorner_dash.aggregation import aggregate_player_match
from src.skillcorner_dash.kpis import select_dashboard_kpis_v2
from src.skillcorner_dash.report_html import create_match_report_html_10tabs


def main():
    match_id = 1886347
    events_df, phases_df, tracking_df, match_meta = load_match_files(BASE_URL, BASE_URL_LFS,match_id)
    agg_df = aggregate_player_match(events_df)
    dashboard_df = select_dashboard_kpis_v2(agg_df)
    create_match_report_html_10tabs(dashboard_df, match_id, match_meta, output_file="football_match_report.html")

if __name__ == "__main__":
    main()
