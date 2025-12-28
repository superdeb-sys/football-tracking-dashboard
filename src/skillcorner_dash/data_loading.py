# -*- coding: utf-8 -*-
"""Load SkillCorner match data from GitHub and extract match context.

This module provides utilities to fetch match-level files (events, phases,
tracking, metadata) and to standardize a small context dictionary.
"""
import pandas as pd
import json

def load_match_files(BASE_URL, BASE_URL_LFS, match_id: int):
    """
    Load match files for a given match id from GitHub.

    Args:
        base_url: Base URL for standard files (CSV/JSON).
        base_url_lfs: Base URL for Git LFS hosted files (JSONL).
        match_id: SkillCorner match identifier.

    Returns:
        A tuple of:
            - events_df: Dynamic events (CSV).
            - phases_df: Phases of play (CSV).
            - tracking_df: Tracking data normalized to one row per player per frame.
            - match_meta: Match metadata (dict).

    Raises:
        ValueError: If the tracking JSONL cannot be normalized as expected.
    """
    # Dynamic events (CSV)
    events_url = f"{BASE_URL}/{match_id}/{match_id}_dynamic_events.csv"
    events_df = pd.read_csv(events_url)

    # Phases of play (CSV)
    phases_url = f"{BASE_URL}/{match_id}/{match_id}_phases_of_play.csv"
    phases_df = pd.read_csv(phases_url)

    # Match metadata (JSON)
    match_meta_url = f"{BASE_URL}/{match_id}/{match_id}_match.json"
    match_meta = json.loads(pd.read_json(match_meta_url, typ="series").to_json())

    # Tracking (JSONL via Git LFS)
    tracking_url = f"{BASE_URL_LFS}/{match_id}/{match_id}_tracking_extrapolated.jsonl"
    tracking_raw = pd.read_json(tracking_url, lines=True)

    tracking_df = pd.json_normalize(
        tracking_raw.to_dict("records"),
        record_path="player_data",
        meta=["frame", "timestamp", "period", "possession", "ball_data"],
    )
    tracking_df["match_id"] = match_id

    return events_df, phases_df, tracking_df, match_meta


def get_match_context(match_meta: dict) -> dict:
    """Extract a minimal match context from match metadata.

    Args:
        match_meta: Match metadata dictionary.
    
    Returns:
        A dictionary with match id, teams, competition, season, round, and UTC date.
    """
    match_id = match_meta["id"]
    home_team = match_meta["home_team"]["name"]
    away_team = match_meta["away_team"]["name"]

    comp = match_meta["competition_edition"]["competition"]["name"]
    season = match_meta["competition_edition"]["season"]["name"]
    round_name = match_meta["competition_round"]["name"]
    date_time_utc = match_meta["date_time"]

    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "competition": comp,
        "season": season,
        "round_name": round_name,
        "date_time_utc": date_time_utc,
    }