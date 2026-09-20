from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fvg_research.bars import resample_ohlcv
from fvg_research.dataset import current_pickle, dataset_ready
from fvg_research.economics import economic_summary, scenario_table
from fvg_research.event_explorer import (
    event_catalog,
    event_window,
    matched_control_for_event,
    summarize_event,
)
from fvg_research.fvg import touch_at_horizon
from fvg_research.preflight import inspect_sources
from fvg_research.stability import local_atlas, reference_atlas
from research_v2.comparison import build_v1_v2_comparison
from research_v2.hypotheses import register_hypothesis, verify_hypothesis
from research_v2.power import detectable_r_mean, mde_two_proportion, power_scenarios

from .runtime import ROOT, choose_local_files, run_process
from .ui import callout, hero, info_card, section_header

CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "scrollZoom": False,
}


@st.cache_data(show_spinner=False)
def _load_bars(path_text: str, mtime_ns: int) -> pd.DataFrame:
    path = Path(path_text)
    frame = pd.read_pickle(path)
    if "ts_event" in frame.columns:
        frame = frame.set_index("ts_event")
    frame.index = pd.to_datetime(frame.index, utc=True)
    return frame.sort_index()


@st.cache_data(show_spinner=False)
def _bars_for_timeframe(path_text: str, mtime_ns: int, timeframe: str) -> pd.DataFrame:
    base = _load_bars(path_text, mtime_ns)
    return base if timeframe == "1m" else resample_ohlcv(base, timeframe)


@st.cache_data(show_spinner=False)
def _event_catalog_cached(path_text: str, mtime_ns: int, timeframe: str, include_market_state: bool) -> pd.DataFrame:
    return event_catalog(
        _bars_for_timeframe(path_text, mtime_ns, timeframe),
        include_market_state=include_market_state,
    )


@st.cache_data(show_spinner=False)
def _event_outcome_cached(path_text: str, mtime_ns: int, timeframe: str, horizon: int) -> pd.Series:
    bars = _bars_for_timeframe(path_text, mtime_ns, timeframe)
    events = _event_catalog_cached(path_text, mtime_ns, timeframe, False)
    return touch_at_horizon(bars, events, horizon).astype(bool)


@st.cache_data(show_spinner=False)
def _matched_control_cached(path_text: str, mtime_ns: int, timeframe: str, event_iso: str) -> dict[str, object] | None:
    bars = _bars_for_timeframe(path_text, mtime_ns, timeframe)
    result = matched_control_for_event(bars, pd.Timestamp(event_iso))
    return result.to_dict() if result is not None else None


def _dataset_context() -> tuple[Path, int] | None:
    if not dataset_ready():
        return None
    path = current_pickle()
    return path, path.stat().st_mtime_ns


def _candlestick(
    frame: pd.DataFrame,
    *,
    title: str,
    lower: float,
    upper: float,
    mid: float,
    marker_ts: pd.Timestamp,
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=frame.index,
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                name="OHLC",
            )
        ]
    )
    fig.add_hrect(y0=lower, y1=upper, opacity=0.14, line_width=1)
    fig.add_hline(y=mid, line_dash="dot", opacity=0.65)
    fig.add_vline(x=marker_ts, line_dash="dash", opacity=0.8)
    fig.update_layout(
        title=title,
        height=520,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
    )
    return fig


def event_explorer_page() -> None:
    hero(
        "Visual audit",
        "FVG Event Explorer",
        "Inspect the actual bars behind individual FVG observations, their mechanically defined zone, future outcome, and an optional matched ordinary control.",
        ["Candles", "Event-level audit", "Matched control", "Filters"],
    )
    context = _dataset_context()
    if context is None:
        callout(
            "Local dataset required",
            "Prepare the licensed MNQ dataset first. The explorer intentionally works from the exact active bars used by local calculations.",
        )
        return

    path, mtime = context
    timeframe = st.selectbox(
        "Native timeframe",
        ["1m", "5m", "15m", "1H", "4H"],
        help="Higher timeframes are resampled from the same active 1-minute series using the CME 18:00 ET anchor.",
    )
    include_state = st.checkbox(
        "Enable exact volatility-regime / trend filters",
        value=False,
        help="This reproduces the rolling causal market-state classification and is intentionally deferred because it is much heavier than basic event browsing.",
    )
    with st.spinner("Loading event catalogue…" if not include_state else "Calculating exact causal market-state filters…"):
        catalog = _event_catalog_cached(str(path), mtime, timeframe, include_state)

    section_header(
        "Filter",
        "Choose the population you want to inspect",
        "Basic browsing is kept fast. Exact rolling volatility/trend state is optional because reproducing it across millions of bars is computationally heavier.",
    )
    f1, f2, f3, f4 = st.columns(4)
    years = sorted(int(value) for value in catalog["year"].dropna().unique())
    year = f1.selectbox("Year", ["All", *years])
    direction = f2.selectbox("Direction", ["All", "Bullish", "Bearish"])
    sessions = sorted(str(value) for value in catalog["session"].dropna().unique())
    session = f3.selectbox("Session", ["All", *sessions])
    if include_state and "vol_regime" in catalog.columns:
        regimes = sorted(str(value) for value in catalog["vol_regime"].dropna().unique())
        regime = f4.selectbox("Volatility regime", ["All", *regimes])
    else:
        f4.caption("Volatility regime filter is off")
        regime = "All"

    g1, g2, g3 = st.columns(3)
    max_distance = float(g1.number_input("Max starting distance (ATR)", min_value=0.0, value=5.0, step=0.25))
    max_width = float(g2.number_input("Max FVG width (ATR)", min_value=0.0, value=3.0, step=0.25))
    horizon = int(g3.selectbox("Outcome horizon (native bars)", [1, 3, 5, 10, 20, 60], index=2))
    outcome_filter = st.radio("Outcome filter", ["All", "Touched", "Not touched"], horizontal=True)

    filtered = catalog.loc[
        catalog["distance_atr"].le(max_distance)
        & catalog["width_atr"].le(max_width)
    ].copy()
    if year != "All":
        filtered = filtered.loc[filtered["year"].eq(int(year))]
    if direction != "All":
        filtered = filtered.loc[filtered["direction_label"].eq(direction)]
    if session != "All":
        filtered = filtered.loc[filtered["session"].astype(str).eq(session)]
    if regime != "All" and "vol_regime" in filtered.columns:
        filtered = filtered.loc[filtered["vol_regime"].astype(str).eq(regime)]
    if outcome_filter != "All" and len(filtered):
        outcomes = _event_outcome_cached(str(path), mtime, timeframe, horizon).reindex(filtered.index)
        filtered = filtered.loc[outcomes.eq(outcome_filter == "Touched")]

    if filtered.empty:
        st.warning("No events match those filters.")
        return

    key = "event_explorer_position"
    position = int(st.session_state.get(key, 0))
    position = max(0, min(position, len(filtered) - 1))
    controls = st.columns([1, 1, 1, 3])
    if controls[0].button("← Previous", width="stretch"):
        st.session_state[key] = max(0, position - 1)
        st.rerun()
    if controls[1].button("Random", width="stretch"):
        st.session_state[key] = random.randrange(len(filtered))
        st.rerun()
    if controls[2].button("Next →", width="stretch"):
        st.session_state[key] = min(len(filtered) - 1, position + 1)
        st.rerun()
    controls[3].caption(f"{timeframe} · event {position + 1:,} of {len(filtered):,} matching observations")

    event_ts = filtered.index[position]
    bars = _bars_for_timeframe(str(path), mtime, timeframe)
    summary = summarize_event(bars, event_ts, horizon=horizon)
    row = filtered.loc[event_ts]

    metrics = st.columns(6)
    metrics[0].metric("Direction", str(summary["direction"]).title())
    metrics[1].metric("Width", f"{summary['width_ticks']:.1f} ticks")
    metrics[2].metric("Width / ATR", f"{summary['width_atr']:.3f}")
    metrics[3].metric("Distance / ATR", f"{summary['distance_atr']:.3f}")
    metrics[4].metric(f"Touch ≤ {horizon}", "YES" if summary["touch_within_horizon"] else "NO")
    metrics[5].metric("Session", str(row.get("session", "—")))

    window = event_window(bars, event_ts, before=15, after=max(30, min(horizon, 120)))
    fig = _candlestick(
        window,
        title=f"Real FVG · {event_ts.isoformat()}",
        lower=float(summary["lower"]),
        upper=float(summary["upper"]),
        mid=float(summary["mid"]),
        marker_ts=event_ts,
    )
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

    with st.expander("Exact event record"):
        st.json(summary)

    section_header(
        "Matched control",
        "Inspect an ordinary state-matched zone",
        "The control copies the selected FVG's normalized geometry into a non-FVG formation bar with a similar broad market state.",
    )
    if st.button("Build matched control for this event", width="stretch"):
        with st.spinner("Matching this event against ordinary non-FVG bars…"):
            st.session_state["event_explorer_control"] = _matched_control_cached(str(path), mtime, timeframe, event_ts.isoformat())
            st.session_state["event_explorer_control_event"] = timeframe + "|" + event_ts.isoformat()

    control = None
    if st.session_state.get("event_explorer_control_event") == timeframe + "|" + event_ts.isoformat():
        control = st.session_state.get("event_explorer_control")
    if control is None:
        st.caption("Matched-control generation is on demand so browsing real events stays fast.")
        return
    control_ts = pd.Timestamp(control["control_ts"])
    control_window = event_window(bars, control_ts, before=15, after=max(30, min(horizon, 120)))
    fig = _candlestick(
        control_window,
        title=f"Matched ordinary zone · {control_ts.isoformat()}",
        lower=float(control["lower"]),
        upper=float(control["upper"]),
        mid=float(control["mid"]),
        marker_ts=control_ts,
    )
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
    with st.expander("Matched-control record"):
        st.json({key: str(value) if isinstance(value, pd.Timestamp) else value for key, value in control.items()})


def scientific_stress_page() -> None:
    hero(
        "False-discovery checks",
        "Placebos & ablations",
        "Ask whether the pipeline discovers similar-looking effects when the FVG label is deliberately broken, and which matching assumptions materially change the estimate.",
        ["Negative controls", "Ablation", "False positives", "Research v2"],
    )
    if not dataset_ready():
        callout("Local dataset required", "Prepare the active dataset before running the stress tests.")
        return

    c1, c2, c3 = st.columns(3)
    horizon = int(c1.number_input("Horizon (1m bars)", min_value=1, value=60, step=1))
    max_events = int(c2.number_input("Max parent events", min_value=100, value=3000, step=500))
    controls = int(c3.number_input("Controls / parent for ablation", min_value=1, value=2, step=1))

    left, right = st.columns(2)
    if left.button("Run placebo / negative-control suite", type="primary", width="stretch"):
        live = st.empty()
        rc, log = run_process(
            ["-m", "research_v2.runner", "placebo-1m", "--horizon", str(horizon), "--max-events", str(max_events)],
            live_placeholder=live,
        )
        st.session_state["placebo_log"] = log
        st.session_state["placebo_rc"] = rc

    if right.button("Run matching ablation matrix", width="stretch"):
        live = st.empty()
        rc, log = run_process(
            [
                "-m", "research_v2.runner", "ablation-1m",
                "--horizon", str(horizon),
                "--max-events", str(max_events),
                "--controls", str(controls),
            ],
            live_placeholder=live,
        )
        st.session_state["ablation_log"] = log
        st.session_state["ablation_rc"] = rc

    for key, title in (("placebo", "Placebo log"), ("ablation", "Ablation log")):
        if st.session_state.get(f"{key}_log"):
            with st.expander(title, expanded=st.session_state.get(f"{key}_rc") != 0):
                st.code(st.session_state[f"{key}_log"], language="text")

    out = ROOT / "results" / "research_v2"
    placebo_path = out / "placebo_1m.csv"
    if placebo_path.is_file():
        section_header("Negative controls", "Real FVG versus deliberately broken labels")
        frame = pd.read_csv(placebo_path)
        st.dataframe(frame, width="stretch", hide_index=True)
        st.plotly_chart(
            px.bar(frame, x="series", y="touch_rate", color="kind", title="Touch rate under real and placebo constructions"),
            width="stretch",
            config=CHART_CONFIG,
        )

    ablation_path = out / "ablation_1m.csv"
    if ablation_path.is_file():
        section_header("Ablation", "How matching choices move the measured effect")
        frame = pd.read_csv(ablation_path)
        st.dataframe(frame, width="stretch", hide_index=True)
        st.plotly_chart(
            px.bar(frame, x="Variant", y="Difference (pp)", title="FVG-minus-control effect by matching ablation"),
            width="stretch",
            config=CHART_CONFIG,
        )


def power_page() -> None:
    hero(
        "Statistical sensitivity",
        "Power & minimum detectable effect",
        "Estimate how small an effect a given sample can reliably detect, including a design-effect penalty for clustering or dependence.",
        ["MDE", "80/90% power", "Design effect", "Probability + R"],
    )

    c1, c2, c3, c4 = st.columns(4)
    n_fvg = int(c1.number_input("FVG N", min_value=20, value=40000, step=1000))
    n_control = int(c2.number_input("Control N", min_value=20, value=40000, step=1000))
    baseline = float(c3.number_input("Baseline probability", min_value=0.01, max_value=0.99, value=0.90, step=0.01))
    design_effect = float(c4.number_input("Design effect", min_value=1.0, value=1.5, step=0.1))

    cols = st.columns(3)
    cols[0].metric("80% MDE", f"{mde_two_proportion(n_fvg, n_control, baseline=baseline, power=0.80, design_effect=design_effect):.3f} pp")
    cols[1].metric("90% MDE", f"{mde_two_proportion(n_fvg, n_control, baseline=baseline, power=0.90, design_effect=design_effect):.3f} pp")
    ce_n = int(cols[2].number_input("Trade-like N", min_value=10, value=49, step=1))
    std_r = st.number_input("Assumed standard deviation of R", min_value=0.05, value=1.0, step=0.05)
    st.metric("80% detectable mean R", f"{detectable_r_mean(ce_n, std_r=float(std_r), design_effect=design_effect):.3f} R")

    section_header("Scenario table", "How dependence changes detectable probability effects")
    frame = power_scenarios(
        sorted(set([max(20, n_fvg // 4), max(20, n_fvg // 2), n_fvg, n_fvg * 2])),
        baseline=baseline,
        control_ratio=n_control / n_fvg,
    )
    st.dataframe(frame, width="stretch", hide_index=True)
    st.plotly_chart(
        px.line(frame, x="FVG N", y="80% MDE (pp)", color="Design effect", markers=True),
        width="stretch",
        config=CHART_CONFIG,
    )


def hypothesis_registry_page() -> None:
    hero(
        "Confirmatory research discipline",
        "Hypothesis registry",
        "Lock the question, sample window, primary outcome, direction and multiplicity family before inspecting the corresponding result.",
        ["Preregistration", "SHA-256 lock", "Confirmatory vs exploratory", "Research v2"],
    )
    callout(
        "Workflow",
        "Create and lock the hypothesis file first, commit it if the test is meant to be externally auditable, then run the analysis. Editing a locked field changes the hash and fails verification.",
        kind="success",
    )

    example = ROOT / "research_v2" / "hypotheses" / "H001-EXAMPLE.json"
    if example.is_file():
        with st.expander("View committed example preregistration"):
            st.json(json.loads(example.read_text(encoding="utf-8")))

    c1, c2 = st.columns(2)
    hypothesis_id = c1.text_input("Hypothesis ID", value="H002")
    timeframe = c2.text_input("Timeframe", value="1m")
    title = st.text_input("Title", value="Corrected FVG attraction hypothesis")
    question = st.text_area("Question", value="Does the preregistered FVG-minus-control effect differ from zero?")
    dataset_window = st.text_input("Dataset window", value="DECLARE BEFORE RUNNING")
    primary_outcome = st.text_input("Primary outcome", value="Parent-paired near-edge touch probability difference")
    c3, c4 = st.columns(2)
    horizon = c3.text_input("Horizon", value="60 native bars")
    direction = c4.selectbox("Expected direction", ["positive", "negative", "two-sided", "none"])
    statistic = st.text_input("Statistic", value="CME-trade-date clustered bootstrap difference")
    correction_family = st.text_input("Correction family", value="single primary hypothesis")
    filters_text = st.text_area("Filters · one per line", value="minimum FVG width = 1 tick\nfull requested horizon required")

    if st.button("Lock preregistration", type="primary"):
        payload = {
            "hypothesis_id": hypothesis_id.strip(),
            "title": title.strip(),
            "question": question.strip(),
            "dataset_window": dataset_window.strip(),
            "primary_outcome": primary_outcome.strip(),
            "timeframe": timeframe.strip(),
            "filters": [line.strip() for line in filters_text.splitlines() if line.strip()],
            "horizon": horizon.strip(),
            "expected_direction": direction,
            "statistic": statistic.strip(),
            "correction_family": correction_family.strip(),
        }
        target = ROOT / "research_v2" / "hypotheses" / f"{hypothesis_id.strip()}.json"
        try:
            if target.exists():
                raise FileExistsError(f"{target.name} already exists; preregistrations are append-only.")
            locked = register_hypothesis(target, payload)
            st.success(f"Locked {target.relative_to(ROOT)}")
            st.code(locked["lock_hash"], language="text")
        except Exception as exc:
            st.error(str(exc))

    registry = sorted((ROOT / "research_v2" / "hypotheses").glob("*.json"))
    rows = []
    for path in registry:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "File": path.name,
                "Hypothesis": payload.get("hypothesis_id"),
                "Status": payload.get("status"),
                "Hash valid": verify_hypothesis(payload) if payload.get("lock_hash") else "template",
                "Registered": payload.get("registered_utc", "—"),
            })
        except Exception:
            continue
    if rows:
        section_header("Registry", "Tracked hypothesis definitions")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def data_preflight_page() -> None:
    hero(
        "Before the expensive import",
        "Dataset preflight",
        "Inspect archive structure, file size, supported formats, tabular columns and basic compatibility before building the multi-million-row active-contract series.",
        ["Fast", "No dataset mutation", "ZIP inventory", "Schema check"],
    )

    if st.button("Choose files to inspect…", type="primary", width="stretch"):
        chosen = choose_local_files()
        if chosen:
            st.session_state["preflight_paths"] = [str(path) for path in chosen]

    path_text = st.text_area(
        "Or paste one path per line",
        value="\n".join(st.session_state.get("preflight_paths", [])),
        placeholder=r"C:\Users\You\Downloads\GLBX-batch.zip",
    )
    paths = [line.strip() for line in path_text.splitlines() if line.strip()]
    if st.button("Inspect source(s)", disabled=not paths):
        with st.spinner("Inspecting without building the active dataset…"):
            st.session_state["preflight_result"] = inspect_sources(paths)

    results = st.session_state.get("preflight_result")
    if results:
        for item in results:
            with st.container(border=True):
                st.markdown(f"#### {Path(str(item['path'])).name}")
                cols = st.columns(4)
                cols[0].metric("Status", item.get("status", "—"))
                cols[1].metric("Type", item.get("kind", "—"))
                cols[2].metric("Size", f"{int(item.get('bytes', item.get('compressed_bytes', 0))) / 1024**2:,.1f} MB")
                cols[3].metric("Market-data files", item.get("market_data_members", item.get("files", "—")))
                st.json(item)

    if dataset_ready():
        callout(
            "Already prepared",
            "Your active dataset has already passed the full builder validation. Preflight is primarily useful before a new import.",
            kind="success",
        )


def stability_atlas_page(reference: dict) -> None:
    hero(
        "Where the effect lives",
        "Stability atlas",
        "Map the estimated FVG effect across timeframe, chronology and distance so isolated positive cells are visually distinguishable from broad stable structure.",
        ["Timeframe", "Horizon", "Year", "Distance", "Regime"],
    )
    atlas = reference_atlas(reference)

    section_header("Published", "Timeframe × five-bar effect")
    frame = atlas["timeframe"]
    st.plotly_chart(
        px.bar(frame, x="Timeframe", y="Difference (pp)", title="Published five-native-bar matched effect"),
        width="stretch",
        config=CHART_CONFIG,
    )

    left, right = st.columns(2)
    with left:
        chronology = atlas["chronology"]
        st.plotly_chart(
            px.bar(chronology, x="Timeframe", y="Difference (pp)", color="Period", barmode="group", title="Early vs later sample"),
            width="stretch",
            config=CHART_CONFIG,
        )
    with right:
        distance = atlas["distance"]
        st.plotly_chart(
            px.bar(distance, x="Distance bucket", y="Difference (pp)", title="60m effect by starting distance"),
            width="stretch",
            config=CHART_CONFIG,
        )

    local = local_atlas(ROOT / "results")
    section_header(
        "Local",
        "Expanded atlas after reproduction",
        "These dimensions unlock when the corresponding canonical output tables exist locally.",
    )
    if not local:
        st.info("Run the detailed and multi-timeframe canonical suites to unlock the expanded local atlas.")
        return

    if "timeframe_horizon" in local:
        frame = local["timeframe_horizon"]
        if {"timeframe_min", "horizon_bars", "Difference (pp)"}.issubset(frame.columns):
            pivot = frame.pivot_table(index="timeframe_min", columns="horizon_bars", values="Difference (pp)", aggfunc="mean")
            st.plotly_chart(
                px.imshow(pivot, aspect="auto", text_auto=".2f", title="Local effect heatmap · timeframe × horizon"),
                width="stretch",
                config=CHART_CONFIG,
            )
        st.dataframe(frame, width="stretch", hide_index=True)

    for key, title in (
        ("year", "Year-by-year"),
        ("distance", "Distance buckets"),
        ("volatility", "Volatility regimes"),
        ("sensitivity", "Minimum-gap sensitivity"),
    ):
        if key in local:
            st.markdown(f"#### {title}")
            st.dataframe(local[key], width="stretch", hide_index=True)


def economics_page() -> None:
    hero(
        "Statistical ≠ economic",
        "Economic significance",
        "Apply explicit MNQ commission and slippage assumptions to the trade-like CE outputs to see whether a gross statistical pattern is large enough to matter after friction.",
        ["MNQ", "Commission", "Slippage", "Net R"],
    )
    ce_dir = ROOT / "results" / "ce_body"
    candidates = sorted(ce_dir.glob("trades*.pkl"), key=lambda path: path.stat().st_mtime_ns, reverse=True) if ce_dir.is_dir() else []
    if not candidates:
        callout(
            "Trade-level output required",
            "Run the canonical CE/body suite first. Attraction probabilities are not converted into PnL because that would require inventing a trading rule.",
        )
        return

    trades = pd.read_pickle(candidates[0])
    if "mode" in trades.columns:
        trades = trades.loc[trades["mode"].eq("qualifying")].copy()
    timeframes = ["All", *sorted(str(value) for value in trades["timeframe"].dropna().unique())] if "timeframe" in trades.columns else ["All"]
    c1, c2, c3 = st.columns(3)
    timeframe = c1.selectbox("Timeframe", timeframes)
    commission = float(c2.number_input("Commission round turn ($)", min_value=0.0, value=1.24, step=0.10))
    slip = float(c3.number_input("Slippage round turn (ticks)", min_value=0.0, value=2.0, step=0.5))
    if timeframe != "All":
        trades = trades.loc[trades["timeframe"].astype(str).eq(timeframe)]
    d1, d2 = st.columns(2)
    depth_min = float(d1.number_input("Min close depth", min_value=0.0, max_value=1.0, value=0.0, step=0.05))
    depth_max = float(d2.number_input("Max close depth", min_value=0.0, max_value=1.0, value=1.0, step=0.05))
    if "depth" in trades.columns:
        trades = trades.loc[trades["depth"].between(depth_min, depth_max, inclusive="both")]

    summary = economic_summary(
        trades,
        commission_round_turn_usd=commission,
        slippage_ticks_round_turn=slip,
    )
    cols = st.columns(5)
    cols[0].metric("Trades", f"{int(summary['N']):,}")
    cols[1].metric("Gross mean R", f"{summary['gross_mean_R']:+.3f}")
    cols[2].metric("Net mean R", f"{summary['net_mean_R']:+.3f}")
    cols[3].metric("Costs", "$" + f"{summary['cost_total_usd']:,.2f}")
    cols[4].metric("Net PnL · 1 contract", "$" + f"{summary['net_total_usd']:,.2f}")

    scenarios = scenario_table(trades)
    st.dataframe(scenarios, width="stretch", hide_index=True)
    if len(scenarios):
        st.plotly_chart(
            px.line(
                scenarios,
                x="Slippage RT (ticks)",
                y="Net mean R",
                color="Commission RT ($)",
                markers=True,
                title="Net expectancy sensitivity to execution costs",
            ),
            width="stretch",
            config=CHART_CONFIG,
        )


def v1_v2_comparison_page(reference: dict) -> None:
    hero(
        "Self-audit",
        "Published v1 vs corrected v2",
        "Compare the historical published estimate with the corrected research implementation while keeping the old study reproducible and unchanged.",
        ["Method correction", "Transparent revision", "No history rewrite"],
    )
    frame = build_v1_v2_comparison(reference, ROOT / "results" / "research_v2")
    if frame.empty:
        callout(
            "Run Research v2 first",
            "The comparison table populates only from locally generated corrected outputs. No corrected market result is fabricated from the published v1 numbers.",
        )
        return
    st.dataframe(frame, width="stretch", hide_index=True)
    st.plotly_chart(
        px.bar(
            frame.melt(id_vars=["Question", "Correction"], value_vars=["Published v1", "Corrected v2"], var_name="Version", value_name="Estimate"),
            x="Question",
            y="Estimate",
            color="Version",
            barmode="group",
            title="Historical published estimate versus corrected local estimate",
        ),
        width="stretch",
        config=CHART_CONFIG,
    )


def release_provenance_page() -> None:
    hero(
        "Distribution & audit trail",
        "Releases and run provenance",
        "Every serious calculation can leave a machine-readable provenance capsule, while tagged releases build a clean ZIP, standalone report and checksums automatically.",
        ["Run records", "SHA-256", "Release ZIP", "Checksums"],
    )
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").is_file() else "development"
    st.metric("Platform version", version)

    section_header("Releases", "Tagged release automation")
    st.code(
        "git tag v" + version + "\n"
        "git push origin v" + version + "\n\n"
        "GitHub Actions → tests → release ZIP → HTML report → SHA256SUMS.json → GitHub Release",
        language="bash",
    )
    callout(
        "Why tags are deliberate",
        "The repository now contains release automation, but creating a public release remains an explicit versioning action rather than silently tagging every code change.",
    )

    section_header("Run records", "Latest provenance capsules")
    record_dir = ROOT / "results" / "_run_records"
    records = sorted(record_dir.glob("*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)[:30] if record_dir.is_dir() else []
    if not records:
        st.info("Run a canonical study, Research v2 analysis or full reproduction to generate local provenance capsules.")
        return
    rows = []
    for path in records:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append({
                "File": path.name,
                "Kind": payload.get("kind"),
                "Status": payload.get("status"),
                "Elapsed (s)": round(float(payload.get("elapsed_seconds", 0)), 3),
                "Git commit": str(payload.get("git_commit") or "ZIP/no git")[:12],
                "Outputs": len(payload.get("outputs", [])),
            })
        except Exception:
            continue
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    selected = st.selectbox("Inspect capsule", [path.name for path in records])
    selected_path = next(path for path in records if path.name == selected)
    st.json(json.loads(selected_path.read_text(encoding="utf-8")))
