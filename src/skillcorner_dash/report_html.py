# -*- coding: utf-8 -*-
"""
HTML match report generation (Plotly).

This module builds an offline HTML report for a single match, with multiple tabs
and a Team/Opponent toggle.
"""
import json
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.skillcorner_dash.config import COLORS
from src.skillcorner_dash.data_loading import get_match_context

def create_match_report_html_10tabs(dashboard_df, match_id, match_meta, output_file="football_match_report.html"):
    """Create an offline HTML report for one match.

    Args:
        dashboard_df: Player-match KPI table.
        match_id: Match identifier to filter dashboard_df.
        match_meta: Match metadata dictionary (home/away names, competition, etc.).
        output_path: Target HTML path.

    Returns:
        The resolved output path.

    Raises:
        ValueError: If match_id is missing from dashboard_df.
    """

    # -------------------------
    # Data helpers
    # -------------------------
    def pick_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def ensure_cols(df, cols, fill=0):
        df = df.copy()
        for c in cols:
            if c not in df.columns:
                df[c] = fill
        return df

    def safe_ratio(num_s, den_s):
        den = den_s.replace(0, np.nan)
        out = (num_s / den).replace([np.inf, -np.inf], np.nan).fillna(0)
        return out

    #def split_team_opp(match_df):
        #team_ids = match_df['team_id'].dropna().unique()
        #if len(team_ids) != 2:
            #raise ValueError(f"Expected 2 teams for match {match_id}, got {len(team_ids)}: {team_ids}")
        #team_id, opp_id = team_ids[0], team_ids[1]
        #return (
            #match_df[match_df['team_id'] == team_id].copy(),
            #match_df[match_df['team_id'] == opp_id].copy()
        #)
        
    def split_team_opp(match_df, team_id, opp_id):
        return (
            match_df[match_df["team_id"] == team_id].copy(),
            match_df[match_df["team_id"] == opp_id].copy()
        )


    # -------------------------
    # Plot helpers
    # -------------------------
    def style_fig(fig, title, height=750, showlegend=False):
        fig.update_layout(
            template="plotly_white",
            title=title,
            height=height,
            autosize=True,
            showlegend=showlegend,
            margin=dict(l=40, r=20, t=65, b=40),
            font=dict(size=13)
        )
        fig.update_xaxes(showgrid=True, gridcolor="#E6E6E6", zeroline=False)
        fig.update_yaxes(showgrid=False, automargin=True)
        return fig

    def empty_annotation(fig, row, col, text="No data"):
        fig.add_annotation(
            text=text,
            xref=f"x{'' if (row, col) == (1, 1) else fig._grid_ref[row-1][col-1][0][1:]}",
            yref=f"y{'' if (row, col) == (1, 1) else fig._grid_ref[row-1][col-1][1][1:]}",
            x=0.5, y=0.5, showarrow=False, font=dict(color="#7f7f7f", size=14)
        )

    def add_trace_with_side(fig, trace, side):
        # side: 'team', 'opp', or 'both'
        trace.meta = {"side": side}
        fig.add_trace(trace)

    def add_topN_bar(fig, df, metric, n=10, color="#1F77B4", name="Team", side="team",
                     row=1, col=1, x_title=None, showlegend=None):
        if metric not in df.columns:
            empty_annotation(fig, row, col, f"Missing: {metric}")
            return
        top = df.nlargest(n, metric)
        tr = go.Bar(
            y=top['player_name'],
            x=top[metric],
            orientation="h",
            marker=dict(color=color),
            name=name,
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
            showlegend = showlegend
        )
        tr.meta = {"side": side}
        fig.add_trace(tr, row=row, col=col)
        if x_title:
            fig.update_xaxes(title_text=x_title, row=row, col=col)

    def add_scatter(fig, df, x, y, name="Team", side="team",
                    row=1, col=1, color="#1F77B4",
                    x_title=None, y_title=None, size_col=None):
        if x not in df.columns or y not in df.columns:
            empty_annotation(fig, row, col, f"Missing: {x} or {y}")
            return

        marker = dict(color=color, opacity=0.75, size=12)
        if size_col and size_col in df.columns:
            s = df[size_col].fillna(0)
            sizeref = max(s.max(), 1) / 30
            marker = dict(color=color, opacity=0.75, size=np.clip(s / max(sizeref, 1e-9), 8, 40))

        tr = go.Scatter(
            x=df[x], y=df[y],
            mode="markers+text",
            text=df["player_name"],
            textposition="top center",
            marker=marker,
            name=name,
            hovertemplate="<b>%{text}</b><br>x=%{x}<br>y=%{y}<extra></extra>", 
            showlegend=False
        )
        tr.meta = {"side": side}
        fig.add_trace(tr, row=row, col=col)
        if x_title:
            fig.update_xaxes(title_text=x_title, row=row, col=col)
        if y_title:
            fig.update_yaxes(title_text=y_title, row=row, col=col)

    def add_violin(fig, df, metric, name="Team", side="team",
                   row=1, col=1, y_title=None, color = "#1F77B4"):
        if metric not in df.columns:
            empty_annotation(fig, row, col, f"Missing: {metric}")
            return
        tr = go.Violin(
            y=df[metric].fillna(0),
            box_visible=True,
            meanline_visible=True,
            name=name,
            line_color=color,      # contour
            fillcolor=color,       # remplissage
            opacity=0.6            # transparence
            )
        tr.meta = {"side": side}
        fig.add_trace(tr, row=row, col=col)
        if y_title:
            fig.update_yaxes(title_text=y_title, row=row, col=col)

    def add_heatmap_zscore(fig, df, metrics, name="Team", side="team",
                           row=1, col=1, colorscale="RdBu", title=None):
        metrics = [m for m in metrics if m in df.columns]
        if not metrics:
            empty_annotation(fig, row, col, "No metrics available for heatmap")
            return

        mat = df.set_index("player_name")[metrics].fillna(0)
        std = mat.std(ddof=0).replace(0, 1)
        z = (mat - mat.mean()) / std

        tr = go.Heatmap(
            z=z.values,
            x=metrics,
            y=z.index.tolist(),
            colorscale=colorscale,
            reversescale=True,
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>",
            name=name
        )
        tr.meta = {"side": side}
        fig.add_trace(tr, row=row, col=col)
        if title:
            fig.update_xaxes(title_text=title, row=row, col=col)

    def team_totals(df, metric_cols):
        out = {}
        for c in metric_cols:
            if c in df.columns:
                out[c] = float(df[c].fillna(0).sum())
        return out

    # -------------------------
    # Filter match
    # -------------------------
    if "match_id" not in dashboard_df.columns:
        raise ValueError("dashboard_df must contain 'match_id'")

    if match_id not in dashboard_df["match_id"].dropna().unique():
        raise ValueError(f"match_id {match_id} not found in dashboard_df")

    match_df = dashboard_df[dashboard_df["match_id"] == match_id].copy()
    match_df = ensure_cols(match_df, ["team_id", "team_shortname", "player_name"], fill="")

    home = match_meta["home_team"]
    away = match_meta["away_team"]
    team_id = home["id"]
    opp_id = away["id"]
    team_name = home["name"]
    opp_name = away["name"]
    team_df, opp_df = split_team_opp(match_df, team_id, opp_id)

    # -------------------------
    # Derived metrics (safe)
    # -------------------------
    stop_press_col = pick_col(match_df, ["count_stop_possession_danger_pressing_x", "count_stop_possession_danger_pressing_y"])
    reduce_press_col = pick_col(match_df, ["count_reduce_possession_danger_pressing_x", "count_reduce_possession_danger_pressing_y"])
    danger_press_col = pick_col(match_df, ["count_possession_danger_pressing"])
    beaten_press_col = pick_col(match_df, ["count_beaten_by_possession_pressing_x", "count_beaten_by_possession_pressing_y"])
    linebreak_press_col = pick_col(match_df, ["count_affected_line_break_pressing_x", "count_affected_line_break_pressing_y"])

    for df in (team_df, opp_df):
        if stop_press_col and "count_pressing_x" in df.columns:
            df["pressing_stop_rate"] = safe_ratio(df[stop_press_col], df["count_pressing_x"])
        else:
            df["pressing_stop_rate"] = 0

        if reduce_press_col and "count_pressing_x" in df.columns:
            df["pressing_reduce_rate"] = safe_ratio(df[reduce_press_col], df["count_pressing_x"])
        else:
            df["pressing_reduce_rate"] = 0

        if beaten_press_col and "count_pressing_x" in df.columns:
            df["pressing_beaten_rate"] = safe_ratio(df[beaten_press_col], df["count_pressing_x"])
        else:
            df["pressing_beaten_rate"] = 0

        if linebreak_press_col and "count_pressing_x" in df.columns:
            df["pressing_linebreak_rate"] = safe_ratio(df[linebreak_press_col], df["count_pressing_x"])
        else:
            df["pressing_linebreak_rate"] = 0

    # -------------------------
    # Build 9 figures
    # Each figure: store fig_json + toggle_map (trace indices team/opp/both)
    # -------------------------
    figs_json = {}
    toggle_map = {}   # div_id -> {"team":[...], "opp":[...], "both":[...]}

    def finalize_figure(div_id, fig, default_side="team"):
        # Build indices per side based on trace.meta.side
        m = {"team": [], "opp": [], "both": []}
        for i, tr in enumerate(fig.data):
            side = None
            try:
                side = tr.meta.get("side") if tr.meta else None
            except Exception:
                side = None
            if side in m:
                m[side].append(i)
            else:
                # if missing meta, consider "both" (never hidden)
                m["both"].append(i)

        # default visibility: show team + both
        vis = []
        for i in range(len(fig.data)):
            if i in m["both"]:
                vis.append(True)
            elif default_side == "team":
                vis.append(i in m["team"])
            else:
                vis.append(i in m["opp"])

        for i, v in enumerate(vis):
            fig.data[i].visible = v

        figs_json[div_id] = fig.to_json()
        toggle_map[div_id] = m

    # ---- TAB 1: Overview
    fig1 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Top expected threat creators", "Top pressers (volume)",
        "Pressing stop rate", "Runs: volume vs expected threat"
    ))
    add_topN_bar(fig1, team_df, "xthreat_off_ball_runs", n=10, color=COLORS["xthreat"], name=team_name, side="team",
                 row=1, col=1, x_title="xThreat (probability)")
    add_topN_bar(fig1, opp_df, "xthreat_off_ball_runs", n=10, color=COLORS["xthreat"], name=opp_name, side="opp",
                 row=1, col=1, x_title="xThreat (probability)")
    add_topN_bar(fig1, team_df, "count_pressing_x", n=10, color=COLORS["pressing"], name=team_name, side="team",
                 row=1, col=2, x_title="Pressing actions (count)")
    add_topN_bar(fig1, opp_df, "count_pressing_x", n=10, color=COLORS["pressing"], name=opp_name, side="opp",
                 row=1, col=2, x_title="Pressing actions (count)")
    add_topN_bar(fig1, team_df, "pressing_stop_rate", n=10, color=COLORS["success"], name=team_name, side="team",
                 row=2, col=1, x_title="Stops per pressing action (ratio)")
    add_topN_bar(fig1, opp_df, "pressing_stop_rate", n=10, color=COLORS["success"], name=opp_name, side="opp",
                 row=2, col=1, x_title="Stops per pressing action (ratio)")
    add_scatter(fig1, team_df, "count_off_ball_runs", "xthreat_off_ball_runs", name=team_name, side="team",
                row=2, col=2, color=COLORS["runs"], 
                x_title="Off-ball runs (count)", y_title="xThreat (probability)")
    add_scatter(fig1, opp_df, "count_off_ball_runs", "xthreat_off_ball_runs", name=opp_name, side="opp",
                row=2, col=2, color=COLORS["neutral"],
                x_title="Off-ball runs (count)", y_title="xThreat (probability)")
    fig1 = style_fig(fig1, f"", height=760, showlegend=False)
    finalize_figure("graph-tab1", fig1)

    # ---- TAB 2: Off-ball intensity (bar + scatter + violin)
    fig2 = make_subplots(rows=2, cols=2, subplot_titles=(
        "High-Speed Runs", "Sprint runs",
        "Avg distance vs Avg speed", "Speed distribution"
    ))
    add_topN_bar(fig2, team_df, "count_hsr_off_ball_runs", n=10, color=COLORS["runs"], name=team_name, side="team",
                 row=1, col=1, x_title="HSR runs (count)")
    add_topN_bar(fig2, opp_df, "count_hsr_off_ball_runs", n=10, color=COLORS["runs"], name=opp_name, side="opp",
                 row=1, col=1, x_title="HSR runs (count)")
    add_topN_bar(fig2, team_df, "count_sprint_off_ball_runs", n=10, color=COLORS["runs"], name=team_name, side="team",
                 row=1, col=2, x_title="Sprint runs (count)")
    add_topN_bar(fig2, opp_df, "count_sprint_off_ball_runs", n=10, color=COLORS["runs"], name=opp_name, side="opp",
                 row=1, col=2, x_title="Sprint runs (count)")
    add_scatter(fig2, team_df, "avg_distance_covered_off_ball_runs", "avg_speed_avg_off_ball_runs",
                name=team_name, side="team", row=2, col=1, color=COLORS["runs"],
                x_title="Avg distance per run (m)", y_title="Avg speed (km/h)")
    add_scatter(fig2, opp_df, "avg_distance_covered_off_ball_runs", "avg_speed_avg_off_ball_runs",
                name=opp_name, side="opp", row=2, col=1, color=COLORS["runs"],
                x_title="Avg distance per run (m)", y_title="Avg speed (km/h)")
    add_violin(fig2, team_df, "avg_speed_avg_off_ball_runs", name=team_name, side="team", row=2, col=2,
               y_title="Avg speed (km/h)",  color=COLORS["runs"])
    add_violin(fig2, opp_df, "avg_speed_avg_off_ball_runs", name=opp_name, side="opp", row=2, col=2,
               y_title="Avg speed (km/h)",  color=COLORS["runs"])
    fig2 = style_fig(fig2, "", height=760, showlegend=False)
    finalize_figure("graph-tab2", fig2)

    # ---- TAB 3: Off-ball phases & end-product
    fig3 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Runs by phase (build/create/finish)", "Expected threat: create vs finish",
        "Dangerous runs (volume)", "Runs: targeted vs received"
    ))

    phase_cols = ["count_off_ball_runs_in_build_up", "count_off_ball_runs_in_create", "count_off_ball_runs_in_finish"]
    if all(c in team_df.columns for c in phase_cols) and all(c in opp_df.columns for c in phase_cols):
        # Stacked bars: 3 traces per side (works with TOGGLE_MAP approach)
        def add_phase_stack(df, name, side, row, col):
            tmp = df.copy()
            tmp["total_phase_runs"] = tmp[phase_cols].fillna(0).sum(axis=1)
            tmp = tmp.nlargest(10, "total_phase_runs")
            phase_labels = {
              "count_off_ball_runs_in_build_up": "Build-up",
              "count_off_ball_runs_in_create": "Create",
              "count_off_ball_runs_in_finish": "Finish",
            }
            phase_colors = {
              "count_off_ball_runs_in_build_up": COLORS["runs"],
              "count_off_ball_runs_in_create":   COLORS["xthreat"],
              "count_off_ball_runs_in_finish":   COLORS["success"],
            }
            
            for c in phase_cols:
                phase = phase_labels[c]
                tr = go.Bar(
                    y=tmp["player_name"],
                    x=tmp[c].fillna(0),
                    orientation="h",
                    name=phase,                 # <- texte de légende 
                    legendgroup=phase,          # <- regroupe team/opp sur la même entrée
                    #showlegend=(side == "team"),# <- évite les doublons dans la légende
                    marker=dict(color=phase_colors[c]),
                    hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
                )
                tr.meta = {"side": side}
                fig3.add_trace(tr, row=row, col=col)


            fig3.update_layout(barmode="stack")
            fig3.update_xaxes(title_text="Runs (count)", row=row, col=col)

        add_phase_stack(team_df, team_name, "team", 1, 1)
        add_phase_stack(opp_df, opp_name, "opp", 1, 1)
    else:
        add_topN_bar(fig3, team_df, "count_off_ball_runs", n=10, color="#1F77B4", name=team_name, side="team",
                     row=1, col=1, x_title="Off-ball runs (count)")
        add_topN_bar(fig3, opp_df, "count_off_ball_runs", n=10, color="#1F77B4", name=opp_name, side="opp",
                     row=1, col=1, x_title="Off-ball runs (count)")

    if "xthreat_off_ball_runs_in_create" in match_df.columns and "xthreat_off_ball_runs_in_finish" in match_df.columns:
        add_scatter(fig3, team_df, "xthreat_off_ball_runs_in_create", "xthreat_off_ball_runs_in_finish",
                    name=team_name, side="team", row=1, col=2, color=COLORS["xthreat"],
                    x_title="xThreat in create (prob.)", y_title="xThreat in finish (prob.)")
        add_scatter(fig3, opp_df, "xthreat_off_ball_runs_in_create", "xthreat_off_ball_runs_in_finish",
                    name=opp_name, side="opp", row=1, col=2, color=COLORS["xthreat"], 
                    x_title="xThreat in create (prob.)", y_title="xThreat in finish (prob.)")
    else:
        empty_annotation(fig3, 1, 2, "Missing xThreat phase columns")
    
    # figure 3
    add_topN_bar(fig3, team_df, "count_dangerous_off_ball_runs", n=10, color=COLORS["xthreat"], name=team_name, side="team",
                 row=2, col=1, x_title="Dangerous runs (count)", showlegend=False)
    add_topN_bar(fig3, opp_df, "count_dangerous_off_ball_runs", n=10, color=COLORS["xthreat"], name=opp_name, side="opp",
                 row=2, col=1, x_title="Dangerous runs (count)", showlegend=False)

    # Targeted vs received (if present)
    tgt_col = pick_col(match_df, ["count_targeted_off_ball_runs"])
    rcv_col = pick_col(match_df, ["count_received_off_ball_runs"])
    if tgt_col and rcv_col:
        def add_target_received(df, name, side):
            tmp = df.copy()
            tmp["tr_total"] = tmp[[tgt_col, rcv_col]].fillna(0).sum(axis=1)
            tmp = tmp.nlargest(10, "tr_total")
            for c, color in [(tgt_col, COLORS["runs"]), (rcv_col, COLORS["success"])]:
                tr = go.Bar(
                    y=tmp["player_name"],
                    x=tmp[c].fillna(0),
                    orientation="h",
                    name=c.replace('count_', '').replace('_off_ball_runs',''),
                    legendgroup=c,
                    #showlegend=(side == "team"),
                    marker=dict(color=color),
                    hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>"
                )
                tr.meta = {"side": side}
                fig3.add_trace(tr, row=2, col=2)
            fig3.update_layout(barmode="group")
            fig3.update_xaxes(title_text="Count", row=2, col=2)

        add_target_received(team_df, team_name, "team")
        add_target_received(opp_df, opp_name, "opp")
    else:
        empty_annotation(fig3, 2, 2, "Missing targeted/received columns")

    fig3 = style_fig(fig3, "", height=820, showlegend=True)
    fig3.update_layout(
    showlegend=True,
    #legend_title_text="Phase",
    legend=dict(x=1.02, y=1, xanchor="left", yanchor="top")
)
    finalize_figure("graph-tab3", fig3)

    # ---- TAB 4: Depth & support
    fig4 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Expected threat : in behind runs", "Expected thread : ahead of ball runs",
        "Expected threat : in behind runs (finish phase only)", "Expected thread : in behind vs ahead"
    ))
    add_topN_bar(fig4, team_df, "xthreat_runs_in_behind", n=10, color=COLORS["xthreat"], name=team_name, side="team",
                 row=1, col=1, x_title="xThreat (probability)")
    add_topN_bar(fig4, opp_df, "xthreat_runs_in_behind", n=10, color=COLORS["xthreat"], name=opp_name, side="opp",
                 row=1, col=1, x_title="xThreat (probability)")
    add_topN_bar(fig4, team_df, "xthreat_runs_ahead_of_the_ball", n=10, color=COLORS["xthreat"], name=team_name, side="team",
                 row=1, col=2, x_title="xThreat (probability)")
    add_topN_bar(fig4, opp_df, "xthreat_runs_ahead_of_the_ball", n=10, color=COLORS["xthreat"], name=opp_name, side="opp",
                 row=1, col=2, x_title="xThreat (probability)")
    add_topN_bar(fig4, team_df, "xthreat_runs_in_behind_in_finish", n=10, color=COLORS["xthreat"], name=team_name, side="team",
                 row=2, col=1, x_title="xThreat (probability)")
    add_topN_bar(fig4, opp_df, "xthreat_runs_in_behind_in_finish", n=10, color=COLORS["xthreat"], name=opp_name, side="opp",
                 row=2, col=1, x_title="xThreat (probability)")
    add_scatter(fig4, team_df, "xthreat_runs_in_behind", "xthreat_runs_ahead_of_the_ball",
                name=team_name, side="team", row=2, col=2, color=COLORS["runs"],
                x_title="Behind xThreat (prob.)", y_title="Ahead xThreat (prob.)")
    add_scatter(fig4, opp_df, "xthreat_runs_in_behind", "xthreat_runs_ahead_of_the_ball",
                name=opp_name, side="opp", row=2, col=2, color=COLORS["runs"],
                x_title="Behind xThreat (prob.)", y_title="Ahead xThreat (prob.)")
    fig4 = style_fig(fig4, "", height=760, showlegend=False)
    finalize_figure("graph-tab4", fig4)

    # ---- TAB 5: Pressing outcomes
    fig5 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Pressing: volume vs threat stopped (bubble=danger faced)",
        "Top threat stopped (count)",
        "Top threat reduced (count)",
        "Stop rate vs reduce rate"
    ))
    if stop_press_col and danger_press_col:
        add_scatter(fig5, team_df, "count_pressing_x", stop_press_col, name=team_name, side="team", row=1, col=1,
                    color=COLORS["pressing"], size_col=danger_press_col,
                    x_title="Pressing actions (count)", y_title="Stop danger (count)")
        add_scatter(fig5, opp_df, "count_pressing_x", stop_press_col, name=opp_name, side="opp", row=1, col=1,
                    color=COLORS["pressing"], size_col=danger_press_col,
                    x_title="Pressing actions (count)", y_title="Stop danger (count)")
    else:
        empty_annotation(fig5, 1, 1, "Missing stop/danger columns")

    if stop_press_col:
        add_topN_bar(fig5, team_df, stop_press_col, n=10, color=COLORS["success"], name=team_name, side="team",
                     row=1, col=2, x_title="Stop danger (count)")
        add_topN_bar(fig5, opp_df, stop_press_col, n=10, color=COLORS["success"], name=opp_name, side="opp",
                     row=1, col=2, x_title="Stop danger (count)")
    else:
        empty_annotation(fig5, 1, 2, "Missing stop column")

    if reduce_press_col:
        add_topN_bar(fig5, team_df, reduce_press_col, n=10, color=COLORS["success"], name=team_name, side="team",
                     row=2, col=1, x_title="Reduce danger (count)")
        add_topN_bar(fig5, opp_df, reduce_press_col, n=10, color=COLORS["success"], name=opp_name, side="opp",
                     row=2, col=1, x_title="Reduce danger (count)")
    else:
        empty_annotation(fig5, 2, 1, "Missing reduce column")

    add_scatter(fig5, team_df, "pressing_stop_rate", "pressing_reduce_rate", name=team_name, side="team",
                row=2, col=2, color=COLORS["success"],
                x_title="Stop rate (ratio)", y_title="Reduce rate (ratio)")
    add_scatter(fig5, opp_df, "pressing_stop_rate", "pressing_reduce_rate", name=opp_name, side="opp",
                row=2, col=2, color=COLORS["success"],
                x_title="Stop rate (ratio)", y_title="Reduce rate (ratio)")

    fig5 = style_fig(fig5, "", height=780, showlegend=False)
    finalize_figure("graph-tab5", fig5)

    # ---- TAB 6: Pressing failures
    fig6 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Top beaten by possession (count)",
        "Top affected line-break (count)",
        "Volume vs beaten rate",
        "Beaten rate distribution"
    ))
    if beaten_press_col:
        add_topN_bar(fig6, team_df, beaten_press_col, n=10, color=COLORS["pressing"], name=team_name, side="team",
                     row=1, col=1, x_title="Beaten (count)")
        add_topN_bar(fig6, opp_df, beaten_press_col, n=10, color=COLORS["pressing"], name=opp_name, side="opp",
                     row=1, col=1, x_title="Beaten (count)")
    else:
        empty_annotation(fig6, 1, 1, "Missing beaten column")

    if linebreak_press_col:
        add_topN_bar(fig6, team_df, linebreak_press_col, n=10, color=COLORS["pressing"], name=team_name, side="team",
                     row=1, col=2, x_title="Affected line-break (count)")
        add_topN_bar(fig6, opp_df, linebreak_press_col, n=10, color=COLORS["pressing"], name=opp_name, side="opp",
                     row=1, col=2, x_title="Affected line-break (count)")
    else:
        empty_annotation(fig6, 1, 2, "Missing affected line-break column")

    if "count_pressing_x" in match_df.columns:
        add_scatter(fig6, team_df, "count_pressing_x", "pressing_beaten_rate", name=team_name, side="team",
                    row=2, col=1, color=COLORS["pressing"],
                    x_title="Pressing actions (count)", y_title="Beaten rate (ratio)")
        add_scatter(fig6, opp_df, "count_pressing_x", "pressing_beaten_rate", name=opp_name, side="opp",
                    row=2, col=1, color=COLORS["pressing"],
                    x_title="Pressing actions (count)", y_title="Beaten rate (ratio)")
    else:
        empty_annotation(fig6, 2, 1, "Missing count_pressing_x")

    add_violin(fig6, team_df, "pressing_beaten_rate", name=team_name, side="team", row=2, col=2,
               y_title="Beaten rate (ratio)", color=COLORS["pressing"])
    add_violin(fig6, opp_df, "pressing_beaten_rate", name=opp_name, side="opp", row=2, col=2,
               y_title="Beaten rate (ratio)", color=COLORS["pressing"])

    fig6 = style_fig(fig6, "", height=780, showlegend=False)
    finalize_figure("graph-tab6", fig6)

    # ---- TAB 7: Player heatmap (overview)
    fig7 = make_subplots(rows=1, cols=1, subplot_titles=("Player KPI heatmap (z-score)",))
    heat_metrics = [
        "count_off_ball_runs", "xthreat_off_ball_runs", "count_dangerous_off_ball_runs",
        "count_pressing_x", "pressing_stop_rate", "pressing_reduce_rate", "pressing_beaten_rate", "pressing_linebreak_rate",
        stop_press_col, reduce_press_col, beaten_press_col, linebreak_press_col, danger_press_col
    ]
    heat_metrics = [m for m in heat_metrics if m]  # drop None
    add_heatmap_zscore(fig7, team_df, heat_metrics, name=team_name, side="team", row=1, col=1, title="z-score per team")
    add_heatmap_zscore(fig7, opp_df, heat_metrics, name=opp_name, side="opp", row=1, col=1, title="z-score per team")
    fig7 = style_fig(fig7, "", height=900, showlegend=False)
    finalize_figure("graph-tab7", fig7)

    # ---- TAB 8: Profiles (bubble + violin)
    fig8 = make_subplots(rows=2, cols=2, subplot_titles=(
        "Runs vs expected threat (size=dangerous runs)",
        "Pressing vs threat stopped (size=danger faced)",
        "Expected threat distribution",
        "Pressing stop rate distribution"
    ))
    add_scatter(fig8, team_df, "count_off_ball_runs", "xthreat_off_ball_runs", name=team_name, side="team",
                row=1, col=1, color=COLORS["runs"], size_col="count_dangerous_off_ball_runs",
                x_title="Off-ball runs (count)", y_title="xThreat (probability)")
    add_scatter(fig8, opp_df, "count_off_ball_runs", "xthreat_off_ball_runs", name=opp_name, side="opp",
                row=1, col=1, color=COLORS["runs"], size_col="count_dangerous_off_ball_runs",
                x_title="Off-ball runs (count)", y_title="xThreat (probability)")

    if stop_press_col and danger_press_col:
        add_scatter(fig8, team_df, "count_pressing_x", stop_press_col, name=team_name, side="team",
                    row=1, col=2, color=COLORS["pressing"], size_col=danger_press_col,
                    x_title="Pressing actions (count)", y_title="Stop danger (count)")
        add_scatter(fig8, opp_df, "count_pressing_x", stop_press_col, name=opp_name, side="opp",
                    row=1, col=2, color=COLORS["pressing"], size_col=danger_press_col,
                    x_title="Pressing actions (count)", y_title="Stop danger (count)")
    else:
        empty_annotation(fig8, 1, 2, "Missing stop/danger columns")

    add_violin(fig8, team_df, "xthreat_off_ball_runs", name=team_name, side="team", row=2, col=1,
               y_title="xThreat (probability)", color=COLORS["xthreat"])
    add_violin(fig8, opp_df, "xthreat_off_ball_runs", name=opp_name, side="opp", row=2, col=1,
               y_title="xThreat (probability)", color=COLORS["xthreat"])
    add_violin(fig8, team_df, "pressing_stop_rate", name=team_name, side="team", row=2, col=2,
               y_title="Stops/pressing (ratio)", color=COLORS["success"])
    add_violin(fig8, opp_df, "pressing_stop_rate", name=opp_name, side="opp", row=2, col=2,
               y_title="Stops/pressing (ratio)", color=COLORS["success"])

    fig8 = style_fig(fig8, "", height=820, showlegend=False)
    finalize_figure("graph-tab8", fig8)

    # ---- TAB 9: Team vs Opp summary (slope chart)
    fig9 = go.Figure()
    # choose a few stable KPIs
    summary_candidates = [
        "count_off_ball_runs",
        "xthreat_off_ball_runs",
        "count_dangerous_off_ball_runs",
        "count_pressing_x",
        stop_press_col,
        reduce_press_col,
        beaten_press_col,
        linebreak_press_col,
        danger_press_col
    ]
    summary_metrics = [c for c in summary_candidates if c and c in match_df.columns]

    t_tot = team_totals(team_df, summary_metrics)
    o_tot = team_totals(opp_df, summary_metrics)

    # Each KPI is one line from Team -> Opponent (always visible, not toggleable)
    for k in summary_metrics:
        y1 = t_tot.get(k, 0.0)
        y2 = o_tot.get(k, 0.0)
        tr = go.Scatter(
            x=[team_name, opp_name],
            y=[y1, y2],
            mode="lines+markers",
            name=k,
            hovertemplate=f"<b>{k}</b><br>%{{x}}: %{{y}}<extra></extra>"
        )
        tr.meta = {"side": "both"}  # never hidden
        fig9.add_trace(tr)

    fig9.update_yaxes(title_text="Total (match)")
    fig9 = style_fig(fig9, "", height=650, showlegend=True)
    finalize_figure("graph-tab9", fig9, default_side="team")

    ctx = get_match_context(match_meta)
    report_title = f"{ctx['home_team']} vs {ctx['away_team']} — Match Report"

    # -------------------------
    # HTML (tabs + plots)
    # -------------------------
    tabs = [
        ("Onglet1",  "Tab 1: Overview",         "graph-tab1",  760),
        ("Onglet2",  "Tab 2: Running intensity","graph-tab2",  760),
        ("Onglet3",  "Tab 3: Runs by phase", "graph-tab3",  820),
        ("Onglet4",  "Tab 4: Depth runs",  "graph-tab4",  760),
        ("Onglet5",  "Tab 5: Pressing impact","graph-tab5",  780),
        ("Onglet6",  "Tab 6: Pressing exposure","graph-tab6",  780),
        ("Onglet7",  "Tab 7: Player KPI heatmap",          "graph-tab7",  900),
        ("Onglet8",  "Tab 8: Player profiles (runs/pressing/threat)",         "graph-tab8",  820),
        ("Onglet9",  "Tab 9: Match KPI totals (Home vs Away)",      "graph-tab9",  650)
    ]

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>{report_title}</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ font-family: Arial; margin: 20px; background: #f0f2f5; }}
    .tab {{ overflow: hidden; border: 1px solid #ccc; background: #2c3e50; }}
    .tab button {{
      background: #3498db; color: white; float: left; border: none;
      padding: 14px 20px; cursor: pointer; font-size: 16px;
    }}
    .tab button:hover {{ background: #2980b9; }}
    .tab button.active {{ background: #e74c3c; }}
    .tabcontent {{
      display: none; padding: 20px; background: white;
      border: 1px solid #ccc; border-top: none; min-height: 900px;
    }}
    .match-section {{ margin: 20px 0; padding: 15px; background: #ecf0f1; border-radius: 8px; }}
    .toggle-bar {{ margin: 12px 0 18px 0; }}
    .toggle-bar button {{
      background: #34495e; color: white; border: none; padding: 10px 14px;
      margin-right: 8px; border-radius: 6px; cursor: pointer; font-size: 14px;
    }}
    .toggle-bar button.active {{ background: #e67e22; }}
    .help-box {{
  margin: 8px 0 12px 0;
  font-size: 13px;
  color: #2c3e50;
      }}
    .help-item {{
  display: inline-block;
  margin-right: 14px;
  cursor: help;
  border-bottom: 1px dotted #999;
}}
  </style>
</head>
<body>

<h1>{report_title}</h1>

<div class="toggle-bar">
  <button id="btn-team" class="active" onclick="setSide('team')">{team_name}</button>
  <button id="btn-opp" onclick="setSide('opp')">{opp_name}</button>
</div>

<div class="tab">
"""

    for i, (tab_id, label, div_id, h) in enumerate(tabs):
        active = "active" if i == 0 else ""
        html += f"""<button class="tablinks {active}" onclick="openTab(event,'{tab_id}')">{label}</button>\n"""

    html += "</div>\n"

    for i, (tab_id, label, div_id, h) in enumerate(tabs):
        display = "block" if i == 0 else "block"
        html += f"""
<div id="{tab_id}" class="tabcontent" style="display:{display};">
  <div class="match-section">
    <h2>{label}</h2>
    <div id="{div_id}" style="width:100%;height:{h}px;"></div>
  </div>
</div>
"""
    

    # Inject JS objects (FIGS + TOGGLE_MAP)
    html += "<script>\n"
    html += "var FIGS = {};\n"
    html += "var TOGGLE_MAP = {};\n"
    for div_id, fig_json in figs_json.items():
        html += f'FIGS["{div_id}"] = {fig_json};\n'
    html += f"TOGGLE_MAP = {json.dumps(toggle_map)};\n"
    html += "</script>\n"

    # Render all plots once (simple). If you want lazy rendering later, it’s easy to adapt.
    html += "<script>\n"
    html += "Object.keys(FIGS).forEach(function(divId){\n"
    html += "  Plotly.newPlot(divId, FIGS[divId].data, FIGS[divId].layout, {responsive:true});\n"
    html += "});\n"
    html += "</script>\n"

    # Tabs + toggle (propre via TOGGLE_MAP indices) [web:136]
    html += """
<script>
function openTab(evt, tabName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) { tabcontent[i].style.display = "none"; }

  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) { tablinks[i].className = tablinks[i].className.replace(" active", ""); }

  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " active";
}

function setSide(side) {
  document.getElementById('btn-team').classList.remove('active');
  document.getElementById('btn-opp').classList.remove('active');
  if (side === 'team') document.getElementById('btn-team').classList.add('active');
  else document.getElementById('btn-opp').classList.add('active');

  Object.keys(TOGGLE_MAP).forEach(function(divId) {
    var gd = document.getElementById(divId);
    if (!gd || !gd.data) return;

    var m = TOGGLE_MAP[divId] || {};
    var teamIdx = new Set((m.team || []));
    var oppIdx  = new Set((m.opp || []));
    var bothIdx = new Set((m.both || []));

    var vis = gd.data.map(function(_, i) {
      if (bothIdx.has(i)) return true;
      if (side === "team") return teamIdx.has(i);
      return oppIdx.has(i);
    });

    Plotly.restyle(gd, {visible: vis});
  });
}

const LONG_EXPL = {
  "graph-tab1": [
    { label: "Top expected threat creators", text: "Players ranked by total Expected Threat generated from their actions. Higher values indicate greater contribution to creating dangerous situations." },
    { label: "Top pressers (volume)", text: "Players ranked by number of pressing actions (activity, not effectiveness)." },
    { label: "Pressing stop rate", text: "Stops per pressing action. A “stop” means the press led to an immediate disruption of the opponent’s possession sequence based on your event definitions." },
    { label: "Runs: volume vs expected threat", text: "Compares how often players make off-ball runs (x-axis) with the Expected Threat generated by those runs (y-axis)." }
  ],
  "graph-tab2" : [
    {label: "High-Speed Runs", text: "Players ranked by the number of high-speed off-ball runs. Useful for identifying repeated high-intensity efforts."}, 
    {label: "Sprint runs", text:"Players ranked by number of sprint off-ball runs. Highlights peak-intensity running output."},
    {label: "Avg distance vs Avg speed", text:"Each point is a player: average distance per run vs average run speed. Helps distinguish short/fast vs long/steady run profiles."}, 
    {label: "Speed distribution", text: "Distribution of player average run speeds. Shows whether the team has many moderate-speed runners or a few very fast profiles."}
    ],
  "graph-tab3" : [
    {label: "Runs by phase (build/create/finish)", text:"Breakdown of off-ball runs by possession phase. Helps identify whether players run more to support build-up, chance creation, or finishing."},
    {label: "Expected threat: create vs finish", text:"For each player, compares Expected Threat generated in the create phase versus the finish phase. Reveals whether threat comes earlier or later in attacks."},
    {label: "Dangerous runs (volume)", text:"Players ranked by number of “dangerous” off-ball runs as defined in your pipeline."}, 
    {label: "Runs: targeted vs received", text:"Compares runs that teammates attempted to target with a pass versus runs that actually received the ball (only shown if both columns exist)."}
    ],
  "graph-tab4": [
    {label: "Expected threat : in behind runs", text: "Expected Threat generated by runs attacking the space behind the defensive line. Useful to quantify depth threat."},
    {label: "Expected thread : ahead of ball runs", text:"Expected Threat generated by runs made ahead of the ball (supporting forward options)."},
    {label: "Expected thread : in behind runs (finish phase only)", text:"Expected Threat from in-behind runs specifically during the finish phase, focusing on end-product situations."}, 
    {label: "Expected thread : in behind vs ahead", text:"Each point is a player. Compares in-behind threat vs ahead-of-ball threat to identify runner types."}
    ]
  ,
  "graph-tab5" : [
    {label: "Pressing: volume vs threat stopped (bubble=danger faced)", text: "Each point is a player. X = pressing volume, Y = “threat stopped” count; bubble size reflects total threat faced in pressing contexts."},
    {label: "Top threat stopped (count)", text: "Players ranked by how many opponent threats were stopped after their pressing actions (count metric from your dataset)."},
    {label: "Top threat reduced (count)", text: "Players ranked by how many threats were reduced (not fully stopped) after pressing actions (count metric from your dataset)."},
    {label: "Stop rate vs reduce rate", text: "Each point is a player. Compares stop efficiency vs reduce efficiency per pressing action."}
    ],
    "graph-tab6" : [
    {label: "Top beaten by possession (count)", text: "Players ranked by how often they were “beaten” in possession/pressing contexts according to your event definition."},
    {label: "Top affected line-break (count)", text: "Players ranked by involvement in line-break events (count metric from your dataset). Indicates exposure or involvement in defensive structure breaks."},
    {label: "Volume vs beaten rate", text: "Each point is a player. X = pressing volume, Y = beaten rate (beaten per pressing action). Helps separate high-volume pressers from high-risk profiles."},
    {label: "Beaten rate distribution", text: "Distribution of beaten rate across players. Useful to spot outliers with unusually high exposure."}
    ],
  "graph-tab7": [
    { label: "Player KPI heatmap (z-score)", text: "Heatmap of standardized player KPIs (z-scores) inside the team." }
  ], 
  "graph-tab8" : [
    {label: "Runs vs expected threat (size=dangerous runs)", text:"Player profile map: running volume vs Expected Threat, with bubble size showing dangerous-run volume. Identifies high-output vs high-impact players."},
    {label: "Pressing vs threat stopped (size=danger faced)", text: "Player profile map: pressing volume vs threat stopped, with bubble size indicating threat faced. Separates active pressers from effective disruptors."},
    {label: "Expected threat distribution", text:"Distribution of Expected Threat per player. Useful to see whether impact is concentrated in a few players or spread across the team."},
    {label: "Pressing stop rate distribution", text:"Distribution of pressing stop rate per player. Shows consistency vs outliers in pressing effectiveness."}
  ], 
  "graph-tab9" : [
    {label: "Match KPI totals (Home vs Away)", text:"For each KPI, the chart draws a line from Team total to Opponent total. It is a match-level comparison, not a player ranking."}
  ]
  
  
};

const TAB9_LABELS = {
  "count_off_ball_runs": "Number of off-ball runs",
  "xthreat_off_ball_runs": "Expected threat from off-ball runs",
  "count_dangerous_off_ball_runs": "Number of dangerous off-ball runs",
  "count_pressing_x": "Number of pressing actions",
  "count_stop_possession_danger_pressing_x": "Number of pressing actions that stopped a dangerous possession",
  "count_reduce_possession_danger_pressing_x": "Number of pressing actions that reduced possession danger",
  "count_beaten_by_possession_pressing_x": "Number of pressing actions beaten by possession",
  "count_affected_line_break_pressing_x": "Number of pressing actions affected by a line break",
  "count_possession_danger_pressing": "Number of dangerous possessions"
};

function esc(s){
  return String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
}

function injectHelp(divId){
  const graphDiv = document.getElementById(divId);
  const items = LONG_EXPL[divId];
  if(!graphDiv || !items || !items.length) return;

  const box = document.createElement("div");
  box.className = "help-box";
  box.innerHTML = items.map(it =>
    `<span class="help-item" title="${esc(it.text)}">${esc(it.label)}</span>`
  ).join("");

  graphDiv.parentNode.insertBefore(box, graphDiv);
}

document.addEventListener("DOMContentLoaded", () => {
  Object.keys(LONG_EXPL).forEach(injectHelp);
});

function relabelFigure(divId, labels){
  const fig = FIGS[divId];
  if (!fig || !fig.data) return;
  fig.data.forEach(tr => {
    const oldName = tr.name;
    const newName = labels[oldName];
    if (newName) {
      tr.name = newName; // => légende
      if (typeof tr.hovertemplate === "string") {
        tr.hovertemplate = tr.hovertemplate.replaceAll(oldName, newName); // => tooltip
      }
    }
  });
}

relabelFigure("graph-tab9", TAB9_LABELS);

// Force la mise à jour immédiate de la légende
Plotly.react(
  "graph-tab9",
  FIGS["graph-tab9"].data,
  FIGS["graph-tab9"].layout,
  { responsive: true }
);

</script>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8", errors="ignore") as f:
        f.write(html)

    print(f"SUCCESS: Match report created: {output_file}")
