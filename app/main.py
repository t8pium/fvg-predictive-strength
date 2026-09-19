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

REFERENCE = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
PROVENANCE = json.loads((ROOT / "reference_results" / "manifest.json").read_text(encoding="utf-8"))
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
    if st.button("Reproduce / data setup", width="stretch"):
        st.session_state["page"] = "Data Setup"
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
    if page == "Data Setup":
        data_page()
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
