# -*- coding: utf-8 -*-
"""Project configuration constants.

Centralizes remote endpoints (SkillCorner open data) and shared colors used by
the dashboard/report.
"""

BASE_URL = "https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches"
BASE_URL_LFS = "https://media.githubusercontent.com/media/SkillCorner/opendata/master/data/matches"

GROUP_COLS = ["match_id", "team_id", "team_shortname", "player_id", "player_name"]

COLORS = {
    "runs": "#3498DB",        # off-ball / running
    "xthreat": "#D62728",     # danger / xThreat
    "pressing": "#E67E22",    # pressing
    "success": "#2ECC71",     # réussite / stop
    "neutral": "#95A5A6"
}