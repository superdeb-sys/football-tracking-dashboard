# -*- coding: utf-8 -*-
"""
Aggregate SkillCorner dynamic events at player-match level.

This module builds a single player-match table by running multiple aggregate
groups (off-ball runs, line-breaking passes, defensive engagements, pressing)
and outer-merging the results.
"""

import pandas as pd
from src.skillcorner_dash.DynamicEventsAggregator import DynamicEventAggregator
from src.skillcorner_dash.config import GROUP_COLS

def aggregate_player_match(events_df):
    """Aggregate multiple KPI groups for each player in a match.

    Args:
        events_df: Dynamic events dataframe for a single match.
    
    Returns:
        A dataframe indexed by player-match identifiers (GROUP_COLS), containing
        all aggregated KPIs merged with an outer join.
    """

    # group_by per player-match
    group_cols = GROUP_COLS
    agg = DynamicEventAggregator(df=events_df)

    # Off-ball runs
    obr = agg.generate_aggregates(group_by=group_cols, aggregate_type="off_ball_runs")

    # Line-breaking passes
    lbp = agg.generate_aggregates(group_by=group_cols, aggregate_type="line_breaking_passes")

    # Defensive engagements
    obe = agg.generate_aggregates(group_by=group_cols, aggregate_type="on_ball_engagements")

    # Pressing
    press = agg.generate_aggregates(group_by=group_cols, aggregate_type="pressing_engagements")

    # Merge all
    out = (
        obr.merge(lbp, on=group_cols, how="outer")
           .merge(obe, on=group_cols, how="outer")
           .merge(press, on=group_cols, how="outer")
    )

    return out