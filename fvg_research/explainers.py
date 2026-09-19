from __future__ import annotations

from html import escape


WIDTH = 900
HEIGHT = 330


def _svg(title: str, subtitle: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(title)}">
<rect width="900" height="330" rx="18" fill="#0d1117"/>
<rect x="1" y="1" width="898" height="328" rx="17" fill="none" stroke="#30363d"/>
<text x="34" y="42" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="22" font-weight="700">{escape(title)}</text>
<text x="34" y="66" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">{escape(subtitle)}</text>
{body}
</svg>"""


def _candle(x: int, o: int, h: int, l: int, c: int, up: bool = True) -> str:
    fill = "#3fb950" if up else "#f85149"
    top, bottom = min(o, c), max(o, c)
    return (
        f'<line x1="{x}" y1="{h}" x2="{x}" y2="{l}" stroke="{fill}" stroke-width="3"/>'
        f'<rect x="{x-9}" y="{top}" width="18" height="{max(bottom-top,4)}" rx="2" fill="{fill}"/>'
    )


def _label(x: int, y: int, text: str, anchor: str = "middle", color: str = "#c9d1d9", size: int = 12) -> str:
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}">{escape(text)}</text>'


def experiment_svg(exp_id: str) -> str:
    if exp_id == "raw_fill":
        body = (
            _candle(145, 196, 154, 220, 170, True)
            + _candle(215, 185, 150, 215, 202, False)
            + _candle(285, 130, 105, 150, 118, True)
            + '<rect x="115" y="150" width="205" height="44" fill="#58a6ff" fill-opacity=".16" stroke="#58a6ff" stroke-dasharray="5 4"/>'
            + '<line x1="115" y1="150" x2="320" y2="150" stroke="#58a6ff"/>'
            + '<line x1="115" y1="172" x2="320" y2="172" stroke="#d2a8ff" stroke-dasharray="4 4"/>'
            + '<line x1="115" y1="194" x2="320" y2="194" stroke="#58a6ff"/>'
            + _label(350, 154, "near edge", "start")
            + _label(350, 176, "midpoint", "start")
            + _label(350, 198, "far edge", "start")
            + '<path d="M450 170 C540 90 620 115 705 158" fill="none" stroke="#f0f6fc" stroke-width="3"/>'
            + '<path d="M705 158 L689 151 L694 168 Z" fill="#f0f6fc"/>'
            + _label(575, 104, "future price path")
            + _label(575, 232, "Question: which FVG level is touched before each horizon?")
        )
        return _svg("Raw fill-rate experiment", "Measure touch, midpoint and full-fill behavior without controls.", body)

    if exp_id == "matched_attraction":
        body = (
            '<rect x="55" y="98" width="335" height="160" rx="14" fill="#161b22" stroke="#30363d"/>'
            '<rect x="510" y="98" width="335" height="160" rx="14" fill="#161b22" stroke="#30363d"/>'
            + _label(222, 125, "REAL FVG", color="#58a6ff", size=13)
            + _label(677, 125, "MATCHED ORDINARY ZONE", color="#d2a8ff", size=13)
            + '<rect x="115" y="168" width="160" height="40" fill="#58a6ff" fill-opacity=".18" stroke="#58a6ff"/>'
            + '<rect x="570" y="168" width="160" height="40" fill="#d2a8ff" fill-opacity=".18" stroke="#d2a8ff"/>'
            + '<line x1="95" y1="150" x2="295" y2="150" stroke="#8b949e" stroke-dasharray="4 4"/>'
            + '<line x1="550" y1="150" x2="750" y2="150" stroke="#8b949e" stroke-dasharray="4 4"/>'
            + _label(222, 226, "same direction · width/ATR · distance/ATR")
            + _label(677, 226, "similar session · volatility · trend · time bucket")
            + '<path d="M404 178 L496 178" stroke="#f0f6fc" stroke-width="2"/>'
            + '<path d="M496 178 L482 170 L482 186 Z" fill="#f0f6fc"/>'
            + _label(450, 164, "compare")
        )
        return _svg("Matched-zone attraction", "Test whether the FVG label adds attraction beyond geometry and broad state.", body)

    if exp_id == "age_decay":
        xs = [120, 260, 390, 540, 720]
        labels = ["formation", "1 bar", "3 bars", "5 bars", "10 / 20"]
        body = '<line x1="120" y1="175" x2="760" y2="175" stroke="#8b949e" stroke-width="3"/>'
        for x, text in zip(xs, labels):
            body += f'<circle cx="{x}" cy="175" r="8" fill="#58a6ff"/>'
            body += _label(x, 205, text)
        body += '<path d="M260 135 L720 135" stroke="#3fb950" stroke-width="5" stroke-linecap="round"/>'
        body += _label(490, 120, "only zones still untouched survive into the next question", color="#3fb950")
        body += _label(450, 252, "Conditional probability, not another cumulative fill-rate chart.")
        return _svg("FVG age decay", "Remove already-touched zones before asking whether an older gap still carries information.", body)

    if exp_id == "continuation":
        body = (
            _candle(125, 205, 170, 225, 180, True)
            + _candle(190, 176, 145, 194, 154, True)
            + _candle(255, 150, 115, 164, 125, True)
            + '<path d="M100 235 L285 105" stroke="#58a6ff" stroke-width="4"/>'
            + '<path d="M285 105 L268 111 L279 124 Z" fill="#58a6ff"/>'
            + _label(190, 253, "FVG-forming displacement")
            + '<rect x="405" y="112" width="185" height="128" rx="12" fill="#161b22" stroke="#30363d"/>'
            + _label(497, 142, "MATCH MOVE")
            + _label(497, 170, "direction")
            + _label(497, 190, "move size / ATR")
            + _label(497, 210, "body size / ATR + state")
            + '<path d="M635 175 L790 128" stroke="#3fb950" stroke-width="4"/>'
            + '<path d="M635 175 L790 215" stroke="#f85149" stroke-width="4"/>'
            + _label(718, 108, "future signed return?")
        )
        return _svg("Formation continuation", "Compare FVG-forming displacement with similar non-FVG moves.", body)

    if exp_id == "retest":
        body = (
            '<rect x="120" y="135" width="300" height="70" fill="#58a6ff" fill-opacity=".16" stroke="#58a6ff"/>'
            + '<line x1="120" y1="135" x2="420" y2="135" stroke="#58a6ff"/>'
            + '<line x1="120" y1="205" x2="420" y2="205" stroke="#58a6ff"/>'
            + '<path d="M75 92 C200 100 280 116 305 139 C335 166 338 185 305 226" fill="none" stroke="#f0f6fc" stroke-width="3"/>'
            + '<circle cx="305" cy="139" r="6" fill="#f0f6fc"/>'
            + _label(305, 120, "first near-edge touch")
            + '<path d="M305 226 L500 95" stroke="#3fb950" stroke-width="4"/>'
            + '<path d="M305 226 L500 205" stroke="#f85149" stroke-width="4"/>'
            + _label(550, 102, "rejection target first = success", "start", "#3fb950")
            + _label(550, 210, "far edge first = failure", "start", "#f85149")
        )
        return _svg("First-touch retest reaction", "After first contact, race rejection against full traversal.", body)

    if exp_id == "midpoint":
        body = (
            '<rect x="150" y="110" width="300" height="130" fill="#58a6ff" fill-opacity=".13" stroke="#58a6ff"/>'
            + '<line x1="150" y1="110" x2="450" y2="110" stroke="#58a6ff"/>'
            + '<line x1="150" y1="175" x2="450" y2="175" stroke="#d2a8ff" stroke-width="3"/>'
            + '<line x1="150" y1="240" x2="450" y2="240" stroke="#58a6ff"/>'
            + '<circle cx="300" cy="175" r="8" fill="#d2a8ff"/>'
            + '<path d="M300 175 L300 118" stroke="#3fb950" stroke-width="4"/>'
            + '<path d="M300 175 L300 232" stroke="#f85149" stroke-width="4"/>'
            + _label(475, 115, "near edge", "start")
            + _label(475, 179, "CE / 50%", "start", "#d2a8ff")
            + _label(475, 244, "far edge", "start")
            + _label(675, 145, "equal distance")
            + _label(675, 170, "from midpoint")
            + _label(675, 205, "Which boundary trades first?")
        )
        return _svg("Midpoint / CE race", "Start only after exact midpoint trade so near and far edges are geometrically symmetric.", body)

    if exp_id == "body_acceptance":
        body = '<rect x="140" y="105" width="320" height="160" fill="#58a6ff" fill-opacity=".12" stroke="#58a6ff"/>'
        for i, pct in enumerate(["0%", "25%", "50%", "75%", "100%"]):
            y = 105 + i * 40
            body += f'<line x1="140" y1="{y}" x2="460" y2="{y}" stroke="#30363d"/>'
            body += _label(480, y + 4, pct, "start")
        body += _candle(320, 145, 123, 235, 192, False)
        body += '<circle cx="320" cy="192" r="7" fill="#d2a8ff"/>'
        body += _label(320, 286, "classify the signal candle by body-close depth")
        body += _label(650, 150, "entry = close", "start")
        body += _label(650, 180, "target = near edge", "start", "#3fb950")
        body += _label(650, 210, "stop = far edge", "start", "#f85149")
        return _svg("Candle-body acceptance around CE", "Measure how deeply an opposite-color signal candle closes inside the gap.", body)

    if exp_id == "controls_regimes":
        body = (
            '<rect x="80" y="115" width="190" height="120" rx="12" fill="#161b22" stroke="#30363d"/>'
            + _label(175, 143, "INPUT FEATURES")
            + _label(175, 168, "distance / ATR")
            + _label(175, 188, "width / ATR")
            + _label(175, 208, "volatility · trend · time")
            + '<path d="M285 175 L410 175" stroke="#f0f6fc" stroke-width="3"/>'
            + '<rect x="425" y="125" width="190" height="100" rx="50" fill="#58a6ff" fill-opacity=".18" stroke="#58a6ff"/>'
            + _label(520, 164, "CONTROLLED")
            + _label(520, 185, "LOGISTIC MODEL")
            + '<path d="M630 175 L735 175" stroke="#f0f6fc" stroke-width="3"/>'
            + '<rect x="750" y="140" width="90" height="70" rx="10" fill="#3fb950" fill-opacity=".14" stroke="#3fb950"/>'
            + _label(795, 168, "FVG")
            + _label(795, 188, "odds ratio")
            + _label(450, 270, "Question: after explicit controls, how much information remains in is_fvg?")
        )
        return _svg("Distance, regimes & controlled model", "Separate the FVG label from obvious geometric and market-state predictors.", body)

    if exp_id == "oos":
        body = (
            '<line x1="90" y1="172" x2="810" y2="172" stroke="#8b949e" stroke-width="4"/>'
            + '<rect x="90" y="142" width="500" height="60" rx="8" fill="#58a6ff" fill-opacity=".22" stroke="#58a6ff"/>'
            + '<rect x="590" y="142" width="220" height="60" rx="8" fill="#d2a8ff" fill-opacity=".22" stroke="#d2a8ff"/>'
            + _label(340, 177, "EARLY 70%")
            + _label(700, 177, "LATER 30%")
            + _label(340, 225, "measure effect")
            + _label(700, 225, "measure again")
            + _label(450, 273, "A stable effect should not depend entirely on the earlier sample.")
        )
        return _svg("Chronological robustness", "Preserve time ordering and compare earlier versus later matched-event effects.", body)

    raise KeyError(f"Unknown experiment: {exp_id}")


def research_flow_svg() -> str:
    boxes = [
        (35, 128, 125, "Licensed raw", "Databento / OHLCV"),
        (190, 128, 125, "Active MNQ", "volume-selected"),
        (345, 128, 125, "FVG detector", "completed candles"),
        (500, 78, 155, "Detailed 1m", "01 · 02 · 08 · 09"),
        (500, 178, 155, "Multi-timeframe", "02 · 03 · 04 · 05 · 09"),
        (690, 78, 150, "Midpoint", "06"),
        (690, 178, 150, "CE execution", "07"),
    ]
    body = ""
    for x, y, w, title, sub in boxes:
        body += f'<rect x="{x}" y="{y}" width="{w}" height="66" rx="12" fill="#161b22" stroke="#30363d"/>'
        body += _label(x + w // 2, y + 27, title, size=13)
        body += _label(x + w // 2, y + 48, sub, color="#8b949e", size=11)
    arrows = [
        (160, 161, 190, 161), (315, 161, 345, 161),
        (470, 150, 500, 111), (470, 172, 500, 211),
        (655, 111, 690, 111), (655, 211, 690, 211),
    ]
    for x1, y1, x2, y2 in arrows:
        body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#58a6ff" stroke-width="2"/>'
    body += _label(450, 285, "Four canonical computational suites feed nine reader-facing experiments.")
    return _svg("Research architecture", "The presentation layer does not duplicate the heavy analysis.", body)
