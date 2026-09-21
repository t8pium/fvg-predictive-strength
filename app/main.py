from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from fvg_research.dashboard_helpers import parse_local_paths
from fvg_research.dataset import dataset_ready
from fvg_research.diagnostics import (
    ce_band_intervals,
    chronological_shift,
    local_detailed_diagnostics,
    matched_effect_profile,
    raw_fill_intervals,
)
from fvg_research.explainers import experiment_svg, research_flow_svg
from fvg_research.report import build_report

from .catalog import CE_TIMEFRAMES, EXPERIMENTS, EXPERIMENT_TAGS, ORDER, TF_LABELS
from .charts import headline_metrics, published_charts
from .provenance import EXPERIMENT_PROVENANCE
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
from .ui import (
    apply_theme,
    callout,
    hero,
    info_card,
    method_steps,
    section_header,
    sidebar_status,
)
from .verification import verification_rows
from .v4_pages import (
    data_preflight_page,
    economics_page,
    event_explorer_page,
    hypothesis_registry_page,
    power_page,
    release_provenance_page,
    scientific_stress_page,
    stability_atlas_page,
    v1_v2_comparison_page,
)
from .public_nsx_pages import (
    public_nsx_experiment_page,
    public_nsx_explorer_page,
    public_nsx_overview_page,
    public_nsx_reproduction_page,
    public_nsx_setup_page,
)

REFERENCE = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
PROVENANCE = json.loads((ROOT / "reference_results" / "manifest.json").read_text(encoding="utf-8"))
TEMPORAL = json.loads((ROOT / "research_v2" / "findings" / "temporal_attraction_reaction_2026-09-20.json").read_text(encoding="utf-8"))
GITHUB = "https://github.com/t8pium/fvg-predictive-strength"
REPORT = "https://t8pium.github.io/projects/fvg-predictive-strength/"
STATIC_REPORT = "https://t8pium.github.io/fvg-predictive-strength/"
CHART_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "scrollZoom": False,
}

GLOSSARY = [
    ("FVG", "A three-candle Fair Value Gap. The study treats it as a mechanically defined price zone, not as an assumed trading signal."),
    ("Matched control", "An ordinary non-FVG zone constructed to resemble a real FVG in distance, width and broad market state."),
    ("pp", "Percentage points. A +0.58 pp difference means 90.86% versus 90.28%, not a 0.58% relative increase."),
    ("ATR", "Average True Range. Distances and returns are often normalized by ATR so different volatility regimes are comparable."),
    ("CE / midpoint", "Consequent Encroachment: the exact 50% level of an FVG."),
    ("Chronological split", "An early-versus-late sample check. It is more informative than a random shuffle for non-stationary market data."),
]


def dataset_summary() -> None:
    if not dataset_ready():
        callout(
            "No local dataset yet",
            "That is fine for reading the study. Every published chart and result remains available without licensed market data.",
        )
        return

    manifest = read_dataset_manifest()
    callout("Local dataset ready", current_dataset_label(), kind="success")
    if not manifest:
        return

    cols = st.columns(4)
    cols[0].metric("Active bars", f"{int(manifest.get('active_rows', 0)):,}")
    cols[1].metric("Contracts", manifest.get("contracts", "—"))
    cols[2].metric("Start", str(manifest.get("start", "—"))[:10])
    cols[3].metric("End", str(manifest.get("end", "—"))[:10])

    comparison = pd.DataFrame(dataset_comparison(REFERENCE))
    if len(comparison):
        st.dataframe(comparison, width="stretch", hide_index=True)
        if (comparison["Status"] == "MATCH").all():
            callout(
                "Snapshot check passed",
                "The core dataset checks match the frozen published snapshot.",
                kind="success",
            )
        else:
            callout(
                "Snapshot differs",
                "Your dataset is usable, but reproduced values can differ from the published reference because the input is not identical.",
                kind="warning",
            )


def prepare_paths(paths: list[Path], key: str) -> None:
    if not paths:
        st.error("No files were selected.")
        return

    live = st.empty()
    with st.spinner("Building the active-contract dataset…"):
        rc, log = run_process(preparation_args(paths), live_placeholder=live)

    st.session_state[f"{key}_log"] = log
    st.session_state[f"{key}_rc"] = rc

    if rc == 0 and dataset_ready():
        st.success("Dataset prepared and activated.")
        st.rerun()

    st.error("Preparation failed. Any previously active dataset was left untouched.")


def file_setup(prefix: str) -> None:
    section_header(
        "Step 1 · Data",
        "Choose your market-data source",
        "For a local Windows launch, selecting the file directly is the simplest and fastest route. Browser upload is only a fallback.",
    )

    with st.container(border=True):
        st.markdown("#### Recommended — choose files on this computer")
        st.caption("Uses the real local file path. Large archives are not copied through the browser.")
        if os.name == "nt":
            if st.button("Choose market-data file(s)…", type="primary", key=f"{prefix}_choose", width="stretch"):
                selected = choose_local_files()
                if selected:
                    st.session_state[f"{prefix}_native_paths"] = [str(path) for path in selected]

            paths = [Path(value) for value in st.session_state.get(f"{prefix}_native_paths", [])]
            if paths:
                st.markdown("**Selected**")
                st.code("\n".join(map(str, paths)), language="text")
                if st.button(
                    "Build dataset from selected file(s)",
                    type="primary",
                    key=f"{prefix}_build_native",
                    width="stretch",
                ):
                    prepare_paths(paths, f"{prefix}_native")
        else:
            st.info("Native file selection is available when the Research Lab is launched locally on Windows.")

    left, right = st.columns(2)
    with left:
        with st.expander("Alternative — paste a file or folder path"):
            value = st.text_area(
                "One path per line",
                key=f"{prefix}_paths",
                placeholder=r"C:\Users\You\Downloads\GLBX-batch.zip",
                help="Paths are passed as arguments to Python, never to a shell.",
            )
            if st.button("Build from path(s)", disabled=not value.strip(), key=f"{prefix}_build_paths", width="stretch"):
                paths = parse_local_paths(value)
                missing = [str(path) for path in paths if not path.exists()]
                if missing:
                    st.error("Path not found: " + ", ".join(missing))
                else:
                    prepare_paths(paths, f"{prefix}_paths")

    with right:
        with st.expander("Fallback — browser upload"):
            uploaded = st.file_uploader(
                "Upload Databento / OHLCV file(s)",
                type=["dbn", "zst", "parquet", "pq", "csv", "gz", "zip"],
                accept_multiple_files=True,
                key=f"{prefix}_upload",
            )
            if uploaded:
                total = sum(getattr(item, "size", 0) or 0 for item in uploaded)
                st.caption(f"{len(uploaded)} file(s) · {total / 1024**2:,.1f} MB")
                if total > LARGE_UPLOAD_WARNING:
                    st.warning("For a file this large, the native picker or direct path is safer and faster.")
                if st.button("Save upload + build", key=f"{prefix}_build_upload", width="stretch"):
                    try:
                        paths = save_uploaded_files(uploaded, prefix)
                    except Exception as exc:
                        st.error(f"Could not save upload: {exc}")
                    else:
                        prepare_paths(paths, f"{prefix}_upload")

    for suffix in ("native", "paths", "upload"):
        log = st.session_state.get(f"{prefix}_{suffix}_log")
        if log:
            with st.expander(
                f"{suffix.title()} import log",
                expanded=st.session_state.get(f"{prefix}_{suffix}_rc") != 0,
            ):
                st.code(log, language="text")


def data_page() -> None:
    hero(
        "Independent reproduction",
        "Reproduce the research",
        "Published results are already available without market data. This workflow is only for readers who want to rebuild the input and rerun the preserved calculations themselves.",
        ["Optional", "Licensed data", "Canonical code", "Published comparison"],
    )

    section_header(
        "Workflow",
        "Four steps from raw data to verification",
        "The local lab separates data preparation from the research calculations so it is always clear what has been validated.",
    )
    cols = st.columns(4)
    with cols[0]:
        info_card("1 · Choose data", "Select local Databento/OHLCV files or download the published range.")
    with cols[1]:
        info_card("2 · Validate", "Build the active MNQ series and compare its core checks with the published snapshot.")
    with cols[2]:
        info_card("3 · Run", "Execute one of the four hash-locked canonical computational suites.")
    with cols[3]:
        info_card("4 · Compare", "See your local values beside the frozen published reference.")

    section_header("Current state", "Dataset status")
    dataset_summary()
    file_setup("data")

    section_header(
        "Alternative source",
        "Download the published range with Databento",
        "Use your own API key to request the same dataset, schema and parent symbol. Historical vendor requests may be billable.",
    )
    with st.expander("Databento API download"):
        st.code(
            "Dataset: GLBX.MDP3\nSchema: ohlcv-1m\nSymbol: MNQ.FUT\nRange: 2020-01-01 → 2026-07-11 (end exclusive)",
            language="text",
        )
        key = st.text_input("Databento API key", type="password")
        confirm = st.checkbox("I understand historical requests may incur Databento charges.")
        if st.button("Download + build", disabled=not (key and confirm), type="primary"):
            live = st.empty()
            rc1, log1 = run_process(
                [str(ROOT / "scripts" / "download_databento.py")],
                env={"DATABENTO_API_KEY": key},
                live_placeholder=live,
            )
            if rc1 == 0:
                rc2, log2 = run_process(
                    [str(ROOT / "scripts" / "prepare_active_contract.py")],
                    live_placeholder=live,
                )
            else:
                rc2, log2 = 1, ""
            with st.expander("Download/build log", expanded=rc1 != 0 or rc2 != 0):
                st.code(log1 + "\n" + log2, language="text")
            if rc1 == 0 and rc2 == 0:
                st.success("Dataset downloaded and activated.")
                st.rerun()
            st.error("Download or preparation failed.")

    section_header(
        "No market data required",
        "Verify the software only",
        "This deterministic suite checks the mechanics, paths, dashboard routes and reproducibility safeguards without using licensed MNQ history.",
    )
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
        tf = st.selectbox(
            "Native timeframe",
            list(TF_LABELS),
            format_func=lambda value: TF_LABELS[value],
            key=f"tf_{exp_id}",
        )
        return "multi-tf", tf, None, f"python scripts/run_original.py multi-tf --tf {tf}"

    if exp["runner"] == "midpoint":
        tf = st.selectbox(
            "Native timeframe",
            list(TF_LABELS),
            format_func=lambda value: TF_LABELS[value],
            key=f"tf_{exp_id}",
        )
        return "midpoint", tf, None, f"python scripts/run_original.py midpoint --tf {tf}"

    if exp["runner"] == "ce":
        tfs = st.multiselect(
            "Timeframes to test (minutes)",
            CE_TIMEFRAMES,
            default=[60, 120, 240],
            key=f"ce_{exp_id}",
        )
        command = "python scripts/run_original.py ce-body --ce-tfs " + ",".join(map(str, tfs))
        return "ce-body", None, tfs, command

    mode = st.radio(
        "Validation suite",
        ["Deep 1m / 60m", "Multi-timeframe / five-bar"],
        key=f"oos_{exp_id}",
    )
    if mode.startswith("Deep"):
        return "detailed-1m", None, None, "python scripts/run_original.py detailed-1m"

    tf = st.selectbox(
        "Native timeframe",
        list(TF_LABELS),
        format_func=lambda value: TF_LABELS[value],
        key=f"oos_tf_{exp_id}",
    )
    return "multi-tf", tf, None, f"python scripts/run_original.py multi-tf --tf {tf}"


def reproduce_panel(exp_id: str, exp: dict) -> None:
    callout(
        "Reproduction is optional",
        "The published result above is frozen evidence. This section is only for independently rebuilding it on your own machine.",
    )

    if not dataset_ready():
        file_setup(f"exp_{exp_id}")
        return

    section_header("Input", "Current local dataset")
    dataset_summary()

    section_header(
        "Calculation",
        "Choose and run the canonical suite",
        "One computational suite may feed several experiment pages. If a matching successful run already exists for this dataset, rerunning is optional.",
    )
    study, tf, ce_tfs, command = runner_config(exp_id, exp)
    st.code(command, language="bash")

    cached = latest_success(study, tf=tf)
    if cached:
        scope = f" at {TF_LABELS.get(tf, str(tf) + 'm')}" if tf is not None else ""
        callout(
            "Existing local run found",
            f"A successful {study} run{scope} already exists for the current dataset.",
            kind="success",
        )

    if st.button(
        "Run canonical calculation",
        type="primary",
        key=f"run_{exp_id}",
        disabled=study == "ce-body" and not ce_tfs,
        width="stretch",
    ):
        live = st.empty()
        with st.spinner("Running preserved canonical analysis…"):
            rc, log = run_original(study, tf=tf, ce_tfs=ce_tfs, live_placeholder=live)
        st.session_state[f"log_{exp_id}"] = log
        st.session_state[f"rc_{exp_id}"] = rc
        st.success("Calculation completed.") if rc == 0 else st.error(f"Experiment exited with code {rc}.")

    if st.session_state.get(f"log_{exp_id}"):
        with st.expander("Complete run log", expanded=st.session_state.get(f"rc_{exp_id}") != 0):
            st.code(st.session_state[f"log_{exp_id}"], language="text")

    section_header(
        "Verification",
        "Published vs local",
        "A match does not mean the market effect is universally true; it means your local calculation reproduced the frozen study within the declared tolerance.",
    )
    checks = pd.DataFrame(verification_rows(exp_id, REFERENCE))
    if len(checks):
        st.dataframe(checks, width="stretch", hide_index=True)
    else:
        st.caption("Run the relevant suite to unlock the side-by-side comparison.")


def source_panel(exp: dict) -> None:
    callout(
        "Canonical source",
        "These files are preserved from the published study. The portable runner verifies their SHA-256 hashes before execution and changes only machine-specific paths in a temporary copy.",
    )
    hashes = PROVENANCE.get("canonical_sources", {})
    for relative in exp["sources"]:
        path = ROOT / relative
        digest = hashes.get(relative, "")
        with st.container(border=True):
            st.markdown(f"#### {path.name}")
            if digest:
                st.caption(f"SHA-256 · {digest}")
            st.markdown(f"[Open this file on GitHub ↗]({GITHUB}/blob/main/{relative})")
            if path.is_file():
                with st.expander("Read source"):
                    st.code(path.read_text(encoding="utf-8"), language="python")


def result_browser() -> None:
    files = result_files()
    if not files:
        callout(
            "No local outputs yet",
            "Run a canonical calculation from any experiment's Reproduce tab and its CSV/JSON/PNG outputs will appear here.",
        )
        return

    labels = [str(path.relative_to(ROOT)) for path in files]
    selected = st.selectbox("Generated output", labels)
    path = ROOT / selected

    cols = st.columns(3)
    cols[0].metric("Type", path.suffix.lstrip(".").upper())
    cols[1].metric("Size", f"{path.stat().st_size / 1024:,.1f} KB")
    cols[2].metric("Location", "results/")

    if path.suffix == ".csv":
        frame = pd.read_csv(path)
        st.dataframe(frame, width="stretch", height=min(520, 36 * (len(frame) + 1)))
        numeric = list(frame.select_dtypes(include="number").columns)
        if numeric and len(frame) <= 500:
            with st.expander("Quick chart"):
                x = st.selectbox("X axis", list(frame.columns), key="output_x")
                y = st.selectbox("Y axis", numeric, key="output_y")
                try:
                    st.plotly_chart(
                        px.line(frame, x=x, y=y, markers=True),
                        width="stretch",
                        config=CHART_CONFIG,
                    )
                except Exception:
                    st.info("This output is better inspected as a table.")
    elif path.suffix == ".json":
        st.json(json.loads(path.read_text(encoding="utf-8")))
    else:
        st.image(str(path), caption=selected)


def glossary() -> None:
    section_header(
        "Reading guide",
        "Terms used throughout the study",
        "The project is easier to interpret if these terms are kept distinct.",
    )
    for start in range(0, len(GLOSSARY), 3):
        columns = st.columns(3)
        for column, (term, definition) in zip(columns, GLOSSARY[start:start + 3]):
            with column:
                info_card(term, definition)



def quick_demo_page() -> None:
    hero(
        "60-second software proof",
        "Quick demo",
        "Run the complete detector → market-state → matched-control → forward-outcome pipeline on deterministic synthetic OHLCV. No Databento account or licensed market history is required.",
        ["Synthetic data", "No market claim", "Fast", "End-to-end"],
    )
    callout(
        "What this proves",
        "The demo proves that the software pipeline runs coherently on a fresh machine. Its numerical result is deliberately not presented as evidence about MNQ or FVG profitability.",
        kind="warning",
    )

    cols = st.columns(4)
    with cols[0]:
        info_card("1 · Generate", "Create deterministic MNQ-like synthetic OHLCV with injected FVG formations.")
    with cols[1]:
        info_card("2 · Detect", "Run the same reusable completed-candle FVG detector.")
    with cols[2]:
        info_card("3 · Match", "Build ordinary matched control zones from causal market-state features.")
    with cols[3]:
        info_card("4 · Measure", "Compare future touch outcomes over several horizons.")

    if st.button("Run quick demo", type="primary", width="stretch"):
        live = st.empty()
        rc, log = run_process(
            [str(ROOT / "scripts" / "run_demo.py")],
            live_placeholder=live,
        )
        st.session_state["quick_demo_log"] = log
        st.session_state["quick_demo_rc"] = rc

    if st.session_state.get("quick_demo_log"):
        with st.expander("Demo log", expanded=st.session_state.get("quick_demo_rc") != 0):
            st.code(st.session_state["quick_demo_log"], language="text")

    summary_path = ROOT / "results" / "demo" / "demo_summary.json"
    csv_path = ROOT / "results" / "demo" / "demo_horizons.csv"
    if summary_path.is_file() and csv_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        section_header("Latest run", "Synthetic demo result")
        cols = st.columns(4)
        cols[0].metric("Synthetic bars", f"{int(summary['bars']):,}")
        cols[1].metric("Detected FVGs", f"{int(summary['detected_fvgs']):,}")
        cols[2].metric("Matched controls", f"{int(summary['matched_control_rows']):,}")
        cols[3].metric("Elapsed", f"{float(summary['elapsed_seconds']):.2f}s")
        frame = pd.read_csv(csv_path)
        st.dataframe(frame, width="stretch", hide_index=True)
        fig = px.line(
            frame,
            x="horizon_bars",
            y=["fvg_rate", "control_rate"],
            markers=True,
            labels={"value": "Touch rate", "horizon_bars": "Forward horizon (bars)", "variable": "Series"},
            title="Synthetic FVG vs matched-control touch rate",
        )
        st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)


def full_reproduction_page() -> None:
    hero(
        "One-click canonical workflow",
        "Reproduce the full published study",
        "Run all four preserved computational suites across every published timeframe. Completed stages are cached against the active dataset, so an interrupted run can be resumed without repeating finished work.",
        ["12 cached stages", "Resume-safe", "Canonical v1", "Published comparison"],
    )

    stage_rows = [
        ("01", "Detailed 1m", "Raw fill · deep matched attraction · controls/regimes · deep chronology"),
        ("02–06", "Multi-timeframe", "1m · 5m · 15m · 1H · 4H"),
        ("07–11", "Midpoint / CE", "1m · 5m · 15m · 1H · 4H"),
        ("12", "CE body / execution", "1m through 1D signal timeframes"),
    ]
    st.dataframe(
        pd.DataFrame(stage_rows, columns=["Stage", "Canonical suite", "Feeds"]),
        width="stretch",
        hide_index=True,
    )

    section_header("Input", "Active dataset")
    dataset_summary()
    if not dataset_ready():
        file_setup("full_reproduction")
        return

    callout(
        "Resume behavior",
        "The orchestrator checks fresh success manifests before every stage. Re-running after a crash or manual stop skips stages that already completed on the current dataset.",
        kind="success",
    )

    force = st.checkbox("Force rerun every stage even when a fresh cached result exists.")
    button_label = "Rerun everything" if force else "Start / resume full reproduction"
    if st.button(button_label, type="primary", width="stretch"):
        args = [str(ROOT / "scripts" / "reproduce_full.py")]
        if force:
            args.append("--force")
        live = st.empty()
        rc, log = run_process(args, live_placeholder=live)
        st.session_state["full_reproduction_log"] = log
        st.session_state["full_reproduction_rc"] = rc

    if st.session_state.get("full_reproduction_log"):
        with st.expander(
            "Full reproduction log",
            expanded=st.session_state.get("full_reproduction_rc") != 0,
        ):
            st.code(st.session_state["full_reproduction_log"], language="text")

    state_path = ROOT / "results" / "_full_reproduction" / "state.json"
    verify_path = ROOT / "results" / "_full_reproduction" / "verification.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        section_header("Progress", "Latest full-run state")
        st.caption(f"Status: {state.get('status', 'unknown')}")
        stages = pd.DataFrame(state.get("stages", []))
        if len(stages):
            visible = [column for column in ["key", "label", "status", "seconds", "exit_code"] if column in stages.columns]
            st.dataframe(stages[visible], width="stretch", hide_index=True)
    if verify_path.is_file():
        checks = pd.DataFrame(json.loads(verify_path.read_text(encoding="utf-8")))
        if len(checks):
            section_header("Verification", "Published vs reproduced values")
            st.dataframe(checks, width="stretch", hide_index=True)


def diagnostics_page() -> None:
    hero(
        "Statistical context",
        "Diagnostics & uncertainty",
        "Inspect effect-size profiles, descriptive uncertainty, sample size and chronological stability without turning every positive cell into a trading conclusion.",
        ["Effect size", "Sample size", "Uncertainty", "Robustness"],
    )

    section_header(
        "Matched attraction",
        "Effect size across horizon",
        "The central question is not whether FVGs are revisited often, but how much more often they are reached than comparable ordinary zones.",
    )
    matched = matched_effect_profile(REFERENCE)
    st.dataframe(matched, width="stretch", hide_index=True)
    st.plotly_chart(
        px.line(
            matched,
            x="Horizon",
            y="Difference (pp)",
            markers=True,
            title="Incremental matched attraction by horizon",
        ),
        width="stretch",
        config=CHART_CONFIG,
    )

    section_header(
        "Raw fill-rate uncertainty",
        "Large N makes the descriptive sampling interval very narrow",
        "These Wilson intervals treat events as independent Bernoulli observations. Because market events overlap and cluster, they are descriptive only and do not replace the canonical clustered/bootstrap inference.",
    )
    raw_ci = raw_fill_intervals(REFERENCE)
    raw_ci["plus"] = raw_ci["Wilson high (%)"] - raw_ci["Rate (%)"]
    raw_ci["minus"] = raw_ci["Rate (%)"] - raw_ci["Wilson low (%)"]
    fig = px.line(
        raw_ci,
        x="Horizon",
        y="Rate (%)",
        markers=True,
        error_y="plus",
        error_y_minus="minus",
        title="Raw touch rate with descriptive Wilson interval",
    )
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
    st.dataframe(raw_ci.drop(columns=["plus", "minus"]), width="stretch", hide_index=True)

    section_header(
        "Exploratory CE cell",
        "Sample-size uncertainty around 4H close-depth bands",
        "The intervals below describe win-rate uncertainty only. They do not fix overlap, dependence or the multiple-testing problem documented in the scientific audit.",
    )
    ce = ce_band_intervals(REFERENCE)
    ce["plus"] = ce["Wilson high (%)"] - ce["Win rate (%)"]
    ce["minus"] = ce["Win rate (%)"] - ce["Wilson low (%)"]
    fig = px.bar(
        ce,
        x="Band",
        y="Win rate (%)",
        error_y="plus",
        error_y_minus="minus",
        title="4H CE close-depth bands with descriptive Wilson intervals",
    )
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)
    st.dataframe(ce.drop(columns=["plus", "minus"]), width="stretch", hide_index=True)

    section_header(
        "Chronological stability",
        "How the effect changed in later data",
        "A stable market relationship should not depend entirely on the earlier portion of the sample.",
    )
    shift = chronological_shift(REFERENCE)
    st.dataframe(shift, width="stretch", hide_index=True)
    long = shift.melt(
        id_vars=["Timeframe"],
        value_vars=["Early (pp)", "Later (pp)"],
        var_name="Split",
        value_name="Difference (pp)",
    )
    st.plotly_chart(
        px.bar(
            long,
            x="Timeframe",
            y="Difference (pp)",
            color="Split",
            barmode="group",
            title="Early versus later matched effect",
        ),
        width="stretch",
        config=CHART_CONFIG,
    )

    local = local_detailed_diagnostics(ROOT / "results")
    section_header(
        "Local diagnostics",
        "Year, sensitivity and clustered-bootstrap outputs",
        "These panels appear only after the detailed canonical 1m suite has been run locally. They expose diagnostics that are not fully represented in the frozen summary JSON.",
    )
    if not local:
        callout(
            "No local detailed diagnostics yet",
            "Run the detailed 1m canonical suite from Full reproduction or an experiment Reproduce tab to unlock year-by-year, minimum-gap sensitivity, directional and clustered-bootstrap tables.",
        )
    else:
        if "year" in local:
            st.markdown("#### Year-by-year 60-minute matched effect")
            frame = local["year"].copy()
            if "Difference" in frame:
                frame["Difference (pp)"] = frame["Difference"] * 100
            st.dataframe(frame, width="stretch", hide_index=True)
            if {"group", "Difference (pp)"}.issubset(frame.columns):
                st.plotly_chart(
                    px.bar(frame, x="group", y="Difference (pp)", title="Local 60-minute effect by calendar year"),
                    width="stretch",
                    config=CHART_CONFIG,
                )

        if "sensitivity" in local:
            st.markdown("#### Minimum-gap-size sensitivity")
            frame = local["sensitivity"].copy()
            if "Difference" in frame:
                frame["Difference (pp)"] = frame["Difference"] * 100
            st.dataframe(frame, width="stretch", hide_index=True)
            if {"filter", "target", "Difference (pp)"}.issubset(frame.columns):
                st.plotly_chart(
                    px.bar(
                        frame,
                        x="filter",
                        y="Difference (pp)",
                        color="target",
                        barmode="group",
                        title="Local sensitivity to minimum FVG size",
                    ),
                    width="stretch",
                    config=CHART_CONFIG,
                )

        if "bootstrap_summary" in local:
            st.markdown("#### Clustered-bootstrap inference summary")
            frame = local["bootstrap_summary"].copy()
            for column in ("Difference", "CI_low", "CI_high"):
                if column in frame:
                    frame[column + "_pp"] = frame[column] * 100
            visible = [
                column for column in
                ["test", "N_matched", "Difference_pp", "CI_low_pp", "CI_high_pp", "p_cluster_boot"]
                if column in frame.columns
            ]
            st.dataframe(frame[visible] if visible else frame, width="stretch", hide_index=True)

        if "directional" in local:
            st.markdown("#### Directional displacement diagnostic")
            frame = local["directional"]
            st.dataframe(frame, width="stretch", hide_index=True)
            if {"bars", "FVG_mean_toward_ATR", "Control_mean_toward_ATR"}.issubset(frame.columns):
                st.plotly_chart(
                    px.line(
                        frame,
                        x="bars",
                        y=["FVG_mean_toward_ATR", "Control_mean_toward_ATR"],
                        markers=True,
                        title="Local forward movement toward the zone",
                    ),
                    width="stretch",
                    config=CHART_CONFIG,
                )


def temporal_regime_page() -> None:
    hero(
        "Exploratory extension · same MNQ history",
        "Temporal attraction & rejection regimes",
        "When does the FVG label add more information as an attraction zone, and when does it add more information after first touch as a rejection/reaction zone?",
        ["2020–2026", "Matched controls", "Year / session / hour", "Not frozen v1"],
    )
    callout(
        "Status",
        "This is newer exploratory / extended research on the same MNQ dataset. It is intentionally separated from the frozen published v1 metrics.",
        kind="warning",
    )

    overall = TEMPORAL["overall"]
    attraction = overall["attraction"]
    rejection = overall["rejection"]
    reaction = overall["reaction_3bar_atr"]

    cols = st.columns(3)
    cols[0].metric(
        "60m attraction premium",
        f"{attraction['difference_pp']:+.2f} pp",
        f"{attraction['fvg'] * 100:.2f}% vs {attraction['control'] * 100:.2f}%",
    )
    cols[1].metric(
        "First-touch rejection premium",
        f"{rejection['difference_pp']:+.2f} pp",
        f"{rejection['fvg'] * 100:.2f}% vs {rejection['control'] * 100:.2f}%",
    )
    cols[2].metric(
        "3-bar move-away premium",
        f"{reaction['difference']:+.3f} ATR",
        f"{reaction['fvg']:+.3f} vs {reaction['control']:+.3f}",
    )

    callout(
        "Main finding",
        "Attraction is more regime-dependent. Reaction/rejection is smaller, but more temporally stable. FVG age and native timeframe are stronger conditioning variables than recurring weekday or calendar-month seasonality.",
        kind="success",
    )

    section_header(
        "Year",
        "Attraction changes by regime; rejection is more stable",
        "The attraction premium varies materially across years. The rejection premium remains positive in each year shown but its broad year-to-year heterogeneity is much weaker.",
    )
    years = sorted(TEMPORAL["attraction_by_year_pp"])
    yearly = pd.DataFrame(
        {
            "Year": years,
            "Attraction premium (pp)": [TEMPORAL["attraction_by_year_pp"][year] for year in years],
            "Rejection premium (pp)": [TEMPORAL["rejection_by_year_pp"][year] for year in years],
        }
    )
    st.dataframe(yearly, width="stretch", hide_index=True)
    long_year = yearly.melt(id_vars="Year", var_name="Behavior", value_name="Premium (pp)")
    st.plotly_chart(
        px.bar(
            long_year,
            x="Year",
            y="Premium (pp)",
            color="Behavior",
            barmode="group",
            title="Matched FVG premium by year",
        ),
        width="stretch",
        config=CHART_CONFIG,
    )

    era = pd.DataFrame(
        [{"Era": key, "Attraction premium (pp)": value} for key, value in TEMPORAL.get("era_attraction_pp", {}).items()]
    )
    if len(era):
        st.markdown("#### Era comparison")
        st.dataframe(era, width="stretch", hide_index=True)
        callout(
            "No recent strengthening",
            "The latest era has a smaller attraction premium than 2020–2024. The data does not support the idea that FVG attraction only started working recently.",
        )

    section_header(
        "Sessions",
        "Formation-session attraction vs touch-session rejection",
        "High raw revisit probability does not necessarily mean a large FVG-specific effect. NY premarket is the clearest example.",
    )
    formation = pd.DataFrame(
        [
            {"Session": key.replace("_", " ").title(), "Attraction premium (pp)": value}
            for key, value in TEMPORAL["attraction_by_formation_session_pp"].items()
        ]
    )
    touch = pd.DataFrame(
        [
            {"Session": key.replace("_", " ").title(), "Rejection premium (pp)": value}
            for key, value in TEMPORAL["rejection_by_touch_session_pp"].items()
        ]
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            px.bar(formation, x="Session", y="Attraction premium (pp)", title="Attraction premium by FVG formation session"),
            width="stretch",
            config=CHART_CONFIG,
        )
        st.dataframe(formation, width="stretch", hide_index=True)
    with right:
        st.plotly_chart(
            px.bar(touch, x="Session", y="Rejection premium (pp)", title="Rejection premium by actual touch session"),
            width="stretch",
            config=CHART_CONFIG,
        )
        st.dataframe(touch, width="stretch", hide_index=True)

    callout(
        "Premarket lesson",
        "NY premarket had one of the highest raw FVG touch rates, but only a very small matched attraction premium. Ordinary nearby zones were also revisited extremely often there.",
    )

    section_header(
        "Hour of day",
        "Interesting reaction windows, but not confirmed time filters",
        "These are descriptive ET-hour candidates. The overall hour-of-day heterogeneity test was not strong enough to establish a production rule.",
    )
    hour_frame = pd.DataFrame(
        [{"ET hour": hour, "Rejection premium (pp)": value} for hour, value in TEMPORAL.get("rejection_by_touch_hour_pp", {}).items()]
    ).sort_values("Rejection premium (pp)", ascending=False)
    if len(hour_frame):
        st.dataframe(hour_frame, width="stretch", hide_index=True)
        st.plotly_chart(
            px.bar(hour_frame, x="ET hour", y="Rejection premium (pp)", title="Descriptive first-touch rejection premium by ET hour"),
            width="stretch",
            config=CHART_CONFIG,
        )

    section_header(
        "Native timeframe",
        "Attraction decays with timeframe; reaction stays modestly positive",
        "This is one of the strongest timing results in the entire project.",
    )
    tf_order = ["1m", "5m", "15m", "1H", "4H"]
    tf_frame = pd.DataFrame(
        {
            "Timeframe": tf_order,
            "Attraction premium (pp)": [TEMPORAL["native_timeframe_attraction_5bar_pp"][tf] for tf in tf_order],
            "Rejection premium (pp)": [TEMPORAL["native_timeframe_rejection_pp"][tf] for tf in tf_order],
        }
    )
    st.dataframe(tf_frame, width="stretch", hide_index=True)
    st.plotly_chart(
        px.line(
            tf_frame.melt(id_vars="Timeframe", var_name="Behavior", value_name="Premium (pp)"),
            x="Timeframe",
            y="Premium (pp)",
            color="Behavior",
            markers=True,
            title="Attraction versus rejection across native timeframe",
        ),
        width="stretch",
        config=CHART_CONFIG,
    )

    section_header(
        "Freshness",
        "FVG age is the clearest temporal variable",
        "If an FVG contains unusual attraction information, the incremental effect is concentrated in the first few bars after formation.",
    )
    age = pd.DataFrame(
        [
            {"Age window": key.replace("_", "→").replace("to", ""), "Incremental attraction (pp)": value}
            for key, value in TEMPORAL["age_decay_1m_pp"].items()
        ]
    )
    age["Age window"] = ["1→3 bars", "3→5 bars", "5→10 bars", "10→20 bars"]
    st.dataframe(age, width="stretch", hide_index=True)
    st.plotly_chart(
        px.bar(age, x="Age window", y="Incremental attraction (pp)", title="1m conditional attraction premium by FVG age"),
        width="stretch",
        config=CHART_CONFIG,
    )

    section_header(
        "Calendar structure",
        "Month and weekday effects are weak; isolated regimes can still spike",
        "Specific months, weeks or days can look extreme, but that is different from a recurring calendar edge.",
    )
    quarter = pd.DataFrame(
        [{"Quarter": key, "Attraction premium (pp)": value} for key, value in TEMPORAL.get("quarter_attraction_pp", {}).items()]
    )
    months = pd.DataFrame(
        [{"Historical month": key, "Attraction premium (pp)": value} for key, value in TEMPORAL.get("historical_month_attraction_pp", {}).items()]
    )
    ql, qr = st.columns(2)
    with ql:
        st.markdown("#### Selected quarter regimes")
        st.dataframe(quarter, width="stretch", hide_index=True)
    with qr:
        st.markdown("#### Stronger historical month episodes")
        st.dataframe(months, width="stretch", hide_index=True)

    hetero_rows = []
    for dimension, values in TEMPORAL.get("heterogeneity_p_approx", {}).items():
        hetero_rows.append(
            {
                "Dimension": dimension.replace("_", " ").title(),
                "Attraction p (approx)": values.get("attraction"),
                "Rejection p (approx)": values.get("rejection"),
            }
        )
    if hetero_rows:
        st.markdown("#### Broad temporal heterogeneity tests")
        st.dataframe(pd.DataFrame(hetero_rows), width="stretch", hide_index=True)

    with st.expander("Extreme week / day diagnostics"):
        st.json(
            {
                "extreme_weeks": TEMPORAL.get("extreme_weeks", {}),
                "extreme_days": TEMPORAL.get("extreme_days", {}),
                "day_of_month_rejection_pp": TEMPORAL.get("day_of_month_rejection_pp", {}),
            }
        )
        st.warning(
            "These are multiple-comparison diagnostics. They are evidence that regimes can become extreme, not evidence that the same calendar date will repeat."
        )

    section_header(
        "Current interpretation",
        "What the temporal study changes",
        "The data is more consistent with two related but different mechanisms than with one universal FVG force.",
    )
    left, right = st.columns(2)
    with left:
        info_card(
            "Attraction",
            "Short-lived, strongest on lower timeframes, strongest when fresh, and materially regime-dependent across years/quarters/sessions.",
            "~+1 pp long-run matched premium",
        )
    with right:
        info_card(
            "Reaction / rejection",
            "Smaller but more stable through time and positive across the tested native timeframes; exact session/hour rankings remain exploratory.",
            "~+2 pp long-run matched premium",
        )

    st.markdown(
        f"[Full temporal study ↗]({GITHUB}/blob/main/docs/TEMPORAL_ATTRACTION_REACTION_STUDY.md) · "
        f"[Machine-readable findings ↗]({GITHUB}/blob/main/research_v2/findings/temporal_attraction_reaction_2026-09-20.json) · "
        f"[Full chat research archive ↗]({GITHUB}/blob/main/docs/CHAT_RESEARCH_ARCHIVE_2026-09-20.md)"
    )


def performance_page() -> None:
    hero(
        "Machine-specific timing",
        "Performance & startup",
        "Measure what actually takes time on this computer instead of publishing invented benchmark numbers from a different machine.",
        ["Startup", "Quick demo", "Report generation", "Optional dataset load"],
    )

    callout(
        "Repeat startup is already optimized",
        "After the first successful install, START_HERE fingerprints the dependency files and runs a lightweight health probe. It does not run pip install again unless the environment or dependency definition changed.",
        kind="success",
    )

    include_dataset = st.checkbox(
        "Include a full active-dataset pickle load in the benchmark",
        disabled=not dataset_ready(),
        help="This can use significant memory. Leave it off for a quick benchmark.",
    )
    if st.button("Run benchmark on this machine", type="primary", width="stretch"):
        args = [str(ROOT / "scripts" / "benchmark.py")]
        if include_dataset:
            args.append("--include-dataset")
        live = st.empty()
        rc, log = run_process(args, live_placeholder=live)
        st.session_state["benchmark_log"] = log
        st.session_state["benchmark_rc"] = rc

    if st.session_state.get("benchmark_log"):
        with st.expander("Benchmark log", expanded=st.session_state.get("benchmark_rc") != 0):
            st.code(st.session_state["benchmark_log"], language="text")

    path = ROOT / "results" / "_benchmarks" / "latest.json"
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        section_header("Latest benchmark", "Measured on this machine")
        st.caption(f"{payload.get('platform', '')} · Python {payload.get('python', '')}")
        rows = [
            {"Measurement": key.replace("_", " "), "Value": value}
            for key, value in payload.get("measurements", {}).items()
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    full_state = ROOT / "results" / "_full_reproduction" / "state.json"
    if full_state.is_file():
        payload = json.loads(full_state.read_text(encoding="utf-8"))
        stages = pd.DataFrame(payload.get("stages", []))
        timed = stages.loc[stages.get("seconds", pd.Series(dtype=float)).fillna(0) > 0] if len(stages) else pd.DataFrame()
        if len(timed):
            section_header("Heavy calculations", "Measured full-reproduction stage times")
            st.dataframe(timed[["label", "status", "seconds"]], width="stretch", hide_index=True)


def research_v2_page() -> None:
    hero(
        "Corrected / extended study",
        "Research v2",
        "A separate new-research track that addresses known limitations in the published scripts without rewriting the historical v1 evidence.",
        ["NEW / UNPUBLISHED", "Corrected censoring", "Walk-forward", "Multiplicity control"],
    )
    callout(
        "Not part of the published v1 result",
        "Any value generated here is new research. It is intentionally kept separate from the frozen published reference until it has been run on licensed data and reviewed.",
        kind="warning",
    )

    corrections = [
        ("Full-horizon symmetry", "Real FVGs and controls both require the complete requested future window."),
        ("Contract-boundary censoring", "Future outcomes cannot cross an active-contract segment."),
        ("Parent-paired decay", "Control survivors are averaged within each parent before comparison."),
        ("CME trade-date clustering", "Bootstrap clusters use the same 18:00 ET trade-date convention as the dataset."),
        ("Chronological isolation", "Walk-forward controls are constructed inside the corresponding test period only."),
        ("Multiplicity control", "Walk-forward p-values receive Benjamini-Hochberg FDR-adjusted q-values."),
    ]
    for start in range(0, len(corrections), 3):
        cols = st.columns(3)
        for column, (title, body) in zip(cols, corrections[start:start + 3]):
            with column:
                info_card(title, body)

    if not dataset_ready():
        section_header("Input", "Prepare a dataset before running v2")
        dataset_summary()
        return

    section_header("Run", "Choose a corrected v2 analysis")
    study = st.radio(
        "Study",
        ["attraction-1m", "age-decay-1m", "walk-forward-1m", "ce-reinfer"],
        format_func=lambda value: {
            "attraction-1m": "Corrected 1m matched attraction",
            "age-decay-1m": "Corrected parent-paired 1m age decay",
            "walk-forward-1m": "Walk-forward corrected 1m attraction",
            "ce-reinfer": "CE/body clustered re-inference + FDR correction",
        }[value],
    )

    if study == "ce-reinfer":
        callout(
            "Uses canonical trade rows",
            "Run the published CE/body suite first. Research v2 reuses those exact signal/trade mechanics and changes only the uncertainty and multiplicity layer.",
        )
        boot = st.number_input("Bootstrap replications", min_value=100, value=500, step=100)
        horizon = 60
        max_events = 10_000
    else:
        cols = st.columns(3)
        horizon = cols[0].number_input("Horizon (1m bars)", min_value=1, value=60, step=1)
        max_events = cols[1].number_input("Max FVG parents", min_value=100, value=10_000, step=500)
        boot = cols[2].number_input("Bootstrap replications", min_value=100, value=500, step=100)

    if st.button("Run Research v2", type="primary", width="stretch"):
        args = ["-m", "research_v2.runner", study, "--bootstrap", str(int(boot))]
        if study != "ce-reinfer":
            args += [
                "--horizon", str(int(horizon)),
                "--max-events", str(int(max_events)),
            ]
        live = st.empty()
        rc, log = run_process(args, live_placeholder=live)
        st.session_state["v2_log"] = log
        st.session_state["v2_rc"] = rc

    if st.session_state.get("v2_log"):
        with st.expander("Research v2 log", expanded=st.session_state.get("v2_rc") != 0):
            st.code(st.session_state["v2_log"], language="text")

    out = ROOT / "results" / "research_v2"
    file_map = {
        "attraction-1m": out / "corrected_attraction_1m.json",
        "age-decay-1m": out / "corrected_age_decay_1m.json",
        "walk-forward-1m": out / "walk_forward_1m.json",
        "ce-reinfer": out / "ce_reinference.json",
    }
    file = file_map[study]
    if file.is_file():
        section_header("Latest result", "New / unpublished output")
        payload = json.loads(file.read_text(encoding="utf-8"))
        if study == "attraction-1m":
            result = payload.get("result", {})
            cols = st.columns(4)
            cols[0].metric("Parents", f"{int(result.get('parents', 0)):,}")
            cols[1].metric("Difference", f"{float(result.get('difference_pp', float('nan'))):+.3f} pp")
            cols[2].metric("95% cluster CI", f"{float(result.get('ci_low_pp', float('nan'))):+.2f} to {float(result.get('ci_high_pp', float('nan'))):+.2f} pp")
            cols[3].metric("Two-sided p", f"{float(result.get('p_two_sided', float('nan'))):.3f}")
            st.json(payload)
        else:
            records_key = "cells" if study == "ce-reinfer" else "windows"
            frame = pd.DataFrame(payload.get(records_key, []))
            st.dataframe(frame, width="stretch", hide_index=True)
            if len(frame):
                if study == "ce-reinfer":
                    st.plotly_chart(
                        px.scatter(
                            frame,
                            x="mean_R",
                            y="q_mean_R_bh",
                            size="N",
                            color="timeframe",
                            hover_data=["depth_band", "p_mean_R_two_sided"],
                            title="CE cells: mean R versus FDR-adjusted q-value",
                        ),
                        width="stretch",
                        config=CHART_CONFIG,
                    )
                else:
                    title = (
                        "Corrected parent-paired age decay"
                        if study == "age-decay-1m"
                        else "Corrected walk-forward matched attraction"
                    )
                    st.plotly_chart(
                        px.line(
                            frame,
                            x="window",
                            y="difference_pp",
                            markers=True,
                            title=title,
                        ),
                        width="stretch",
                        config=CHART_CONFIG,
                    )


def report_page() -> None:
    hero(
        "Portable research artifact",
        "Report & export",
        "Download a self-contained HTML research report containing the study summary, conceptual diagrams, all nine experiment descriptions, frozen metrics, methodology, provenance and limitations.",
        ["Single HTML file", "Offline readable", "No market data", "Generated from repository evidence"],
    )

    report_html = build_report(
        REFERENCE,
        EXPERIMENTS,
        EXPERIMENT_PROVENANCE,
        ROOT,
    )
    cols = st.columns(2)
    with cols[0]:
        st.download_button(
            "Download self-contained HTML report",
            data=report_html,
            file_name="fvg_predictive_strength_research_report.html",
            mime="text/html",
            type="primary",
            width="stretch",
        )
    with cols[1]:
        st.link_button(
            "Open public static report",
            STATIC_REPORT,
            width="stretch",
        )

    section_header(
        "What is included",
        "One artifact, full audit trail",
        "The report is generated from the same frozen evidence and metadata used by the Research Lab rather than maintained as a separate hand-edited document.",
    )
    cols = st.columns(4)
    with cols[0]:
        info_card("Study summary", "Dataset scope, research question and central published conclusion.")
    with cols[1]:
        info_card("Nine experiments", "Conceptual diagram, headline values, method and limitation for every experiment.")
    with cols[2]:
        info_card("Provenance", "Canonical suite, input scope, sample design, control design, seeds and outputs.")
    with cols[3]:
        info_card("No licensed data", "The report contains evidence and methodology only, never redistributed vendor history.")


def home_page() -> None:
    hero(
        "Quantitative market-structure research",
        "FVG Predictive Strength",
        "A reproducible MNQ study testing whether mechanically defined Fair Value Gaps contain information beyond distance, volatility, trend, session and ordinary price revisits.",
        ["MNQ", "2020–2026", "2.3M active 1m bars", "454k+ 1m FVGs", "9 experiments"],
    )

    section_header("Research question", "Are Fair Value Gaps actually special?")
    callout(
        "Published conclusion",
        "FVGs were revisited frequently, but after matching comparable ordinary zones the incremental attraction was small, strongest shortly after formation, and inconsistent across longer horizons, timeframes and later data.",
    )

    cols = st.columns(4)
    cols[0].metric("Active 1m bars", f"{REFERENCE['study']['active_1m_rows']:,}")
    cols[1].metric("Detected 1m FVGs", f"{REFERENCE['study']['fvg_1m_count']:,}")
    cols[2].metric("Contracts", REFERENCE["study"]["contracts"])
    cols[3].metric("Experiments", len(EXPERIMENTS))

    section_header(
        "Key findings",
        "What the evidence says",
        "These are the headline results. The experiment pages show the exact procedures, charts, raw frozen values and limitations behind each statement.",
    )
    a, b, c, d = st.columns(4)
    with a:
        info_card("Raw revisits", "1m FVGs were frequently revisited.", "~90.9% within 60m")
    with b:
        info_card("Matched effect", "Most of that raw attraction was shared by comparable ordinary zones.", "+0.58 pp at 60m")
    with c:
        info_card("Decay", "The excess attraction was strongest shortly after formation.", "Front-loaded")
    with d:
        info_card("Robustness", "Several effects weakened or reversed in later or higher-timeframe samples.", "Not stable")

    section_header(
        "Study design",
        "How the project tries to falsify the magnet claim",
        "The experiments progress from a descriptive baseline toward stronger controls and temporal stress tests.",
    )
    design = [
        ("1 · Define", "Detect FVGs mechanically from completed candles so there is no discretionary labeling."),
        ("2 · Match", "Construct ordinary control zones with similar geometry and broad market state."),
        ("3 · Test", "Compare attraction, continuation, reaction and midpoint behavior across horizons/timeframes."),
        ("4 · Stress-test", "Stratify by distance/regime and compare early versus later chronological samples."),
    ]
    cols = st.columns(4)
    for column, (title, body) in zip(cols, design):
        with column:
            info_card(title, body)

    section_header(
        "Architecture",
        "How four computational suites become nine experiments",
        "The heavy calculations are shared rather than duplicated. This is why one successful canonical run can populate several experiment pages.",
    )
    st.markdown(research_flow_svg(), unsafe_allow_html=True)

    section_header(
        "Visual summary",
        "Two charts that capture the central result",
        "The first shows the matched attraction shrinking with horizon. The second shows how the five-bar effect changes between the early and later sample.",
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            published_charts("matched_attraction", REFERENCE)[1][1],
            width="stretch",
            config=CHART_CONFIG,
        )
    with right:
        st.plotly_chart(
            published_charts("oos", REFERENCE)[0][1],
            width="stretch",
            config=CHART_CONFIG,
        )

    section_header(
        "Experiment library",
        "Explore all nine experiments",
        "Start with Raw Fill Rates for the baseline, then Matched-Zone Attraction for the primary control test, and Chronological Robustness for the later-data check.",
    )
    items = [(key, EXPERIMENTS[key]) for key in ORDER]
    for start in range(0, len(items), 3):
        columns = st.columns(3)
        for column, (exp_id, exp) in zip(columns, items[start:start + 3]):
            with column:
                with st.container(border=True):
                    st.caption(f"EXPERIMENT {exp['num']}")
                    st.markdown(f"### {exp['title']}")
                    st.caption(" · ".join(EXPERIMENT_TAGS[exp_id]))
                    st.write(exp["question"])
                    st.markdown(f"**Published takeaway:** {exp['takeaway']}")
                    if st.button("Open experiment →", key=f"open_{exp_id}", width="stretch"):
                        st.session_state["selected"] = exp_id
                        st.session_state["page"] = "Experiment"
                        st.rerun()

    glossary()

    section_header(
        "Public long-history replication",
        "Repeat the same research process on free Nasdaq-100 history",
        "A separate public track uses HistData NSX/USD from 2010 onward so readers can inspect the underlying candles, run the same experiment families, and reproduce the work without a licensed Databento dataset.",
    )
    cols = st.columns(3)
    with cols[0]:
        info_card("~16 years", "The public dataset extends the research window back to late 2010.", "5M+ 1m bars")
    with cols[1]:
        info_card("Live explorer", "Load any date slice, resample it and overlay mechanically detected FVGs directly on the candles.", "Actual observations")
    with cols[2]:
        info_card("9 experiment families", "Run the same falsification sequence while keeping the public proxy results separate from MNQ.", "Replication track")
    if st.button("Open public Nasdaq replication →", type="primary", width="stretch"):
        st.session_state["page"] = "Public Nasdaq"
        st.rerun()

    section_header(
        "Latest extension",
        "When are FVGs most predictive?",
        "A newer temporal study separates attraction from first-touch rejection across year, session, hour, timeframe and FVG age.",
    )
    cols = st.columns(3)
    with cols[0]:
        info_card("60m attraction premium", "FVGs were reached slightly more often than tightly matched ordinary zones.", "+1.05 pp")
    with cols[1]:
        info_card("First-touch rejection premium", "After touch, FVGs rejected slightly more often than matched ordinary zones.", "+1.93 pp")
    with cols[2]:
        info_card("Strongest timing result", "Freshness and native timeframe mattered more than recurring weekday/month seasonality.", "Age > calendar")
    if st.button("Open temporal regime study →", width="stretch"):
        st.session_state["page"] = "Temporal Regimes"
        st.rerun()

    section_header(
        "Reproducibility",
        "Read immediately; reproduce when you want",
        "Frozen evidence, provenance and source are visible without data. Full local reproduction is a separate workflow so the research remains inspectable even if a user never downloads licensed market history.",
    )
    cols = st.columns(3)
    with cols[0]:
        info_card("Published evidence", "Frozen metrics and rendered figures can be inspected directly from GitHub.")
    with cols[1]:
        info_card("Hash-locked source", "Four preserved canonical scripts are checked in CI and again before local execution.")
    with cols[2]:
        info_card("Independent rerun", "Bring licensed data, build the active series and compare your output against the frozen reference.")

    cta_left, cta_right = st.columns(2)
    with cta_left:
        if st.button("Run the no-data quick demo →", type="primary", width="stretch"):
            st.session_state["page"] = "Quick Demo"
            st.rerun()
    with cta_right:
        if st.button("Open full reproduction →", width="stretch"):
            st.session_state["page"] = "Full Reproduction"
            st.rerun()

    st.markdown("---")
    st.markdown(
        f"[GitHub repository]({GITHUB}) · "
        f"[Published report]({REPORT}) · "
        f"[Experiment specification]({GITHUB}/blob/main/docs/EXPERIMENTS.md) · "
        f"[Scientific audit]({GITHUB}/blob/main/docs/SCIENTIFIC_AUDIT.md)"
    )


def experiment_page(exp_id: str) -> None:
    exp = EXPERIMENTS[exp_id]

    top_left, top_right = st.columns([1, 5])
    with top_left:
        if st.button("← Experiments", width="stretch"):
            st.session_state["page"] = "Home"
            st.rerun()
    with top_right:
        st.caption("PUBLISHED REFERENCE · FROZEN EVIDENCE")

    hero(
        f"Experiment {exp['num']}",
        exp["title"],
        exp["question"],
        EXPERIMENT_TAGS[exp_id],
    )
    st.write(exp["summary"])

    metrics = headline_metrics(exp_id, REFERENCE)
    if metrics:
        cols = st.columns(len(metrics))
        for column, (label, value, delta) in zip(cols, metrics):
            column.metric(label, value, delta)

    callout("What this experiment adds", exp["takeaway"])

    section_header(
        "Visual model",
        "What this experiment is actually testing",
        "The diagram is conceptual. The exact numerical rules remain the canonical code and method specification.",
    )
    st.markdown(experiment_svg(exp_id), unsafe_allow_html=True)

    prov = EXPERIMENT_PROVENANCE[exp_id]
    with st.expander("Experiment provenance · sample · controls · seed · outputs"):
        rows = [
            ("Canonical suite", prov["suite"]),
            ("Input", prov["input"]),
            ("Published population", prov["population"]),
            ("Controls", prov["controls"]),
            ("Seed", prov["seed"]),
            ("Primary outputs", ", ".join(prov["outputs"])),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["Field", "Published design"]),
            width="stretch",
            hide_index=True,
        )

    results, method, reproduce, source = st.tabs(
        ["Results", "Method & limitations", "Reproduce", "Canonical source"]
    )

    with results:
        section_header(
            "Published evidence",
            "What the frozen study measured",
            "Every chart below is built from reference_results/reference_metrics.json, not from a live calculation.",
        )
        for heading, figure, table in published_charts(exp_id, REFERENCE):
            with st.container(border=True):
                st.markdown(f"#### {heading}")
                st.plotly_chart(figure, width="stretch", config=CHART_CONFIG)
                with st.expander("View exact values"):
                    st.dataframe(table, width="stretch", hide_index=True)

    with method:
        left, right = st.columns([2, 1])
        with left:
            section_header("Procedure", "Exact experiment sequence")
            method_steps(exp["method"])
        with right:
            section_header("Interpretation", "Important guardrail")
            callout("Limitation", exp["limitations"], kind="warning")
            info_card(
                "Audit trail",
                "The full specification and scientific audit document the retained methodological limitations rather than silently changing the published analysis.",
            )
            st.markdown(
                f"[Full experiment specification ↗]({GITHUB}/blob/main/docs/EXPERIMENTS.md)\n\n"
                f"[Scientific audit ↗]({GITHUB}/blob/main/docs/SCIENTIFIC_AUDIT.md)"
            )

    with reproduce:
        reproduce_panel(exp_id, exp)

    with source:
        source_panel(exp)


def sidebar() -> None:
    st.markdown("### FVG Predictive Strength")
    st.caption("Research Lab · published evidence + local reproduction")

    if st.button("Research overview", width="stretch"):
        st.session_state["page"] = "Home"
        st.rerun()

    st.markdown("**Run & verify**")
    if st.button("Quick demo", width="stretch"):
        st.session_state["page"] = "Quick Demo"
        st.rerun()
    if st.button("Reproduce / data setup", width="stretch"):
        st.session_state["page"] = "Data Setup"
        st.rerun()
    if st.button("Full reproduction", width="stretch"):
        st.session_state["page"] = "Full Reproduction"
        st.rerun()

    st.markdown("**Public Nasdaq replication**")
    if st.button("Public Nasdaq overview", width="stretch"):
        st.session_state["page"] = "Public Nasdaq"
        st.rerun()
    if st.button("Public data setup", width="stretch"):
        st.session_state["page"] = "Public Nasdaq Setup"
        st.rerun()
    if st.button("Public data explorer", width="stretch"):
        st.session_state["page"] = "Public Nasdaq Explorer"
        st.rerun()
    if st.button("Public experiment lab", width="stretch"):
        st.session_state["page"] = "Public Nasdaq Experiments"
        st.rerun()
    if st.button("Public full replication", width="stretch"):
        st.session_state["page"] = "Public Nasdaq Reproduction"
        st.rerun()

    st.markdown("**Inspect & export**")
    if st.button("Event explorer", width="stretch"):
        st.session_state["page"] = "Event Explorer"
        st.rerun()
    if st.button("Diagnostics", width="stretch"):
        st.session_state["page"] = "Diagnostics"
        st.rerun()
    if st.button("Temporal regimes", width="stretch"):
        st.session_state["page"] = "Temporal Regimes"
        st.rerun()
    if st.button("Stability atlas", width="stretch"):
        st.session_state["page"] = "Stability Atlas"
        st.rerun()
    if st.button("Power / MDE", width="stretch"):
        st.session_state["page"] = "Power"
        st.rerun()
    if st.button("Economic significance", width="stretch"):
        st.session_state["page"] = "Economics"
        st.rerun()
    if st.button("Report / export", width="stretch"):
        st.session_state["page"] = "Report"
        st.rerun()
    if st.button("Performance", width="stretch"):
        st.session_state["page"] = "Performance"
        st.rerun()

    st.markdown("**Research discipline**")
    if st.button("Placebos / ablations", width="stretch"):
        st.session_state["page"] = "Stress Tests"
        st.rerun()
    if st.button("Hypothesis registry", width="stretch"):
        st.session_state["page"] = "Hypothesis Registry"
        st.rerun()
    if st.button("Dataset preflight", width="stretch"):
        st.session_state["page"] = "Data Preflight"
        st.rerun()
    if st.button("Research v2", width="stretch"):
        st.session_state["page"] = "Research v2"
        st.rerun()
    if st.button("v1 vs v2", width="stretch"):
        st.session_state["page"] = "V1 V2"
        st.rerun()
    if st.button("Releases / provenance", width="stretch"):
        st.session_state["page"] = "Releases"
        st.rerun()
    if st.button("Local outputs", width="stretch"):
        st.session_state["page"] = "Generated Outputs"
        st.rerun()

    st.markdown("---")
    labels = {key: f"{EXPERIMENTS[key]['num']} · {EXPERIMENTS[key]['title']}" for key in ORDER}
    selected = st.selectbox(
        "Jump to experiment",
        ORDER,
        format_func=lambda key: labels[key],
        key="sidebar_experiment",
    )
    if st.button("Open selected experiment", width="stretch"):
        st.session_state["selected"] = selected
        st.session_state["page"] = "Experiment"
        st.rerun()

    st.markdown("---")
    sidebar_status("Local dataset", "Ready" if dataset_ready() else "Not prepared")
    if dataset_ready():
        st.caption(current_dataset_label())
    sidebar_status("Published sample", "MNQ · 2020–2026")
    sidebar_status("Code version", repo_commit())

    st.markdown(
        f"[GitHub source ↗]({GITHUB})  \n"
        f"[Published report ↗]({REPORT})"
    )


def main() -> None:
    st.set_page_config(
        page_title="FVG Predictive Strength — Research Lab",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()

    if "page" not in st.session_state:
        st.session_state["page"] = "Home"

    with st.sidebar:
        sidebar()

    page = st.session_state["page"]
    if page == "Quick Demo":
        quick_demo_page()
    elif page == "Public Nasdaq":
        public_nsx_overview_page()
    elif page == "Public Nasdaq Setup":
        public_nsx_setup_page()
    elif page == "Public Nasdaq Explorer":
        public_nsx_explorer_page()
    elif page == "Public Nasdaq Experiments":
        public_nsx_experiment_page()
    elif page == "Public Nasdaq Reproduction":
        public_nsx_reproduction_page()
    elif page == "Data Setup":
        data_page()
    elif page == "Full Reproduction":
        full_reproduction_page()
    elif page == "Event Explorer":
        event_explorer_page()
    elif page == "Diagnostics":
        diagnostics_page()
    elif page == "Temporal Regimes":
        temporal_regime_page()
    elif page == "Stability Atlas":
        stability_atlas_page(REFERENCE)
    elif page == "Power":
        power_page()
    elif page == "Economics":
        economics_page()
    elif page == "Stress Tests":
        scientific_stress_page()
    elif page == "Hypothesis Registry":
        hypothesis_registry_page()
    elif page == "Data Preflight":
        data_preflight_page()
    elif page == "Performance":
        performance_page()
    elif page == "Research v2":
        research_v2_page()
    elif page == "V1 V2":
        v1_v2_comparison_page(REFERENCE)
    elif page == "Releases":
        release_provenance_page()
    elif page == "Report":
        report_page()
    elif page == "Generated Outputs":
        hero(
            "Local reproduction",
            "Generated outputs",
            "Browse files created by calculations on this machine. These are intentionally kept separate from the frozen published evidence.",
            ["Local only", "CSV", "JSON", "PNG"],
        )
        result_browser()
    elif page == "Experiment" and st.session_state.get("selected") in EXPERIMENTS:
        experiment_page(st.session_state["selected"])
    else:
        home_page()
