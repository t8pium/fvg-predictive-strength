from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from fvg_research.dashboard_helpers import parse_local_paths
from fvg_research.dataset import dataset_ready

from .catalog import CE_TIMEFRAMES, EXPERIMENTS, ORDER, TF_LABELS
from .charts import headline_metrics, published_charts
from .runtime import (
    LARGE_UPLOAD_WARNING,
    ROOT,
    choose_local_files,
    current_dataset_label,
    dataset_comparison,
    latest_success,
    preparation_args,
    read_dataset_manifest,
    repo_commit,
    result_files,
    run_original,
    run_process,
    save_uploaded_files,
)
from .verification import verification_rows

REFERENCE = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
GITHUB = "https://github.com/t8pium/fvg-predictive-strength"
REPORT = "https://t8pium.github.io/projects/fvg-predictive-strength/"


def dataset_summary() -> None:
    if not dataset_ready():
        st.warning("No local dataset is prepared. Published results remain fully viewable.")
        return
    st.success(f"Local dataset ready · {current_dataset_label()}")
    manifest = read_dataset_manifest()
    if not manifest:
        return
    cols = st.columns(4)
    cols[0].metric("Active bars", f"{int(manifest.get('active_rows', 0)):,}")
    cols[1].metric("Contracts", manifest.get("contracts", "—"))
    cols[2].metric("Start", str(manifest.get("start", "—"))[:10])
    cols[3].metric("End", str(manifest.get("end", "—"))[:10])
    frame = pd.DataFrame(dataset_comparison(REFERENCE))
    if len(frame):
        st.dataframe(frame, width="stretch", hide_index=True)
        if (frame["Status"] == "MATCH").all():
            st.info("Core dataset checks match the frozen published snapshot.")
        else:
            st.info("This dataset differs from the frozen snapshot, so reproduced values may differ.")


def prepare_paths(paths: list[Path], key: str) -> None:
    if not paths:
        st.error("No files were selected.")
        return
    live = st.empty()
    with st.spinner("Building a new versioned active-contract dataset…"):
        rc, log = run_process(preparation_args(paths), live_placeholder=live)
    st.session_state[f"{key}_log"] = log
    st.session_state[f"{key}_rc"] = rc
    if rc == 0 and dataset_ready():
        st.success("Dataset prepared and activated.")
        st.rerun()
    st.error("Preparation failed. Any previously active dataset was left untouched.")


def file_setup(prefix: str) -> None:
    st.markdown("### Recommended: choose files on this computer")
    st.write("The local Windows launcher can pass the real file path directly, avoiding a browser copy of large market-data archives.")
    if os.name == "nt":
        if st.button("Choose market-data file(s)…", type="primary", key=f"{prefix}_choose"):
            selected = choose_local_files()
            if selected:
                st.session_state[f"{prefix}_native_paths"] = [str(p) for p in selected]
        paths = [Path(x) for x in st.session_state.get(f"{prefix}_native_paths", [])]
        if paths:
            st.code("\n".join(map(str, paths)), language="text")
            if st.button("Build dataset from selected file(s)", type="primary", key=f"{prefix}_build_native"):
                prepare_paths(paths, f"{prefix}_native")
    else:
        st.caption("Native file selection is available when launched locally on Windows.")

    with st.expander("Use file/folder path instead"):
        value = st.text_area(
            "One path per line",
            key=f"{prefix}_paths",
            placeholder=r"C:\Users\You\Downloads\GLBX-batch.zip",
        )
        if st.button("Build from path(s)", disabled=not value.strip(), key=f"{prefix}_build_paths"):
            paths = parse_local_paths(value)
            missing = [str(p) for p in paths if not p.exists()]
            if missing:
                st.error("Path not found: " + ", ".join(missing))
            else:
                prepare_paths(paths, f"{prefix}_paths")

    with st.expander("Browser upload fallback"):
        uploaded = st.file_uploader(
            "Upload Databento / OHLCV file(s)",
            type=["dbn", "zst", "parquet", "pq", "csv", "gz", "zip"],
            accept_multiple_files=True,
            key=f"{prefix}_upload",
        )
        if uploaded:
            total = sum(getattr(x, "size", 0) or 0 for x in uploaded)
            st.write(f"{len(uploaded)} file(s) · {total / 1024**2:,.1f} MB")
            if total > LARGE_UPLOAD_WARNING:
                st.warning("Prefer the native picker/path method for a file this large.")
            if st.button("Save upload + build", key=f"{prefix}_build_upload"):
                try:
                    paths = save_uploaded_files(uploaded, prefix)
                except Exception as exc:
                    st.error(f"Could not save upload: {exc}")
                else:
                    prepare_paths(paths, f"{prefix}_upload")

    for suffix in ("native", "paths", "upload"):
        log = st.session_state.get(f"{prefix}_{suffix}_log")
        if log:
            with st.expander(f"{suffix.title()} import log", expanded=st.session_state.get(f"{prefix}_{suffix}_rc") != 0):
                st.code(log, language="text")


def data_page() -> None:
    st.title("Reproduce the research")
    st.write("The published evidence needs no market data. Use this page only to rebuild the input and run the canonical calculations yourself.")
    dataset_summary()
    st.markdown("---")
    file_setup("data")

    with st.expander("Download the published range with your Databento API key"):
        st.write("GLBX.MDP3 · ohlcv-1m · MNQ.FUT · 2020-01-01 through 2026-07-10")
        key = st.text_input("Databento API key", type="password")
        confirm = st.checkbox("I understand historical requests may incur Databento charges.")
        if st.button("Download + build", disabled=not (key and confirm)):
            live = st.empty()
            rc1, log1 = run_process(
                [str(ROOT / "scripts" / "download_databento.py")],
                env={"DATABENTO_API_KEY": key},
                live_placeholder=live,
            )
            if rc1 == 0:
                rc2, log2 = run_process([str(ROOT / "scripts" / "prepare_active_contract.py")], live_placeholder=live)
            else:
                rc2, log2 = 1, ""
            with st.expander("Download/build log", expanded=rc1 != 0 or rc2 != 0):
                st.code(log1 + "\n" + log2, language="text")
            if rc1 == 0 and rc2 == 0:
                st.success("Dataset downloaded and activated.")
                st.rerun()
            st.error("Download or preparation failed.")

    st.markdown("### Software-only verification")
    st.caption("No licensed market data is required.")
    if st.button("Run deterministic self-test"):
        live = st.empty()
        rc, log = run_process(["-m", "unittest", "discover", "-s", "tests", "-v"], live_placeholder=live)
        with st.expander("Self-test log", expanded=rc != 0):
            st.code(log, language="text")
        st.success("Self-test passed.") if rc == 0 else st.error("Self-test failed.")


def runner_config(exp_id: str, exp: dict):
    if exp["runner"] == "detailed":
        return "detailed-1m", None, None, "python scripts/run_original.py detailed-1m"
    if exp["runner"] == "multi":
        tf = st.selectbox("Native timeframe", list(TF_LABELS), format_func=lambda x: TF_LABELS[x], key=f"tf_{exp_id}")
        return "multi-tf", tf, None, f"python scripts/run_original.py multi-tf --tf {tf}"
    if exp["runner"] == "midpoint":
        tf = st.selectbox("Native timeframe", list(TF_LABELS), format_func=lambda x: TF_LABELS[x], key=f"tf_{exp_id}")
        return "midpoint", tf, None, f"python scripts/run_original.py midpoint --tf {tf}"
    if exp["runner"] == "ce":
        tfs = st.multiselect("Timeframes (minutes)", CE_TIMEFRAMES, default=[60, 120, 240], key=f"ce_{exp_id}")
        return "ce-body", None, tfs, "python scripts/run_original.py ce-body --ce-tfs " + ",".join(map(str, tfs))
    mode = st.radio("Validation suite", ["Deep 1m / 60m", "Multi-timeframe / five-bar"], key=f"oos_{exp_id}")
    if mode.startswith("Deep"):
        return "detailed-1m", None, None, "python scripts/run_original.py detailed-1m"
    tf = st.selectbox("Native timeframe", list(TF_LABELS), format_func=lambda x: TF_LABELS[x], key=f"oos_tf_{exp_id}")
    return "multi-tf", tf, None, f"python scripts/run_original.py multi-tf --tf {tf}"


def reproduce_panel(exp_id: str, exp: dict) -> None:
    if not dataset_ready():
        st.info("Published results need no data. Prepare your own licensed data below only for a local reproduction.")
        file_setup(f"exp_{exp_id}")
        return
    dataset_summary()
    study, tf, ce_tfs, command = runner_config(exp_id, exp)
    st.code(command, language="bash")
    if latest_success(study, tf=tf):
        scope = f" at {TF_LABELS.get(tf, str(tf) + 'm')}" if tf is not None else ""
        st.info(f"A successful {study} run{scope} already exists for the current dataset; rerunning is optional.")
    if st.button("Run canonical calculation", type="primary", key=f"run_{exp_id}", disabled=study == "ce-body" and not ce_tfs):
        live = st.empty()
        with st.spinner("Running preserved canonical analysis…"):
            rc, log = run_original(study, tf=tf, ce_tfs=ce_tfs, live_placeholder=live)
        st.session_state[f"log_{exp_id}"] = log
        st.session_state[f"rc_{exp_id}"] = rc
        st.success("Calculation completed.") if rc == 0 else st.error(f"Experiment exited with code {rc}.")
    if st.session_state.get(f"log_{exp_id}"):
        with st.expander("Complete run log", expanded=st.session_state.get(f"rc_{exp_id}") != 0):
            st.code(st.session_state[f"log_{exp_id}"], language="text")

    st.markdown("### Published vs local")
    checks = pd.DataFrame(verification_rows(exp_id, REFERENCE))
    if len(checks):
        st.dataframe(checks, width="stretch", hide_index=True)
    else:
        st.caption("Run the relevant suite to unlock an automatic side-by-side comparison.")


def source_panel(exp: dict) -> None:
    st.write("These are the hash-locked canonical analysis files used for the published study.")
    for relative in exp["sources"]:
        path = ROOT / relative
        st.markdown(f"**{relative}** · [open on GitHub]({GITHUB}/blob/main/{relative})")
        if path.is_file():
            with st.expander(f"View {path.name}"):
                st.code(path.read_text(encoding="utf-8"), language="python")


def result_browser() -> None:
    files = result_files()
    if not files:
        st.info("No local CSV/JSON/PNG outputs yet.")
        return
    labels = [str(p.relative_to(ROOT)) for p in files]
    selected = st.selectbox("Generated output", labels)
    path = ROOT / selected
    if path.suffix == ".csv":
        frame = pd.read_csv(path)
        st.dataframe(frame, width="stretch", height=min(520, 36 * (len(frame) + 1)))
        numeric = list(frame.select_dtypes(include="number").columns)
        if numeric and len(frame) <= 500:
            x = st.selectbox("Chart x", list(frame.columns), key="output_x")
            y = st.selectbox("Chart y", numeric, key="output_y")
            try:
                st.plotly_chart(px.line(frame, x=x, y=y, markers=True), width="stretch")
            except Exception:
                pass
    elif path.suffix == ".json":
        st.json(json.loads(path.read_text(encoding="utf-8")))
    else:
        st.image(str(path), caption=selected)


def home_page() -> None:
    st.markdown("# FVG Predictive Strength — Research Lab")
    st.markdown("**2.3M+ MNQ one-minute bars · 454k+ 1m FVGs · 27 contracts · 2020–2026 · nine experiments.**")
    cols = st.columns(4)
    cols[0].metric("Active 1m bars", f"{REFERENCE['study']['active_1m_rows']:,}")
    cols[1].metric("Detected 1m FVGs", f"{REFERENCE['study']['fvg_1m_count']:,}")
    cols[2].metric("Contracts", REFERENCE["study"]["contracts"])
    cols[3].metric("Experiments", len(EXPERIMENTS))

    st.markdown("## The answer in one sentence")
    st.info("FVGs were revisited frequently, but after matching comparable ordinary zones the incremental attraction was small, strongest shortly after formation, and inconsistent across longer horizons, timeframes, and later data.")

    a, b, c, d = st.columns(4)
    a.markdown("**Raw revisits**\n\n~90.9% touched within 60 minutes.")
    b.markdown("**Matched effect**\n\n60m excess vs controls: about +0.58 pp.")
    c.markdown("**Decay**\n\nThe strongest excess attraction was near formation.")
    d.markdown("**Robustness**\n\nSeveral later/higher-TF effects weakened or reversed.")

    st.markdown("## Two charts that summarize the study")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(published_charts("matched_attraction", REFERENCE)[1][1], width="stretch")
    with right:
        st.plotly_chart(published_charts("oos", REFERENCE)[0][1], width="stretch")

    st.markdown("## Explore the nine experiments")
    items = [(key, EXPERIMENTS[key]) for key in ORDER]
    for start in range(0, len(items), 3):
        columns = st.columns(3)
        for column, (exp_id, exp) in zip(columns, items[start:start + 3]):
            with column:
                with st.container(border=True):
                    st.caption(f"EXPERIMENT {exp['num']}")
                    st.markdown(f"### {exp['title']}")
                    st.write(exp["question"])
                    st.caption(exp["takeaway"])
                    if st.button("Open results →", key=f"open_{exp_id}", width="stretch"):
                        st.session_state["selected"] = exp_id
                        st.session_state["page"] = "Experiment"
                        st.rerun()
    st.markdown("---")
    st.markdown(f"[GitHub repository]({GITHUB}) · [Published report]({REPORT}) · [Scientific audit]({GITHUB}/blob/main/docs/SCIENTIFIC_AUDIT.md)")


def experiment_page(exp_id: str) -> None:
    exp = EXPERIMENTS[exp_id]
    if st.button("← All experiments"):
        st.session_state["page"] = "Home"
        st.rerun()
    st.caption(f"EXPERIMENT {exp['num']} · PUBLISHED REFERENCE")
    st.title(exp["title"])
    st.subheader(exp["question"])
    st.write(exp["summary"])
    metrics = headline_metrics(exp_id, REFERENCE)
    if metrics:
        cols = st.columns(len(metrics))
        for column, (label, value, delta) in zip(cols, metrics):
            column.metric(label, value, delta)
    st.info(exp["takeaway"])

    results, method, reproduce, source = st.tabs(["Results", "Method & limitations", "Reproduce", "Canonical source"])
    with results:
        st.caption("FROZEN PUBLISHED EVIDENCE · reference_results/reference_metrics.json")
        for heading, figure, table in published_charts(exp_id, REFERENCE):
            st.markdown(f"### {heading}")
            st.plotly_chart(figure, width="stretch")
            with st.expander("View values"):
                st.dataframe(table, width="stretch", hide_index=True)
    with method:
        st.markdown("### Exact procedure")
        for number, step in enumerate(exp["method"], 1):
            st.markdown(f"**{number}.** {step}")
        st.markdown("### Important limitation")
        st.warning(exp["limitations"])
        st.markdown(f"[Full specification]({GITHUB}/blob/main/docs/EXPERIMENTS.md) · [Scientific audit]({GITHUB}/blob/main/docs/SCIENTIFIC_AUDIT.md)")
    with reproduce:
        reproduce_panel(exp_id, exp)
    with source:
        source_panel(exp)


def main() -> None:
    st.set_page_config(page_title="FVG Predictive Strength — Research Lab", page_icon="📊", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {max-width: 1280px; padding-top: 1.6rem; padding-bottom: 4rem;}
        [data-testid="stMetricValue"] {font-size: 1.55rem;}
        div[data-testid="stVerticalBlockBorderWrapper"] {background: rgba(18,22,27,.35);}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if "page" not in st.session_state:
        st.session_state["page"] = "Home"

    with st.sidebar:
        st.markdown("## FVG Research Lab")
        st.caption(f"Code {repo_commit()}")
        if st.button("Research overview", width="stretch"):
            st.session_state["page"] = "Home"
            st.rerun()
        if st.button("Reproduce / data setup", width="stretch"):
            st.session_state["page"] = "Data Setup"
            st.rerun()
        if st.button("Local outputs", width="stretch"):
            st.session_state["page"] = "Generated Outputs"
            st.rerun()
        st.markdown("---")
        st.caption("Local dataset")
        st.write("✅ ready" if dataset_ready() else "— not prepared")
        if dataset_ready():
            st.caption(current_dataset_label())
        st.caption("Published sample")
        st.write("MNQ · 2020–2026")
        st.markdown(f"[GitHub source ↗]({GITHUB})")

    page = st.session_state["page"]
    if page == "Data Setup":
        data_page()
    elif page == "Generated Outputs":
        st.title("Local outputs")
        st.write("These files were generated on this machine and are separate from the frozen published evidence.")
        result_browser()
    elif page == "Experiment" and st.session_state.get("selected") in EXPERIMENTS:
        experiment_page(st.session_state["selected"])
    else:
        home_page()
