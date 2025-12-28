# -*- coding: utf-8 -*-
"""KPI selection utilities.

This module selects a stable subset of KPI columns from an aggregated dataframe,
keeping only columns that actually exist to avoid KeyError.
"""


def select_dashboard_kpis_v2(agg_df):
    """
    Dashboard DF (player-match) avec beaucoup de KPIs, mais sans KeyError:
    on ne garde que les colonnes qui existent dans agg_df.
    """
    base_cols = ['match_id', 'team_id', 'team_shortname', 'player_id', 'player_name']

    kpi_columns = [
        # --- OFF-BALL RUNS (volume / danger / intensity / phases)
        'count_off_ball_runs',
        'count_targeted_off_ball_runs', 'count_received_off_ball_runs',
        'xthreat_off_ball_runs',
        'xthreat_off_ball_runs_in_build_up', 'xthreat_off_ball_runs_in_create', 'xthreat_off_ball_runs_in_finish',
        'count_dangerous_off_ball_runs',
        'count_difficult_off_ball_runs',
        'count_hsr_off_ball_runs', 'count_sprint_off_ball_runs',
        'avg_distance_covered_off_ball_runs', 'avg_speed_avg_off_ball_runs',
        'count_off_ball_runs_in_build_up', 'count_off_ball_runs_in_create', 'count_off_ball_runs_in_finish',

        # --- DEPTH / SUPPORT RUNS
        'xthreat_runs_in_behind', 'xthreat_runs_in_behind_in_finish',
        'xthreat_runs_ahead_of_the_ball', 'xthreat_runs_ahead_of_the_ball_in_finish',

        # --- PRESSING BASIC
        'count_pressing_x', 'count_pressing_y',
        'count_pressing_chain_on_ball_engagements', 'count_pressing_chain_pressing',
        'count_got_goal_side_pressing_x', 'count_got_close_pressing_x',
        'avg_speed_difference_pressing_x',

        # --- PRESSING OUTCOMES (DANGER)
        'count_possession_danger_pressing',
        'count_stop_possession_danger_pressing_x', 'count_stop_possession_danger_pressing_y',
        'count_reduce_possession_danger_pressing_x', 'count_reduce_possession_danger_pressing_y',

        # --- PRESSING FAILURES
        'count_beaten_by_possession_pressing_x', 'count_beaten_by_possession_pressing_y',
        'count_affected_line_break_pressing_x', 'count_affected_line_break_pressing_y',

        # --- PRESSING BY BLOCK
        'count_beaten_by_possession_pressing_in_high_block',
        'count_stop_possession_danger_pressing_in_high_block',
        'count_reduce_possession_danger_pressing_in_high_block',
        'count_affected_line_break_pressing_in_high_block',

        'count_beaten_by_possession_pressing_in_medium_block',
        'count_stop_possession_danger_pressing_in_medium_block',
        'count_reduce_possession_danger_pressing_in_medium_block',
        'count_affected_line_break_pressing_in_medium_block',

        'count_beaten_by_possession_isolated_pressing',
        'count_stop_possession_danger_isolated_pressing',
        'count_reduce_possession_danger_isolated_pressing',
        'count_affected_line_break_isolated_pressing',

        # --- ON-BALL ENGAGEMENTS (non-pressing) danger control
        'count_possession_danger_on_ball_engagements',
        'count_stop_possession_danger_on_ball_engagements_x',
        'count_reduce_possession_danger_on_ball_engagements_x',
        'count_beaten_by_possession_on_ball_engagements_x',
        'count_affected_line_break_on_ball_engagements_x',
        'count_pressing_chain_on_ball_engagements',

        # --- LINE BREAKING PASSES (noms variables -> on met plusieurs candidats)
        # (si ton agrégateur sort d'autres noms, ils seront juste ignorés)
        'xthreat_line_breaking_passes', 'count_line_breaking_passes',
        'count_pass_attempts_line_breaking_passes', 'count_completed_passes_line_breaking_passes'
    ]

    # Colonnes effectivement dispo
    available = [c for c in (base_cols + kpi_columns) if c in agg_df.columns]
    dashboard_df = agg_df[available].copy()

    return dashboard_df
