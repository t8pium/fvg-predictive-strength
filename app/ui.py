from __future__ import annotations

from html import escape

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --fvg-border: color-mix(in srgb, var(--text-color, #0f172a) 13%, transparent);
            --fvg-muted: color-mix(in srgb, var(--text-color, #0f172a) 66%, transparent);
            --fvg-soft: color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 72%, transparent);
            --fvg-primary-soft: color-mix(in srgb, var(--primary-color, #2563eb) 11%, transparent);
            --fvg-success-soft: color-mix(in srgb, #16a34a 12%, transparent);
            --fvg-warning-soft: color-mix(in srgb, #d97706 12%, transparent);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 1.35rem;
            padding-bottom: 4.5rem;
        }

        h1 {
            letter-spacing: -0.035em;
            line-height: 1.05 !important;
            margin-bottom: .55rem !important;
        }

        h2 {
            letter-spacing: -0.022em;
            margin-top: 2.2rem !important;
            margin-bottom: .7rem !important;
        }

        h3 {
            letter-spacing: -0.015em;
        }

        p, li {
            line-height: 1.62;
        }

        .fvg-hero {
            padding: 1.55rem 1.65rem 1.45rem;
            border: 1px solid var(--fvg-border);
            border-radius: 18px;
            background:
                linear-gradient(135deg, var(--fvg-primary-soft), transparent 48%),
                var(--fvg-soft);
            margin-bottom: 1.2rem;
        }

        .fvg-kicker {
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .11em;
            text-transform: uppercase;
            color: var(--primary-color, #2563eb);
            margin-bottom: .55rem;
        }

        .fvg-hero-title {
            font-size: clamp(2rem, 5vw, 3.35rem);
            line-height: 1.02;
            font-weight: 780;
            letter-spacing: -.045em;
            margin: 0 0 .8rem 0;
        }

        .fvg-hero-subtitle {
            max-width: 880px;
            font-size: 1.05rem;
            line-height: 1.65;
            color: var(--fvg-muted);
            margin: 0;
        }

        .fvg-pills {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: 1rem;
        }

        .fvg-pill {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            padding: .34rem .62rem;
            border: 1px solid var(--fvg-border);
            border-radius: 999px;
            font-size: .76rem;
            font-weight: 650;
            line-height: 1;
            background: color-mix(in srgb, var(--background-color, #fff) 76%, transparent);
        }

        .fvg-section {
            margin: 2.2rem 0 .9rem;
        }

        .fvg-section-kicker {
            font-size: .7rem;
            font-weight: 750;
            letter-spacing: .1em;
            text-transform: uppercase;
            color: var(--primary-color, #2563eb);
            margin-bottom: .32rem;
        }

        .fvg-section-title {
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 730;
            letter-spacing: -.025em;
            margin: 0 0 .38rem;
        }

        .fvg-section-body {
            color: var(--fvg-muted);
            max-width: 860px;
            line-height: 1.6;
            margin: 0;
        }

        .fvg-card {
            height: 100%;
            padding: 1rem 1.05rem;
            border: 1px solid var(--fvg-border);
            border-radius: 14px;
            background: var(--fvg-soft);
        }

        .fvg-card-title {
            font-size: .96rem;
            font-weight: 720;
            margin-bottom: .35rem;
        }

        .fvg-card-body {
            font-size: .9rem;
            color: var(--fvg-muted);
            line-height: 1.52;
        }

        .fvg-big-value {
            font-size: 1.5rem;
            font-weight: 760;
            letter-spacing: -.025em;
            margin: .2rem 0 .35rem;
        }

        .fvg-callout {
            border: 1px solid var(--fvg-border);
            border-left: 4px solid var(--primary-color, #2563eb);
            border-radius: 12px;
            padding: .9rem 1rem;
            background: var(--fvg-primary-soft);
            margin: .8rem 0 1.05rem;
        }

        .fvg-callout.success {
            border-left-color: #16a34a;
            background: var(--fvg-success-soft);
        }

        .fvg-callout.warning {
            border-left-color: #d97706;
            background: var(--fvg-warning-soft);
        }

        .fvg-callout-title {
            font-size: .78rem;
            font-weight: 760;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: .3rem;
        }

        .fvg-callout-body {
            line-height: 1.58;
            color: var(--text-color, #0f172a);
        }

        .fvg-method-step {
            display: grid;
            grid-template-columns: 2.15rem 1fr;
            gap: .7rem;
            align-items: start;
            padding: .78rem .9rem;
            margin-bottom: .55rem;
            border: 1px solid var(--fvg-border);
            border-radius: 11px;
            background: var(--fvg-soft);
        }

        .fvg-step-num {
            width: 2rem;
            height: 2rem;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--fvg-primary-soft);
            color: var(--primary-color, #2563eb);
            font-weight: 780;
            font-size: .8rem;
        }

        .fvg-step-text {
            padding-top: .23rem;
            line-height: 1.5;
        }

        .fvg-glossary-term {
            font-weight: 730;
            margin-bottom: .2rem;
        }

        .fvg-glossary-def {
            color: var(--fvg-muted);
            font-size: .88rem;
            line-height: 1.5;
        }

        .fvg-divider {
            height: 1px;
            background: var(--fvg-border);
            margin: 1.7rem 0;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--fvg-border);
            border-radius: 13px;
            padding: .78rem .88rem;
            background: var(--fvg-soft);
        }

        [data-testid="stMetricLabel"] {
            font-weight: 650;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.42rem;
            letter-spacing: -.025em;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
            border-color: var(--fvg-border) !important;
            background: color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 38%, transparent);
        }

        [data-baseweb="tab-list"] {
            gap: .3rem;
            padding: .22rem;
            border: 1px solid var(--fvg-border);
            border-radius: 12px;
            background: var(--fvg-soft);
        }

        [data-baseweb="tab"] {
            height: 2.5rem;
            border-radius: 9px;
            padding-left: .9rem;
            padding-right: .9rem;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--fvg-border);
            border-radius: 12px;
            overflow: hidden;
        }

        div.stButton > button {
            border-radius: 10px;
            min-height: 2.55rem;
            font-weight: 650;
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--fvg-border);
            border-radius: 12px;
            overflow: hidden;
        }

        code, pre {
            border-radius: 10px !important;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--fvg-border);
        }

        .fvg-sidebar-status {
            border: 1px solid var(--fvg-border);
            border-radius: 10px;
            padding: .65rem .72rem;
            background: var(--fvg-soft);
            margin: .55rem 0;
        }

        .fvg-sidebar-label {
            font-size: .7rem;
            font-weight: 730;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: var(--fvg-muted);
            margin-bottom: .2rem;
        }

        .fvg-sidebar-value {
            font-size: .86rem;
            font-weight: 650;
        }

        @media (max-width: 700px) {
            .block-container {padding-top: .8rem;}
            .fvg-hero {padding: 1.2rem 1.1rem;}
            .fvg-hero-title {font-size: 2rem;}
            .fvg-hero-subtitle {font-size: .96rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pills(items: list[str]) -> str:
    rendered = "".join(f'<span class="fvg-pill">{escape(str(item))}</span>' for item in items)
    return f'<div class="fvg-pills">{rendered}</div>'


def hero(kicker: str, title: str, subtitle: str, tags: list[str] | None = None) -> None:
    tags_html = pills(tags or [])
    st.markdown(
        f"""
        <div class="fvg-hero">
            <div class="fvg-kicker">{escape(kicker)}</div>
            <div class="fvg-hero-title">{escape(title)}</div>
            <p class="fvg-hero-subtitle">{escape(subtitle)}</p>
            {tags_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(kicker: str, title: str, body: str = "") -> None:
    body_html = f'<p class="fvg-section-body">{escape(body)}</p>' if body else ""
    st.markdown(
        f"""
        <div class="fvg-section">
            <div class="fvg-section-kicker">{escape(kicker)}</div>
            <div class="fvg-section-title">{escape(title)}</div>
            {body_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str, value: str | None = None) -> None:
    value_html = f'<div class="fvg-big-value">{escape(value)}</div>' if value else ""
    st.markdown(
        f"""
        <div class="fvg-card">
            <div class="fvg-card-title">{escape(title)}</div>
            {value_html}
            <div class="fvg-card-body">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout(title: str, body: str, kind: str = "info") -> None:
    css = "" if kind == "info" else f" {escape(kind)}"
    st.markdown(
        f"""
        <div class="fvg-callout{css}">
            <div class="fvg-callout-title">{escape(title)}</div>
            <div class="fvg-callout-body">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def method_steps(steps: list[str]) -> None:
    html = []
    for number, step in enumerate(steps, 1):
        html.append(
            f"""
            <div class="fvg-method-step">
                <div class="fvg-step-num">{number}</div>
                <div class="fvg-step-text">{escape(step)}</div>
            </div>
            """
        )
    st.markdown("".join(html), unsafe_allow_html=True)


def sidebar_status(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="fvg-sidebar-status">
            <div class="fvg-sidebar-label">{escape(label)}</div>
            <div class="fvg-sidebar-value">{escape(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
