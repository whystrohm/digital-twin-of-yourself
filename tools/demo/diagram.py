#!/usr/bin/env python3
"""Draw the how-it-works diagram as an HTML page holding one inline SVG.

make_demo.py renders it to assets/how-it-works.png. Palette only:
ground #07080A, ink #F6F5F2 and its alpha steps, signal #E4552A.
"""

import html

W, H = 1200, 760
LEFT = 176          # where the boxes start
BOX_W, BOX_H = 168, 64
GAP = 36
LANE_Y = [150, 300, 450, 600]

# kind: code (ink outline), model (signal outline), person (dashed), file (no outline, tinted)
LANES = [
    ("1", "Measure", [
        ("Your writing", ".md and .txt files", "file"),
        ("twin_scan.py", "redacts, then counts", "code"),
        ("patterns.json", "the numbers", "file"),
        ("twin_report.py", "inline charts", "code"),
        ("report.html", "offline, one file", "file"),
    ]),
    ("2", "Extract", [
        ("patterns.json", "plus samples", "file"),
        ("Interview", "5 questions at most", "person"),
        ("SKILL.md", "reads and classifies", "model"),
        ("twin.md", "the System Prompt", "file"),
        ("twin.rules.json", "what code can check", "file"),
    ]),
    ("3", "Enforce", [
        ("A draft", "yours or an AI's", "file"),
        ("twin_check.py", "rules, line by line", "code"),
        ("Pass or fail", "exit 0, 1 or 2", "file"),
        ("Pull request", "annotations on the diff", "file"),
    ]),
    ("4", "Improve", [
        ("Draft + edit", "what you changed", "file"),
        ("twin_diff.py", "finds the pattern", "code"),
        ("proposals.md", "nothing applied yet", "file"),
        ("You approve", "tick to accept", "person"),
        ("Changelog", "version +1, with evidence", "file"),
    ]),
]


def box_x(i):
    return LEFT + i * (BOX_W + GAP)


def box(x, y, name, sub, kind):
    cls = {"code": "code", "model": "model", "person": "person", "file": "file"}[kind]
    return (
        '<g class="box %s"><rect x="%d" y="%d" width="%d" height="%d" rx="2"/>'
        '<text class="name" x="%d" y="%d">%s</text>'
        '<text class="sub" x="%d" y="%d">%s</text></g>' % (
            cls, x, y, BOX_W, BOX_H, x + 14, y + 27, html.escape(name), x + 14, y + 47, html.escape(sub)))


def arrow(x1, y, x2):
    return ('<line class="arrow" x1="%d" y1="%d" x2="%d" y2="%d"/>'
            '<path class="head" d="M%d %d l-7 -4 v8 z"/>' % (x1, y, x2 - 7, y, x2, y))


def svg():
    parts = []
    parts.append('<text class="eyebrow" x="40" y="58">HOW IT WORKS</text>')
    parts.append('<text class="title" x="40" y="96">The model classifies. Code measures and checks.</text>')
    # legend
    lx = 760
    for i, (kind, label) in enumerate((("code", "Code: offline, same output every time"),
                                       ("model", "Model: reads and classifies"),
                                       ("person", "You: decide"))):
        y = 44 + i * 22
        parts.append('<g class="box %s"><rect x="%d" y="%d" width="22" height="14" rx="2"/></g>'
                     '<text class="legend" x="%d" y="%d">%s</text>' % (kind, lx, y, lx + 34, y + 12, html.escape(label)))
    for (num, label, boxes), y in zip(LANES, LANE_Y):
        parts.append('<line class="lane" x1="40" y1="%d" x2="%d" y2="%d"/>' % (y - 26, W - 40, y - 26))
        parts.append('<text class="num" x="40" y="%d">%s</text>' % (y + 30, num))
        parts.append('<text class="lanelabel" x="72" y="%d">%s</text>' % (y + 30, label.upper()))
        for i, (name, sub, kind) in enumerate(boxes):
            x = box_x(i)
            parts.append(box(x, y, name, sub, kind))
            if i < len(boxes) - 1:
                parts.append(arrow(x + BOX_W + 4, y + BOX_H // 2, x + BOX_W + GAP - 4))
    # Calibration loop: rules are checked against your own writing before they ship.
    rx = box_x(4) + BOX_W // 2
    parts.append('<path class="loop" d="M%d %d v26 H%d v-14"/>' % (rx, LANE_Y[1] + BOX_H, box_x(2) + BOX_W // 2,))
    parts.append('<path class="head sig" d="M%d %d l-4 7 h8 z"/>' % (box_x(2) + BOX_W // 2, LANE_Y[1] + BOX_H + 6))
    parts.append('<text class="note" x="%d" y="%d">calibrate: the rules must pass your own normal writing</text>' % (
        box_x(2) + BOX_W // 2 + 14, LANE_Y[1] + BOX_H + 22))
    parts.append('<text class="foot" x="40" y="%d">Everything in scripts/ runs offline on Python 3.9+, with no dependencies. '
                 'Emails, phone numbers and money amounts are redacted before anything is counted.</text>' % (H - 34))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">%s</svg>'
            % (W, H, W, H, "".join(parts)))


CSS = """
html,body{margin:0;background:#07080A}
svg{display:block}
.eyebrow{font:500 13px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.16em;fill:#E4552A}
.title{font:800 32px "Archivo",Arial,sans-serif;font-stretch:85%;fill:#F6F5F2;letter-spacing:-.01em}
.legend{font:13px "Archivo",Arial,sans-serif;fill:rgba(246,245,242,.66)}
.lane{stroke:rgba(246,245,242,.22);stroke-width:1}
.num{font:800 30px "Archivo",Arial,sans-serif;fill:#E4552A}
.lanelabel{font:500 13px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;fill:#F6F5F2}
.box rect{fill:rgba(246,245,242,.04);stroke:rgba(246,245,242,.22);stroke-width:1}
.box.code rect{stroke:#F6F5F2;stroke-width:1.5}
.box.model rect{stroke:#E4552A;stroke-width:2}
.box.person rect{stroke:#F6F5F2;stroke-width:1.5;stroke-dasharray:5 4}
.name{font:500 15px "IBM Plex Mono",ui-monospace,monospace;fill:#F6F5F2}
.sub{font:13px "Archivo",Arial,sans-serif;fill:rgba(246,245,242,.66)}
.arrow{stroke:rgba(246,245,242,.40);stroke-width:1.5}
.head{fill:rgba(246,245,242,.40)}.head.sig{fill:#E4552A}
.loop{fill:none;stroke:#E4552A;stroke-width:1.5;stroke-dasharray:4 4}
.note{font:13px "Archivo",Arial,sans-serif;fill:rgba(246,245,242,.66)}
.foot{font:13px "Archivo",Arial,sans-serif;fill:rgba(246,245,242,.40)}
"""


def page(font_css=""):
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s%s</style></head><body>%s</body></html>'
            % (font_css, CSS, svg()))
