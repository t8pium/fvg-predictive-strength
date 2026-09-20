from __future__ import annotations

from html import escape

import streamlit as st


# Explicit colors are intentional. The previous theme derived card/text colors
# from Streamlit variables with color-mix(), which produced poor contrast under
# some browser/Streamlit dark-theme combinations.
BG = "#0b0f17"
SIDEBAR = "#11131d"
SURFACE = "#111827"
SURFACE_2 = "#182235"
SURFACE_3 = "#202b3d"
BORDER = "#334155"
TEXT = "#f8fafc"
MUTED = "#cbd5e1"
SUBTLE = "#94a3b8"
ACCENT = "#60a5fa"
ACCENT_STRONG = "#3b82f6"
INFO_BG = "#10243c"
INFO_TEXT = "#dbeafe"
SUCCESS_BG = "#0d2818"
SUCCESS_TEXT = "#dcfce7"
WARNING_BG = "#3a2612"
WARNING_TEXT = "#fff7ed"
DANGER_BG = "#3a151c"
DANGER_TEXT = "#ffe4e6"


def _render_html(html: str) -> None:
    """Render compact custom HTML without Markdown block/code ambiguity.

    Keep component HTML on one physical line. Indented multiline raw HTML can be
    terminated by an empty line in Python-generated markup, after which Markdown
    may interpret the remaining indented <div> as a code block.
    """
    st.markdown(" ".join(html.split()), unsafe_allow_html=True)


def apply_theme() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --fvg-bg: {BG};
            --fvg-sidebar: {SIDEBAR};
            --fvg-surface: {SURFACE};
            --fvg-surface-2: {SURFACE_2};
            --fvg-surface-3: {SURFACE_3};
            --fvg-border: {BORDER};
            --fvg-text: {TEXT};
            --fvg-muted: {MUTED};
            --fvg-subtle: {SUBTLE};
            --fvg-accent: {ACCENT};
            --fvg-accent-strong: {ACCENT_STRONG};
            --fvg-info-bg: {INFO_BG};
            --fvg-info-text: {INFO_TEXT};
            --fvg-success-bg: {SUCCESS_BG};
            --fvg-success-text: {SUCCESS_TEXT};
            --fvg-warning-bg: {WARNING_BG};
            --fvg-warning-text: {WARNING_TEXT};
            --fvg-danger-bg: {DANGER_BG};
            --fvg-danger-text: {DANGER_TEXT};
        }}

        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: var(--fvg-bg) !important;
            color: var(--fvg-text) !important;
        }}

        .block-container {{
            max-width: 1220px;
            padding-top: 1.35rem;
            padding-bottom: 4.5rem;
        }}

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
            color: var(--fvg-text) !important;
        }}

        .stApp h1 {{
            letter-spacing: -0.035em;
            line-height: 1.05 !important;
            margin-bottom: .55rem !important;
        }}

        .stApp h2 {{
            letter-spacing: -0.022em;
            margin-top: 2.2rem !important;
            margin-bottom: .7rem !important;
        }}

        .stApp h3 {{
            letter-spacing: -0.015em;
        }}

        .stApp p, .stApp li {{
            line-height: 1.62;
        }}

        .stApp [data-testid="stMarkdownContainer"] > p,
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p {{
            color: var(--fvg-muted) !important;
        }}

        /* Hero */
        .fvg-hero {{
            padding: 1.55rem 1.65rem 1.45rem;
            border: 1px solid var(--fvg-border);
            border-radius: 18px;
            background:
                radial-gradient(circle at 14% 0%, rgba(59,130,246,.20), transparent 36%),
                linear-gradient(135deg, #172033 0%, #111827 66%, #0f172a 100%);
            box-shadow: 0 12px 30px rgba(0,0,0,.24);
            margin-bottom: 1.2rem;
        }}

        .fvg-kicker {{
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .11em;
            text-transform: uppercase;
            color: var(--fvg-accent) !important;
            margin-bottom: .55rem;
        }}

        .fvg-hero-title {{
            color: var(--fvg-text) !important;
            font-size: clamp(2rem, 5vw, 3.35rem);
            line-height: 1.02;
            font-weight: 800;
            letter-spacing: -.045em;
            margin: 0 0 .8rem;
        }}

        .fvg-hero-subtitle {{
            max-width: 900px;
            font-size: 1.05rem;
            line-height: 1.65;
            color: var(--fvg-muted) !important;
            margin: 0;
        }}

        .fvg-pills {{
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1rem;
        }}

        .fvg-pill {{
            display: inline-flex;
            align-items: center;
            padding: .36rem .66rem;
            border: 1px solid #3b4a60;
            border-radius: 999px;
            background: #202b3d;
            color: var(--fvg-text) !important;
            font-size: .76rem;
            font-weight: 700;
            line-height: 1;
        }}

        /* Section headings */
        .fvg-section {{
            margin: 2.2rem 0 .9rem;
        }}

        .fvg-section-kicker {{
            color: var(--fvg-accent) !important;
            font-size: .7rem;
            font-weight: 800;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin-bottom: .32rem;
        }}

        .fvg-section-title {{
            color: var(--fvg-text) !important;
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 750;
            letter-spacing: -.025em;
            margin: 0 0 .38rem;
        }}

        .fvg-section-body {{
            color: var(--fvg-muted) !important;
            max-width: 900px;
            line-height: 1.65;
            margin: 0;
        }}

        /* Information cards */
        .fvg-card {{
            height: 100%;
            box-sizing: border-box;
            padding: 1rem 1.05rem;
            border: 1px solid var(--fvg-border);
            border-radius: 14px;
            background: var(--fvg-surface-2);
            box-shadow: 0 5px 18px rgba(0,0,0,.16);
        }}

        .fvg-card-title {{
            color: var(--fvg-text) !important;
            font-size: .96rem;
            font-weight: 750;
            margin-bottom: .38rem;
        }}

        .fvg-card-body {{
            color: var(--fvg-muted) !important;
            font-size: .91rem;
            line-height: 1.56;
        }}

        .fvg-big-value {{
            color: var(--fvg-text) !important;
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -.025em;
            margin: .2rem 0 .4rem;
        }}

        /* Callouts */
        .fvg-callout {{
            border: 1px solid #24496f;
            border-left: 4px solid var(--fvg-accent-strong);
            border-radius: 12px;
            padding: .95rem 1rem;
            background: var(--fvg-info-bg);
            box-shadow: 0 4px 16px rgba(0,0,0,.12);
            margin: .8rem 0 1.05rem;
        }}

        .fvg-callout.success {{
            border-color: #21683e;
            border-left-color: #22c55e;
            background: var(--fvg-success-bg);
        }}

        .fvg-callout.warning {{
            border-color: #8a5714;
            border-left-color: #f59e0b;
            background: var(--fvg-warning-bg);
        }}

        .fvg-callout.danger {{
            border-color: #8e3443;
            border-left-color: #fb7185;
            background: var(--fvg-danger-bg);
        }}

        .fvg-callout-title {{
            color: var(--fvg-text) !important;
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .34rem;
        }}

        .fvg-callout-body {{
            color: var(--fvg-info-text) !important;
            line-height: 1.62;
        }}

        .fvg-callout.success .fvg-callout-body {{
            color: var(--fvg-success-text) !important;
        }}

        .fvg-callout.warning .fvg-callout-body {{
            color: var(--fvg-warning-text) !important;
        }}

        .fvg-callout.danger .fvg-callout-body {{
            color: var(--fvg-danger-text) !important;
        }}

        /* Numbered method steps */
        .fvg-method-step {{
            display: grid;
            grid-template-columns: 2.15rem 1fr;
            gap: .72rem;
            align-items: start;
            padding: .82rem .92rem;
            margin-bottom: .58rem;
            border: 1px solid var(--fvg-border);
            border-radius: 11px;
            background: var(--fvg-surface-2);
        }}

        .fvg-step-num {{
            width: 2rem;
            height: 2rem;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #1e3a5f;
            color: #bfdbfe !important;
            border: 1px solid #315b87;
            font-weight: 800;
            font-size: .8rem;
        }}

        .fvg-step-text {{
            color: var(--fvg-text) !important;
            padding-top: .23rem;
            line-height: 1.55;
        }}

        /* Metrics */
        div[data-testid="stMetric"] {{
            border: 1px solid var(--fvg-border);
            border-radius: 13px;
            padding: .82rem .9rem;
            background: var(--fvg-surface-2);
            box-shadow: 0 4px 14px rgba(0,0,0,.13);
        }}

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * {{
            color: var(--fvg-muted) !important;
            font-weight: 700 !important;
        }}

        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * {{
            color: var(--fvg-text) !important;
            font-size: 1.42rem;
            letter-spacing: -.025em;
        }}

        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] * {{
            font-weight: 700 !important;
        }}

        /* Streamlit bordered containers */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px;
            border-color: var(--fvg-border) !important;
            background: var(--fvg-surface) !important;
        }}

        /* Tabs */
        [data-baseweb="tab-list"] {{
            gap: .28rem;
            padding: .22rem;
            border: 1px solid var(--fvg-border);
            border-radius: 12px;
            background: var(--fvg-surface) !important;
        }}

        [data-baseweb="tab"] {{
            height: 2.55rem;
            border-radius: 9px;
            padding-left: .9rem;
            padding-right: .9rem;
            color: var(--fvg-muted) !important;
        }}

        [data-baseweb="tab"] * {{
            color: inherit !important;
        }}

        [data-baseweb="tab"][aria-selected="true"] {{
            background: var(--fvg-surface-3) !important;
            color: var(--fvg-text) !important;
        }}

        /* Buttons */
        div.stButton > button,
        div[data-testid="stDownloadButton"] > button {{
            min-height: 2.55rem;
            border-radius: 10px !important;
            border: 1px solid #475569 !important;
            background: #1b2535 !important;
            color: var(--fvg-text) !important;
            font-weight: 700 !important;
        }}

        div.stButton > button *,
        div[data-testid="stDownloadButton"] > button * {{
            color: var(--fvg-text) !important;
        }}

        div.stButton > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {{
            border-color: var(--fvg-accent) !important;
            background: #223149 !important;
        }}

        div.stButton > button[kind="primary"],
        div[data-testid="stDownloadButton"] > button[kind="primary"] {{
            border-color: #60a5fa !important;
            background: #2563eb !important;
            color: #ffffff !important;
        }}

        div.stButton > button[kind="primary"]:hover {{
            background: #1d4ed8 !important;
        }}

        /* Expanders, alerts, tables and code */
        [data-testid="stExpander"] {{
            border: 1px solid var(--fvg-border) !important;
            border-radius: 12px !important;
            background: var(--fvg-surface) !important;
            overflow: hidden;
        }}

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary * {{
            color: var(--fvg-text) !important;
        }}

        [data-testid="stAlert"] {{
            border-radius: 12px;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid var(--fvg-border);
            border-radius: 12px;
            overflow: hidden;
        }}

        .stCodeBlock, pre, code {{
            border-radius: 10px !important;
        }}

        .stCodeBlock pre {{
            background: #0a0f18 !important;
            color: #e5edf7 !important;
            border: 1px solid #273449 !important;
        }}

        /* Inputs */
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {{
            background: var(--fvg-surface) !important;
            border-color: var(--fvg-border) !important;
            color: var(--fvg-text) !important;
        }}

        input, textarea {{
            color: var(--fvg-text) !important;
        }}

        label, label p {{
            color: var(--fvg-muted) !important;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: var(--fvg-sidebar) !important;
            border-right: 1px solid var(--fvg-border);
        }}

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p {{
            color: var(--fvg-text) !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
            color: var(--fvg-subtle) !important;
        }}

        .fvg-sidebar-status {{
            border: 1px solid var(--fvg-border);
            border-radius: 10px;
            padding: .67rem .74rem;
            background: var(--fvg-surface);
            margin: .55rem 0;
        }}

        .fvg-sidebar-label {{
            color: var(--fvg-subtle) !important;
            font-size: .7rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .2rem;
        }}

        .fvg-sidebar-value {{
            color: var(--fvg-text) !important;
            font-size: .86rem;
            font-weight: 700;
        }}

        /* Links remain obvious against the dark canvas. */
        .stApp a {{
            color: #7dd3fc;
        }}

        .stApp a:hover {{
            color: #bae6fd;
        }}

        @media (max-width: 700px) {{
            .block-container {{
                padding-top: .8rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }}
            .fvg-hero {{
                padding: 1.2rem 1.1rem;
            }}
            .fvg-hero-title {{
                font-size: 2rem;
            }}
            .fvg-hero-subtitle {{
                font-size: .96rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def pills(items: list[str]) -> str:
    if not items:
        return ""
    rendered = "".join(
        f'<span class="fvg-pill">{escape(str(item))}</span>'
        for item in items
    )
    return f'<div class="fvg-pills">{rendered}</div>'


def hero(kicker: str, title: str, subtitle: str, tags: list[str] | None = None) -> None:
    _render_html(
        '<div class="fvg-hero">'
        f'<div class="fvg-kicker">{escape(kicker)}</div>'
        f'<div class="fvg-hero-title">{escape(title)}</div>'
        f'<div class="fvg-hero-subtitle">{escape(subtitle)}</div>'
        f'{pills(tags or [])}'
        '</div>'
    )


def section_header(kicker: str, title: str, body: str = "") -> None:
    body_html = f'<div class="fvg-section-body">{escape(body)}</div>' if body else ""
    _render_html(
        '<div class="fvg-section">'
        f'<div class="fvg-section-kicker">{escape(kicker)}</div>'
        f'<div class="fvg-section-title">{escape(title)}</div>'
        f'{body_html}'
        '</div>'
    )


def info_card(title: str, body: str, value: str | None = None) -> None:
    value_html = f'<div class="fvg-big-value">{escape(value)}</div>' if value is not None else ""
    _render_html(
        '<div class="fvg-card">'
        f'<div class="fvg-card-title">{escape(title)}</div>'
        f'{value_html}'
        f'<div class="fvg-card-body">{escape(body)}</div>'
        '</div>'
    )


def callout(title: str, body: str, kind: str = "info") -> None:
    allowed = {"info", "success", "warning", "danger"}
    tone = kind if kind in allowed else "info"
    _render_html(
        f'<div class="fvg-callout {tone}">'
        f'<div class="fvg-callout-title">{escape(title)}</div>'
        f'<div class="fvg-callout-body">{escape(body)}</div>'
        '</div>'
    )


def method_steps(steps: list[str]) -> None:
    blocks = "".join(
        '<div class="fvg-method-step">'
        f'<div class="fvg-step-num">{number}</div>'
        f'<div class="fvg-step-text">{escape(step)}</div>'
        '</div>'
        for number, step in enumerate(steps, 1)
    )
    _render_html(blocks)


def sidebar_status(label: str, value: str) -> None:
    _render_html(
        '<div class="fvg-sidebar-status">'
        f'<div class="fvg-sidebar-label">{escape(label)}</div>'
        f'<div class="fvg-sidebar-value">{escape(value)}</div>'
        '</div>'
    )
