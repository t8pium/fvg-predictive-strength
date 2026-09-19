from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference_results" / "reference_metrics.json"
OUT = ROOT / "reference_results" / "figures"

WIDTH = 920
HEIGHT = 460
MARGIN = {"left": 78, "right": 24, "top": 68, "bottom": 78}
PLOT_W = WIDTH - MARGIN["left"] - MARGIN["right"]
PLOT_H = HEIGHT - MARGIN["top"] - MARGIN["bottom"]


def esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _header(title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        f'<text x="{MARGIN["left"]}" y="32" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="22" font-weight="700">{esc(title)}</text>',
        f'<text x="{MARGIN["left"]}" y="53" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">{esc(subtitle)}</text>',
    ]


def _axes(parts: list[str], ymin: float, ymax: float, y_suffix: str = "") -> tuple[float, float]:
    if ymin == ymax:
        ymax = ymin + 1
    left, top = MARGIN["left"], MARGIN["top"]
    bottom = top + PLOT_H
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{left + PLOT_W}" y2="{bottom}" stroke="#30363d"/>')
    for i in range(5):
        value = ymin + (ymax - ymin) * i / 4
        y = bottom - PLOT_H * i / 4
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + PLOT_W}" y2="{y:.1f}" stroke="#21262d"/>')
        parts.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">{value:.2f}{esc(y_suffix)}</text>')
    return left, bottom


def line_chart(labels: list[str], values: list[float], title: str, subtitle: str, y_suffix: str = "") -> str:
    ymin = min(0.0, min(values))
    ymax = max(values) * 1.08 if max(values) > 0 else 1.0
    parts = _header(title, subtitle)
    left, bottom = _axes(parts, ymin, ymax, y_suffix)
    points = []
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + (PLOT_W * i / max(1, len(labels) - 1))
        y = bottom - (value - ymin) / (ymax - ymin) * PLOT_H
        points.append(f"{x:.1f},{y:.1f}")
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#58a6ff"/>')
        parts.append(f'<text x="{x:.1f}" y="{bottom + 24}" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">{esc(label)}</text>')
    parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#58a6ff" stroke-width="3"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def bar_chart(labels: list[str], values: list[float], title: str, subtitle: str, y_suffix: str = "") -> str:
    low = min(values + [0.0])
    high = max(values + [0.0])
    span = max(high - low, 1e-9)
    ymin = low - span * 0.12
    ymax = high + span * 0.12
    parts = _header(title, subtitle)
    left, bottom = _axes(parts, ymin, ymax, y_suffix)
    zero_y = bottom - (0 - ymin) / (ymax - ymin) * PLOT_H
    slot = PLOT_W / len(labels)
    bar_w = slot * 0.58
    for i, (label, value) in enumerate(zip(labels, values)):
        x = left + slot * i + (slot - bar_w) / 2
        value_y = bottom - (value - ymin) / (ymax - ymin) * PLOT_H
        y = min(value_y, zero_y)
        height = max(abs(value_y - zero_y), 1)
        fill = "#3fb950" if value >= 0 else "#f85149"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" rx="3" fill="{fill}"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{bottom + 24}" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">{esc(label)}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="11">{value:+.2f}{esc(y_suffix)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def grouped_bar(labels: list[str], first: list[float], second: list[float], first_name: str, second_name: str, title: str, subtitle: str, y_suffix: str = "") -> str:
    values = first + second + [0.0]
    low, high = min(values), max(values)
    span = max(high - low, 1e-9)
    ymin, ymax = low - span * 0.12, high + span * 0.12
    parts = _header(title, subtitle)
    left, bottom = _axes(parts, ymin, ymax, y_suffix)
    zero_y = bottom - (0 - ymin) / (ymax - ymin) * PLOT_H
    slot = PLOT_W / len(labels)
    bar_w = slot * 0.28
    for i, label in enumerate(labels):
        center = left + slot * i + slot / 2
        for offset, value, fill in ((-bar_w * 0.58, first[i], "#58a6ff"), (bar_w * 0.58, second[i], "#d2a8ff")):
            x = center + offset - bar_w / 2
            value_y = bottom - (value - ymin) / (ymax - ymin) * PLOT_H
            y = min(value_y, zero_y)
            height = max(abs(value_y - zero_y), 1)
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" rx="3" fill="{fill}"/>')
        parts.append(f'<text x="{center:.1f}" y="{bottom + 24}" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">{esc(label)}</text>')
    parts.append(f'<rect x="{WIDTH - 250}" y="24" width="12" height="12" fill="#58a6ff"/><text x="{WIDTH - 232}" y="34" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="11">{esc(first_name)}</text>')
    parts.append(f'<rect x="{WIDTH - 130}" y="24" width="12" height="12" fill="#d2a8ff"/><text x="{WIDTH - 112}" y="34" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="11">{esc(second_name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render(reference: dict) -> dict[str, str]:
    exp = reference["experiments"]
    raw = exp["raw_fill"]
    matched = exp["matched_attraction"]["deep_1m"]
    midpoint = exp["midpoint"]["reaction"]
    oos = exp["oos"]["five_bar"]
    return {
        "01_fill_curve.svg": line_chart(
            ["5m", "15m", "30m", "60m", "120m", "240m", "~1d", "~3d"],
            [x * 100 for x in raw["touch_rate"]],
            "Raw FVG revisit probability",
            "Published 1-minute MNQ sample",
            "%",
        ),
        "02_matched_advantage.svg": bar_chart(
            [row["horizon"] for row in matched],
            [row["difference_pp"] for row in matched],
            "Incremental FVG attraction versus matched controls",
            "Most of the excess attraction is concentrated near formation",
            " pp",
        ),
        "03_midpoint_reaction.svg": grouped_bar(
            [row["timeframe"] for row in midpoint],
            [row["fvg"] for row in midpoint],
            [row["control"] for row in midpoint],
            "FVG",
            "Control",
            "Midpoint / CE rejection race",
            "Published rejection rates after exact midpoint trade",
            "%",
        ),
        "04_oos_robustness.svg": grouped_bar(
            [row["timeframe"] for row in oos],
            [row["train_pp"] for row in oos],
            [row["test_pp"] for row in oos],
            "Early 70%",
            "Later 30%",
            "Chronological robustness",
            "Five-native-bar FVG minus control difference",
            " pp",
        ),
    }


def main() -> int:
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in render(reference).items():
        (OUT / name).write_text(content, encoding="utf-8")
        print("Wrote", OUT / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
