#!/usr/bin/env python3
"""Render an L1 business flow (grouped, linear, no branches) to a clean SVG.

Replaces PlantUML for the flow diagram: full style control, scales crisply,
embeds in both Markdown and the single-file HTML, and needs NO network.

Input: a JSON file describing ordered groups, each with ordered steps.
Output: a single .svg.

Usage:
    python3 flow_render.py flow.json flow.svg

A step is either a plain string, or an object with an optional "table"/"tables"
naming the table(s) that step operates on — rendered as a second line in the
card so the builder sees the business-step → data-table mapping.

flow.json:
{
  "groups": [
    {"name": "达人运营", "steps": [
      {"text": "建联达人", "table": "达人"},
      {"text": "达人签约", "table": "达人"},
      {"text": "数据监管", "table": "达人数据监管"}
    ]},
    {"name": "单曲制作", "steps": [
      {"text": "词曲采买 / Demo 匹配", "tables": ["Demo 采买", "词曲拓展记录"]},
      {"text": "立项单曲", "table": "单曲项目"}
    ]}
  ]
}
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

# Per-group accent palette (container tint, accent line/text), cycled.
PALETTE = [
    ("#eef3ff", "#3370ff"),
    ("#e7f7f2", "#10b981"),
    ("#f4edff", "#8b5cf6"),
    ("#fff3e9", "#f97316"),
    ("#fdeef2", "#ec4899"),
]

PAD = 24            # canvas padding
GROUP_PAD_X = 20    # horizontal padding inside a group container
HEADER_H = 34       # group header band height
STEP_W = 250
STEP_H = 56         # two-line card: step name + mapped table
STEP_GAP = 26       # vertical gap between steps (holds the arrow)
GROUP_GAP = 32      # vertical gap between group containers
GROUP_BOTTOM = 18   # padding below last step inside a group
FS_STEP = 15
FS_HEADER = 14
FONT = '\'PingFang SC\', \'Helvetica Neue\', \'Microsoft YaHei\', Arial, sans-serif'


def _char_w(ch: str, fs: float) -> float:
    o = ord(ch)
    if o > 0x2E7F:      # CJK / full-width
        return fs
    if ch == " ":
        return fs * 0.3
    return fs * 0.56


def text_width(s: str, fs: float) -> float:
    return sum(_char_w(c, fs) for c in s)


def wrap(s: str, max_w: float, fs: float, max_lines: int = 2) -> list[str]:
    """Greedy wrap. ASCII runs stay atomic; CJK breaks per char."""
    tokens = re.findall(r"[A-Za-z0-9]+|.", s)
    lines = [""]
    for t in tokens:
        if t == " " and lines[-1] == "":
            continue
        trial = lines[-1] + t
        if text_width(trial, fs) > max_w and lines[-1]:
            if len(lines) >= max_lines:
                lines[-1] = trial          # overflow rather than drop
            else:
                lines.append(t if t != " " else "")
        else:
            lines[-1] = trial
    return [ln for ln in lines if ln] or [""]


def render(data: dict, out: Path) -> None:
    groups = data.get("groups", [])
    group_w = STEP_W + 2 * GROUP_PAD_X
    width = group_w + 2 * PAD
    cx = PAD + group_w / 2

    boxes: list[dict] = []   # step boxes
    conts: list[dict] = []   # group containers
    arrows: list[tuple[float, float, float]] = []  # (x, y1, y2)

    y = PAD
    for gi, g in enumerate(groups):
        tint, accent = PALETTE[gi % len(PALETTE)]
        top = y
        sy = top + HEADER_H + 8
        steps = g.get("steps", [])
        for si, step in enumerate(steps):
            if isinstance(step, str):
                text, tables = step, []
            else:
                text = step.get("text", "")
                t = step.get("tables") or step.get("table") or []
                tables = [t] if isinstance(t, str) else list(t)
            boxes.append({"x": PAD + GROUP_PAD_X, "y": sy, "text": text, "tables": tables, "accent": accent})
            if si < len(steps) - 1:
                arrows.append((cx, sy + STEP_H, sy + STEP_H + STEP_GAP))
            sy += STEP_H + STEP_GAP
        bottom = sy - STEP_GAP + GROUP_BOTTOM
        conts.append({"y": top, "h": bottom - top, "name": g.get("name", ""), "tint": tint, "accent": accent})
        y = bottom
        if gi < len(groups) - 1:
            arrows.append((cx, y, y + GROUP_GAP))
        y += GROUP_GAP
    height = y - GROUP_GAP + PAD

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="0 0 {width} {height:.0f}" font-family="{FONT}">'
    )
    p.append(
        '<defs>'
        '<marker id="arw" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M0,0 L6,3 L0,6 Z" fill="#9aa3b2"/></marker>'
        '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#1f2329" flood-opacity="0.10"/></filter>'
        '</defs>'
    )
    p.append(f'<rect x="0" y="0" width="{width}" height="{height:.0f}" fill="#ffffff"/>')

    # group containers (back)
    for c in conts:
        p.append(
            f'<rect x="{PAD}" y="{c["y"]:.0f}" width="{group_w}" height="{c["h"]:.0f}" rx="14" '
            f'fill="{c["tint"]}" stroke="{c["accent"]}" stroke-opacity="0.35" stroke-width="1"/>'
        )
        p.append(
            f'<text x="{PAD + GROUP_PAD_X}" y="{c["y"] + 23:.0f}" font-size="{FS_HEADER}" '
            f'font-weight="700" fill="{c["accent"]}">{html.escape(c["name"])}</text>'
        )

    # arrows (middle)
    for x, y1, y2 in arrows:
        p.append(
            f'<line x1="{x:.0f}" y1="{y1:.0f}" x2="{x:.0f}" y2="{y2 - 2:.0f}" '
            f'stroke="#9aa3b2" stroke-width="1.5" marker-end="url(#arw)"/>'
        )

    # step boxes (front)
    for b in boxes:
        p.append(
            f'<rect x="{b["x"]}" y="{b["y"]:.0f}" width="{STEP_W}" height="{STEP_H}" rx="9" '
            f'fill="#ffffff" stroke="{b["accent"]}" stroke-width="1.5" filter="url(#sh)"/>'
        )
        bx = b["x"] + STEP_W / 2
        if b["tables"]:
            # two-line: step name (dark) + mapped table(s) (accent)
            name = wrap(b["text"], STEP_W - 24, FS_STEP, max_lines=1)[0]
            p.append(
                f'<text x="{bx:.0f}" y="{b["y"] + 23:.0f}" font-size="{FS_STEP}" '
                f'fill="#1f2329" text-anchor="middle">{html.escape(name)}</text>'
            )
            tbl = "▸ " + " · ".join(b["tables"])
            p.append(
                f'<text x="{bx:.0f}" y="{b["y"] + 42:.0f}" font-size="12" '
                f'fill="{b["accent"]}" text-anchor="middle">{html.escape(tbl)}</text>'
            )
        else:
            lines = wrap(b["text"], STEP_W - 24, FS_STEP)
            lh = FS_STEP * 1.3
            cy = b["y"] + STEP_H / 2
            start = cy - (len(lines) - 1) * lh / 2 + FS_STEP * 0.35
            for i, ln in enumerate(lines):
                p.append(
                    f'<text x="{bx:.0f}" y="{start + i * lh:.1f}" font-size="{FS_STEP}" '
                    f'fill="#1f2329" text-anchor="middle">{html.escape(ln)}</text>'
                )

    p.append("</svg>")
    out.write_text("".join(p), encoding="utf-8")
    print(str(out))


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    render(data, Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
