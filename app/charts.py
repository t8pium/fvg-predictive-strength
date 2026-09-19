from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def _base(fig: go.Figure, title: str, y_title: str = "") -> go.Figure:
    """Apply one quiet, readable visual system to every published chart."""
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16)),
        height=400,
        margin=dict(l=24, r=18, t=58, b=36),
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        hovermode="x unified",
        bargap=0.22,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(
        showgrid=False,
        automargin=True,
        tickfont=dict(size=11),
        title_font=dict(size=12),
    )
    fig.update_yaxes(
        title_text=y_title or None,
        automargin=True,
        gridcolor="rgba(127,127,127,0.16)",
        zeroline=True,
        zerolinecolor="rgba(127,127,127,0.42)",
        tickfont=dict(size=11),
        title_font=dict(size=12),
    )
    fig.update_traces(hoverlabel=dict(namelength=-1))
    return fig


def _bar(x, y, title: str, y_title: str, *, text=None) -> go.Figure:
    fig = go.Figure(go.Bar(x=x, y=y, text=text, textposition="auto" if text is not None else None))
    return _base(fig, title, y_title)


def published_charts(exp_id: str, reference: dict) -> list[tuple[str, go.Figure, pd.DataFrame]]:
    e = reference["experiments"][exp_id]
    charts: list[tuple[str, go.Figure, pd.DataFrame]] = []

    if exp_id == "raw_fill":
        df = pd.DataFrame({
            "Horizon": ["5m", "15m", "30m", "60m", "120m", "240m", "~1d", "~3d"],
            "Touch rate (%)": [x * 100 for x in e["touch_rate"]],
        })
        fig = go.Figure(go.Scatter(x=df["Horizon"], y=df["Touch rate (%)"], mode="lines+markers"))
        charts.append(("Touch probability rises rapidly with horizon", _base(fig, "Published raw FVG touch probability", "Touch probability (%)"), df))
        eventual = pd.DataFrame({
            "Outcome": ["Eventual near-edge touch", "Eventual full fill"],
            "Rate (%)": [e["eventual_touch"] * 100, e["eventual_full"] * 100],
        })
        charts.append(("Almost all gaps are revisited eventually in-sample", _bar(eventual["Outcome"], eventual["Rate (%)"], "Eventual revisit within available sample", "Rate (%)", text=eventual["Rate (%)"].round(3)), eventual))

    elif exp_id == "matched_attraction":
        df = pd.DataFrame(e["deep_1m"]).copy()
        df["FVG (%)"] = df["fvg"] * 100
        df["Control (%)"] = df["control"] * 100
        fig = go.Figure()
        fig.add_bar(name="FVG", x=df["horizon"], y=df["FVG (%)"])
        fig.add_bar(name="Matched control", x=df["horizon"], y=df["Control (%)"])
        fig.update_layout(barmode="group")
        charts.append(("Absolute revisit rates are high for both FVGs and ordinary matched zones", _base(fig, "FVG versus matched-control touch probability", "Touch probability (%)"), df[["horizon", "FVG (%)", "Control (%)", "difference_pp"]]))
        charts.append(("The excess attraction decays toward zero", _bar(df["horizon"], df["difference_pp"], "Incremental FVG attraction", "FVG − control (percentage points)", text=df["difference_pp"].round(3)), df[["horizon", "difference_pp"]]))

    elif exp_id == "age_decay":
        df = pd.DataFrame(e["one_minute"])
        charts.append(("Most of the incremental attraction is early", _bar(df["window"], df["difference_pp"], "1m conditional attraction after surviving unfilled", "Difference (percentage points)", text=df["difference_pp"].round(2)), df))

    elif exp_id == "continuation":
        df = pd.DataFrame(e["five_bar"])
        charts.append(("Five-bar continuation is inconsistent across timeframes", _bar(df["timeframe"], df["difference_atr"], "FVG move − matched non-FVG move", "ATR-normalized return difference", text=df["difference_atr"].round(3)), df))

    elif exp_id == "retest":
        df = pd.DataFrame(e["reaction"])
        charts.append(("First-touch reaction advantage is positive but modest", _bar(df["timeframe"], df["difference_pp"], "First-touch rejection advantage", "Difference (percentage points)", text=df["difference_pp"].round(2)), df))

    elif exp_id == "midpoint":
        df = pd.DataFrame(e["reaction"])
        fig = go.Figure()
        fig.add_bar(name="FVG", x=df["timeframe"], y=df["fvg"])
        fig.add_bar(name="Matched control", x=df["timeframe"], y=df["control"])
        fig.update_layout(barmode="group")
        charts.append(("Midpoint rejection varies by timeframe", _base(fig, "Midpoint rejection race", "Rejection rate (%)"), df))
        charts.append(("The largest published midpoint difference is the 4H cell", _bar(df["timeframe"], df["difference_pp"], "Midpoint FVG − control difference", "Difference (percentage points)", text=df["difference_pp"].round(2)), df[["timeframe", "difference_pp"]]))

    elif exp_id == "body_acceptance":
        bands = pd.DataFrame(e["four_hour_bands"])
        charts.append(("Exploratory 4H body-close bands", _bar(bands["band"], bands["mean_R"], "4H gross expectancy by close-depth band", "Mean gross R", text=bands["mean_R"].round(3)), bands))
        fig = go.Figure(go.Bar(x=bands["band"], y=bands["win_rate"], text=bands["win_rate"].round(2), textposition="auto"))
        charts.append(("Win rate peaks in the selected 45–50% cell", _base(fig, "4H win rate by close-depth band", "Win rate (%)"), bands[["band", "N", "win_rate", "mean_R"]]))

    elif exp_id == "controls_regimes":
        df = pd.DataFrame(e["distance"])
        fig = go.Figure()
        fig.add_bar(name="FVG", x=df["bucket"], y=df["fvg"])
        fig.add_bar(name="Matched control", x=df["bucket"], y=df["control"])
        fig.update_layout(barmode="group")
        charts.append(("Starting distance explains much of the raw touch probability", _base(fig, "60-minute touch rate by starting distance", "Touch rate (%)"), df))
        charts.append(("The residual FVG difference remains small inside distance buckets", _bar(df["bucket"], df["difference_pp"], "FVG − control by distance", "Difference (percentage points)", text=df["difference_pp"].round(2)), df[["bucket", "difference_pp"]]))

    elif exp_id == "oos":
        df = pd.DataFrame(e["five_bar"])
        fig = go.Figure()
        fig.add_bar(name="Early 70%", x=df["timeframe"], y=df["train_pp"])
        fig.add_bar(name="Later 30%", x=df["timeframe"], y=df["test_pp"])
        fig.update_layout(barmode="group")
        charts.append(("Several effects weaken or reverse later in the sample", _base(fig, "Five-bar matched attraction: early versus later sample", "Difference (percentage points)"), df))
        deep = pd.DataFrame({
            "Split": ["Early 70%", "Later 30%"],
            "Difference (pp)": [e["deep_1m_60m"]["train_pp"], e["deep_1m_60m"]["test_pp"]],
        })
        charts.append(("The deep 1m / 60m effect nearly disappears in the later sample", _bar(deep["Split"], deep["Difference (pp)"], "Deep 1m matched attraction at 60 minutes", "Difference (percentage points)", text=deep["Difference (pp)"].round(2)), deep))

    return charts


def headline_metrics(exp_id: str, reference: dict) -> list[tuple[str, str, str | None]]:
    e = reference["experiments"][exp_id]
    if exp_id == "raw_fill":
        return [
            ("5m touch", f"{e['touch_rate'][0] * 100:.1f}%", None),
            ("60m touch", f"{e['touch_rate'][3] * 100:.1f}%", None),
            ("Eventual touch", f"{e['eventual_touch'] * 100:.2f}%", None),
        ]
    if exp_id == "matched_attraction":
        rows = e["deep_1m"]
        return [
            ("5m excess", f"+{rows[0]['difference_pp']:.2f} pp", None),
            ("60m excess", f"+{rows[3]['difference_pp']:.2f} pp", None),
            ("~1d excess", f"{rows[6]['difference_pp']:+.3f} pp", None),
        ]
    if exp_id == "age_decay":
        rows = e["one_minute"]
        return [(rows[i]["window"], f"{rows[i]['difference_pp']:+.2f} pp", None) for i in range(min(3, len(rows)))]
    if exp_id == "continuation":
        rows = e["five_bar"]
        return [(f"{rows[i]['timeframe']} 5-bar", f"{rows[i]['difference_atr']:+.3f} ATR", None) for i in [0, 1, 3]]
    if exp_id == "retest":
        rows = e["reaction"]
        return [(f"{rows[i]['timeframe']} reaction", f"{rows[i]['difference_pp']:+.2f} pp", None) for i in [0, 1, 4]]
    if exp_id == "midpoint":
        rows = e["reaction"]
        return [("1m difference", f"{rows[0]['difference_pp']:+.2f} pp", None), ("1H difference", f"{rows[3]['difference_pp']:+.2f} pp", None), ("4H difference", f"{rows[4]['difference_pp']:+.2f} pp", None)]
    if exp_id == "body_acceptance":
        row = next(x for x in e["four_hour_bands"] if x["band"] == "45–50%")
        return [("4H 45–50% N", f"{row['N']}", None), ("Win rate", f"{row['win_rate']:.2f}%", None), ("Mean gross R", f"{row['mean_R']:.3f}", None)]
    if exp_id == "controls_regimes":
        return [("FVG odds ratio", f"{e['fvg_odds_ratio_60m']:.3f}", None), ("<0.25 ATR diff", f"{e['distance'][0]['difference_pp']:+.2f} pp", None), ("2–3 ATR diff", f"{e['distance'][-1]['difference_pp']:+.2f} pp", None)]
    if exp_id == "oos":
        deep = e["deep_1m_60m"]
        return [("Early 70%", f"{deep['train_pp']:+.2f} pp", None), ("Later 30%", f"{deep['test_pp']:+.2f} pp", None), ("4H later", f"{e['five_bar'][-1]['test_pp']:+.2f} pp", None)]
    return []
