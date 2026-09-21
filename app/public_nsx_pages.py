from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fvg_research.public_nsx import (
    PUBLIC_ASSET_URL,
    PUBLIC_AUDIT,
    PUBLIC_DIR,
    PUBLIC_MANIFEST,
    PUBLIC_PARQUET,
    PUBLIC_PICKLE,
    PUBLIC_RESULTS,
    public_audit,
    public_manifest,
    public_ready,
    public_result_paths,
    public_result_payload,
    query_public_ohlcv,
    resample_ohlcv,
)
from fvg_research.public_summary import build_public_summary

from .catalog import EXPERIMENTS, EXPERIMENT_TAGS, ORDER, TF_LABELS
from .runtime import (
    LARGE_UPLOAD_WARNING,
    ROOT,
    choose_local_files,
    run_process,
    save_uploaded_files,
)
from .ui import callout, hero, info_card, section_header

CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "scrollZoom": False,
}


def _fmt_date(value: object) -> str:
    text = str(value or "")
    return text[:10] if text else "—"


def _dataset_status_cards() -> None:
    manifest = public_manifest()
    audit = public_audit()
    if not public_ready():
        callout(
            "Public dataset not installed yet",
            "The code path is ready. Install the GitHub Release asset or point the lab at NSXUSD_M1_ALL.csv once; after that every public-replication page uses the local Parquet/pickle directly.",
            kind="warning",
        )
        return

    cols = st.columns(5)
    cols[0].metric("Rows", f"{int(manifest.get('rows', 0)):,}")
    cols[1].metric("Start", _fmt_date(manifest.get("start_utc")))
    cols[2].metric("End", _fmt_date(manifest.get("end_utc")))
    cols[3].metric("Non-zero volume", f"{int(audit.get('nonzero_volume_rows', 0)):,}")
    cols[4].metric("Dataset", "NSX/USD")
    callout(
        "Ready",
        "This is the free long-history Nasdaq-100 index-style quote feed. It is intentionally kept separate from the published CME MNQ evidence.",
        kind="success",
    )


def _prepare_from_paths(paths: list[Path], key: str) -> None:
    if not paths:
        st.error("No file selected.")
        return
    if len(paths) != 1:
        st.error("Select the merged NSXUSD_M1_ALL.csv file.")
        return
    live = st.empty()
    rc, log = run_process(
        [
            str(ROOT / "scripts" / "prepare_histdata_nsx.py"),
            "--input",
            str(paths[0]),
            "--output",
            str(PUBLIC_DIR),
        ],
        live_placeholder=live,
    )
    st.session_state[f"{key}_log"] = log
    st.session_state[f"{key}_rc"] = rc
    if rc == 0:
        st.success("Public Nasdaq dataset audited and prepared.")
        st.rerun()
    st.error("Preparation failed. See the log below.")


def public_nsx_setup_page() -> None:
    hero(
        "Free long-history replication",
        "Public Nasdaq dataset",
        "Install or prepare the 2010–2026 HistData NSX/USD 1-minute history once. The Research Lab then uses it as a first-class public replication dataset.",
        ["5M+ 1m bars", "2010–2026", "Free source", "No Databento required"],
    )
    callout(
        "Scientific boundary",
        "NSX/USD is a Nasdaq-100 index-style quote feed, not CME NQ/MNQ futures. Price-pattern questions can be replicated; futures volume, roll, tick-execution and slippage claims cannot.",
        kind="warning",
    )

    section_header("Status", "Current public dataset")
    _dataset_status_cards()
    if public_ready():
        audit = public_audit()
        with st.expander("Full dataset audit"):
            st.json(audit)

    section_header(
        "Option A",
        "Install the GitHub Release dataset",
        "Once the public-data release asset is uploaded, this becomes the one-click route for every user.",
    )
    st.code(PUBLIC_ASSET_URL, language="text")
    if st.button("Download + install public dataset", type="primary", width="stretch"):
        live = st.empty()
        rc, log = run_process(
            [str(ROOT / "scripts" / "install_public_nsx.py")],
            live_placeholder=live,
        )
        st.session_state["public_install_log"] = log
        st.session_state["public_install_rc"] = rc
        if rc == 0:
            st.success("Public dataset installed.")
            st.rerun()
        st.error("Release asset is not available yet or installation failed.")

    if st.session_state.get("public_install_log"):
        with st.expander(
            "Install log",
            expanded=st.session_state.get("public_install_rc") != 0,
        ):
            st.code(st.session_state["public_install_log"], language="text")

    section_header(
        "Option B",
        "Prepare the CSV you already downloaded",
        "This performs the full audit, fixes the source's fixed-EST clock correctly, and writes Parquet + schema-compatible pickle files.",
    )

    if st.button("Choose NSXUSD_M1_ALL.csv…", width="stretch"):
        selected = choose_local_files()
        if selected:
            st.session_state["public_native_paths"] = [str(path) for path in selected]
    paths = [Path(value) for value in st.session_state.get("public_native_paths", [])]
    if paths:
        st.code("\n".join(map(str, paths)), language="text")
        if st.button("Audit + prepare selected CSV", type="primary", width="stretch"):
            _prepare_from_paths(paths, "public_native")

    with st.expander("Alternative — paste a local path"):
        value = st.text_input(
            "CSV path",
            placeholder=r"C:\Users\You\Downloads\NSXUSD_M1_ALL.csv",
            key="public_csv_path",
        )
        if st.button("Prepare from path", disabled=not value.strip(), width="stretch"):
            path = Path(value.strip().strip('"')).expanduser().resolve()
            if not path.is_file():
                st.error("File not found.")
            else:
                _prepare_from_paths([path], "public_path")

    with st.expander("Fallback — browser upload"):
        uploaded = st.file_uploader(
            "Upload NSXUSD_M1_ALL.csv",
            type=["csv"],
            key="public_csv_upload",
        )
        if uploaded:
            size = getattr(uploaded, "size", 0) or 0
            st.caption(f"{size / 1024**2:,.1f} MB")
            if size > LARGE_UPLOAD_WARNING:
                st.warning("For very large files, the local picker/path route is safer.")
            if st.button("Save upload + prepare", width="stretch"):
                paths = save_uploaded_files([uploaded], "public_nsx")
                _prepare_from_paths(paths, "public_upload")

    for key in ("public_native", "public_path", "public_upload"):
        if st.session_state.get(f"{key}_log"):
            with st.expander(
                f"{key.replace('_', ' ').title()} log",
                expanded=st.session_state.get(f"{key}_rc") != 0,
            ):
                st.code(st.session_state[f"{key}_log"], language="text")


def _detect_slice_fvgs(frame: pd.DataFrame) -> pd.DataFrame:
    if len(frame) < 3:
        return pd.DataFrame()
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    bull = np.zeros(len(frame), dtype=bool)
    bear = np.zeros(len(frame), dtype=bool)
    bull[2:] = low[2:] > high[:-2]
    bear[2:] = high[2:] < low[:-2]
    idx = np.flatnonzero(bull | bear)
    if not len(idx):
        return pd.DataFrame()
    direction = np.where(bull[idx], "bullish", "bearish")
    lower = np.where(bull[idx], high[idx - 2], high[idx])
    upper = np.where(bull[idx], low[idx], low[idx - 2])
    return pd.DataFrame(
        {
            "row": idx,
            "timestamp": frame["ts_event"].iloc[idx].to_numpy(),
            "direction": direction,
            "lower": lower,
            "upper": upper,
            "width": upper - lower,
        }
    )


def public_nsx_explorer_page() -> None:
    hero(
        "Live public data",
        "Nasdaq data & FVG explorer",
        "Browse the actual public price history, resample it, overlay mechanically detected FVGs, and inspect the observations that feed the replication.",
        ["Candlesticks", "FVG overlays", "Date filter", "1m → 4H"],
    )
    _dataset_status_cards()
    if not public_ready():
        if st.button("Open public-data setup →", type="primary"):
            st.session_state["page"] = "Public Nasdaq Setup"
            st.rerun()
        return

    manifest = public_manifest()
    start_default = pd.Timestamp(manifest["start_utc"]).date()
    end_max = pd.Timestamp(manifest["end_utc"]).date()
    recent_start = max(start_default, end_max - timedelta(days=7))

    controls = st.columns(4)
    start = controls[0].date_input(
        "Start date",
        value=recent_start,
        min_value=start_default,
        max_value=end_max,
        key="public_explorer_start",
    )
    end = controls[1].date_input(
        "End date",
        value=end_max,
        min_value=start_default,
        max_value=end_max,
        key="public_explorer_end",
    )
    tf = controls[2].selectbox(
        "Timeframe",
        [1, 5, 15, 60, 240],
        format_func=lambda value: TF_LABELS[value],
        key="public_explorer_tf",
    )
    max_rows = controls[3].selectbox(
        "Max source rows",
        [25_000, 100_000, 250_000],
        index=1,
        format_func=lambda value: f"{value:,}",
    )

    if end < start:
        st.error("End date must be on or after start date.")
        return

    end_exclusive = end + timedelta(days=1)
    frame = query_public_ohlcv(
        f"{start.isoformat()}T00:00:00Z",
        f"{end_exclusive.isoformat()}T00:00:00Z",
        max_rows=max_rows,
    )
    if frame.empty:
        st.info("No rows in that date range.")
        return

    clipped = len(frame) >= max_rows
    bars = resample_ohlcv(frame, tf)
    events = _detect_slice_fvgs(bars)

    cols = st.columns(4)
    cols[0].metric("Source rows loaded", f"{len(frame):,}")
    cols[1].metric("Displayed bars", f"{len(bars):,}")
    cols[2].metric("FVGs in slice", f"{len(events):,}")
    cols[3].metric("Range clipped", "Yes" if clipped else "No")
    if clipped:
        st.warning("The source-row cap was reached. Narrow the date range for a complete visual slice.")

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=bars["ts_event"],
                open=bars["open"],
                high=bars["high"],
                low=bars["low"],
                close=bars["close"],
                name="NSX/USD",
            )
        ]
    )
    for _, event in events.tail(150).iterrows():
        fig.add_shape(
            type="rect",
            x0=event["timestamp"],
            x1=bars["ts_event"].iloc[-1],
            y0=event["lower"],
            y1=event["upper"],
            opacity=0.10,
            line_width=1,
        )
    fig.update_layout(
        title=f"NSX/USD · {TF_LABELS[tf]} · mechanically detected FVGs",
        xaxis_rangeslider_visible=False,
        height=720,
    )
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

    section_header(
        "Detected events",
        "FVGs visible in this exact chart slice",
        "These are calculated from completed candles in the displayed resampled series; they are not pre-drawn annotations.",
    )
    if len(events):
        view = events.tail(500).copy()
        view["timestamp"] = pd.to_datetime(view["timestamp"], utc=True)
        st.dataframe(view, width="stretch", hide_index=True)
    else:
        st.caption("No FVGs in this slice.")


def _run_public_experiment(exp_id: str, tf: int, ce_tfs: list[int]) -> tuple[int, str]:
    runner = EXPERIMENTS[exp_id]["runner"]
    if runner in ("detailed", "oos") and exp_id != "oos":
        study = "detailed-1m"
    elif runner == "multi" or exp_id == "oos":
        study = "multi-tf"
    elif runner == "midpoint":
        study = "midpoint"
    elif runner == "ce":
        study = "ce-body"
    else:
        study = "detailed-1m"

    args = [
        str(ROOT / "scripts" / "run_original.py"),
        study,
        "--data",
        str(PUBLIC_PICKLE),
        "--results-root",
        str(PUBLIC_RESULTS),
    ]
    if study in ("multi-tf", "midpoint"):
        args += ["--tf", str(tf)]
    if study == "ce-body":
        args += ["--ce-tfs", ",".join(map(str, ce_tfs))]
    live = st.empty()
    return run_process(args, live_placeholder=live)


def public_nsx_experiment_page() -> None:
    hero(
        "Same hypotheses · longer free history",
        "Public Nasdaq experiment lab",
        "Run the same nine reader-facing FVG experiment families against the public 2010–2026 NSX/USD history and inspect the generated tables immediately.",
        ["9 experiment families", "Live reruns", "Public data", "Separate from MNQ"],
    )
    callout(
        "Interpretation rule",
        "These are replication/discovery results on an index-style quote feed. They do not overwrite the frozen MNQ results and should not be described as NQ/MNQ futures execution evidence.",
        kind="warning",
    )
    _dataset_status_cards()
    if not public_ready():
        return

    labels = {key: f"{EXPERIMENTS[key]['num']} · {EXPERIMENTS[key]['title']}" for key in ORDER}
    exp_id = st.selectbox(
        "Experiment",
        ORDER,
        format_func=lambda key: labels[key],
        key="public_exp_id",
    )
    exp = EXPERIMENTS[exp_id]
    st.markdown(f"### {exp['title']}")
    st.caption(" · ".join(EXPERIMENT_TAGS[exp_id]))
    st.write(exp["question"])
    callout("Original experiment logic", exp["summary"])

    runner = exp["runner"]
    tf = 1
    ce_tfs = [60, 240]
    if runner in ("multi", "midpoint") or exp_id == "oos":
        tf = st.selectbox(
            "Native timeframe",
            list(TF_LABELS),
            format_func=lambda value: TF_LABELS[value],
            key=f"public_tf_{exp_id}",
        )
    elif runner == "ce":
        ce_tfs = st.multiselect(
            "CE signal timeframes",
            [1, 2, 3, 5, 10, 15, 30, 60, 120, 240, 360, 480, 720, 1440],
            default=[60, 240],
            key="public_ce_tfs",
        )

    if st.button("Run this experiment on public Nasdaq data", type="primary", width="stretch"):
        rc, log = _run_public_experiment(exp_id, tf, ce_tfs)
        st.session_state["public_exp_log"] = log
        st.session_state["public_exp_rc"] = rc
        if rc == 0:
            run_process(
                [str(ROOT / "scripts" / "summarize_public_nsx.py")],
                live_placeholder=None,
            )
            st.success("Experiment completed.")
        else:
            st.error(f"Experiment exited with code {rc}.")

    if st.session_state.get("public_exp_log"):
        with st.expander("Run log", expanded=st.session_state.get("public_exp_rc") != 0):
            st.code(st.session_state["public_exp_log"], language="text")

    paths = public_result_paths(exp_id, tf=tf)
    section_header(
        "Outputs",
        "Current public-replication results",
        "These files are generated from the installed NSX/USD dataset on this machine.",
    )
    if not paths:
        st.caption("No output for this experiment/timeframe yet.")
        return

    for path in paths:
        with st.expander(str(path.relative_to(ROOT)), expanded=len(paths) == 1):
            payload = public_result_payload(path)
            if isinstance(payload, pd.DataFrame):
                st.dataframe(payload, width="stretch", hide_index=True)
                numeric = list(payload.select_dtypes(include="number").columns)
                if 1 <= len(numeric) and len(payload) > 1 and len(payload) <= 500:
                    x = payload.columns[0]
                    y = numeric[-1]
                    try:
                        st.plotly_chart(
                            px.line(payload, x=x, y=y, markers=True, title=path.name),
                            width="stretch",
                            config=CHART_CONFIG,
                        )
                    except Exception:
                        pass
            else:
                st.json(payload)


def public_nsx_reproduction_page() -> None:
    hero(
        "One-click long-history replication",
        "Reproduce all FVG experiments on public Nasdaq data",
        "Run the complete preserved experiment family against the free NSX/USD history. Results are written under results/public_nsx and never overwrite the published MNQ evidence.",
        ["12 stages", "2010–2026", "Resume-safe", "Public replication"],
    )
    _dataset_status_cards()
    if not public_ready():
        return

    stages = pd.DataFrame(
        [
            ("01", "Detailed 1m", "raw fill · deep matched controls · regimes · chronology"),
            ("02–06", "Multi-timeframe", "1m · 5m · 15m · 1H · 4H"),
            ("07–11", "Midpoint", "1m · 5m · 15m · 1H · 4H"),
            ("12", "CE/body execution study", "1m through 1D"),
        ],
        columns=["Stage", "Suite", "Feeds"],
    )
    st.dataframe(stages, width="stretch", hide_index=True)

    force = st.checkbox("Force rerun completed stages")
    skip_ce = st.checkbox("Skip the heaviest CE/body stage for now")
    if st.button("Start / resume complete public replication", type="primary", width="stretch"):
        args = [str(ROOT / "scripts" / "reproduce_public_nsx.py")]
        if force:
            args.append("--force")
        if skip_ce:
            args.append("--skip-ce")
        live = st.empty()
        rc, log = run_process(args, live_placeholder=live)
        st.session_state["public_full_log"] = log
        st.session_state["public_full_rc"] = rc
        if rc == 0:
            st.success("Public replication completed.")
        else:
            st.error("Public replication stopped on a failed stage.")

    if st.session_state.get("public_full_log"):
        with st.expander("Full replication log", expanded=st.session_state.get("public_full_rc") != 0):
            st.code(st.session_state["public_full_log"], language="text")

    state = PUBLIC_RESULTS / "_full_reproduction" / "state.json"
    if state.is_file():
        payload = json.loads(state.read_text(encoding="utf-8"))
        section_header("Progress", "Latest stage state")
        st.dataframe(pd.DataFrame(payload.get("stages", [])), width="stretch", hide_index=True)

    summary_path = PUBLIC_RESULTS / "public_summary.json"
    if summary_path.is_file():
        section_header(
            "Machine-readable result",
            "Public replication summary",
            "This is rebuilt from the generated experiment outputs rather than hand-entered.",
        )
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        st.json(payload)


def public_nsx_overview_page() -> None:
    hero(
        "Public replication track",
        "FVG Predictive Strength · Nasdaq 2010–2026",
        "A second, fully public research track designed to repeat the FVG falsification process on roughly sixteen years of freely obtainable Nasdaq-100 price history.",
        ["NSX/USD", "2010–2026", "5M+ 1m bars", "Same 9 hypotheses"],
    )
    callout(
        "Why this exists",
        "The original MNQ study has higher futures-specific fidelity, but its licensed history cannot be redistributed. The public track trades some market fidelity for much longer history and full accessibility.",
    )
    _dataset_status_cards()

    cols = st.columns(4)
    with cols[0]:
        info_card("Longer history", "Dot-com aftermath, GFC era, QE, low-volatility, COVID, tightening and the AI-led regime all fit inside one accessible series.")
    with cols[1]:
        info_card("Same questions", "Raw fill, matched attraction, age decay, continuation, retest reaction, midpoint/CE, body acceptance, controls and chronology.")
    with cols[2]:
        info_card("Live inspection", "Browse actual candles and dynamically overlay FVGs on any date slice before looking at aggregate statistics.")
    with cols[3]:
        info_card("Separate evidence", "Public results never replace the frozen MNQ study; the two datasets become a robustness comparison.")

    section_header(
        "Workflow",
        "From public data to visible experiments",
        "A reader can install the dataset once, inspect individual observations, run one experiment, or reproduce the entire suite.",
    )
    flow = [
        ("1 · Install", "GitHub Release asset or your merged HistData CSV."),
        ("2 · Audit", "Full timestamp/OHLC integrity scan and fixed-EST → UTC normalization."),
        ("3 · Explore", "Interactive candlesticks + mechanically detected FVG zones."),
        ("4 · Reproduce", "Run the same nine experiment families and inspect output tables immediately."),
    ]
    columns = st.columns(4)
    for column, (title, body) in zip(columns, flow):
        with column:
            info_card(title, body)

    left, middle, right = st.columns(3)
    with left:
        if st.button("Set up public data →", type="primary", width="stretch"):
            st.session_state["page"] = "Public Nasdaq Setup"
            st.rerun()
    with middle:
        if st.button("Open live data explorer →", width="stretch"):
            st.session_state["page"] = "Public Nasdaq Explorer"
            st.rerun()
    with right:
        if st.button("Open experiment lab →", width="stretch"):
            st.session_state["page"] = "Public Nasdaq Experiments"
            st.rerun()

    summary_path = PUBLIC_RESULTS / "public_summary.json"
    if summary_path.is_file():
        section_header(
            "Latest local run",
            "Replication output is available",
            "The exact values below are generated locally from the installed public dataset.",
        )
        payload = build_public_summary(PUBLIC_RESULTS)
        cols = st.columns(3)
        cols[0].metric(
            "Experiment families with output",
            f"{payload.get('experiment_families_with_outputs', 0)}/9",
        )
        detailed = payload.get("experiments", {}).get("raw_fill", {}).get("summary", {})
        cols[1].metric("Detected 1m FVGs", f"{int(detailed.get('fvg_count', 0)):,}")
        cols[2].metric(
            "Raw 60m touch",
            f"{float(detailed.get('raw_touch_60', float('nan'))) * 100:.2f}%"
            if detailed.get("raw_touch_60") is not None else "—",
        )
