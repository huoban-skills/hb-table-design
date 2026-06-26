#!/usr/bin/env python3
"""Convert the 表结构设计.md output into a single self-contained HTML file.

Images (er.png / flow.png) are inlined as base64 so the result is ONE file the
user can send to a customer and open in any browser — no external assets.

Usage:
    python3 md_to_html.py 表结构设计.md 表结构设计.html
    python3 md_to_html.py 表结构设计.md            # -> 表结构设计.html alongside source

Pure standard library. Supports the subset this skill emits: ATX headings,
pipe tables, images, blockquotes, links, bold, unordered lists, paragraphs.
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
import sys
from pathlib import Path

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f5f6f8;
  color: #1f2329;
  font-family: "PingFang SC", "Helvetica Neue", "Microsoft YaHei", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.75;
}
.page {
  max-width: 880px;
  margin: 32px auto;
  background: #fff;
  padding: 48px 56px 64px;
  border-radius: 12px;
  box-shadow: 0 2px 24px rgba(0,0,0,.06);
}
h1 { font-size: 28px; margin: 0 0 24px; padding-bottom: 16px; border-bottom: 2px solid #eef0f3; }
h2 { font-size: 22px; margin: 40px 0 16px; padding-left: 12px; border-left: 4px solid #3370ff; }
h3 { font-size: 18px; margin: 28px 0 12px; color: #3370ff; }
h4 { font-size: 16px; margin: 22px 0 10px; }
p { margin: 12px 0; }
a { color: #3370ff; text-decoration: none; }
a:hover { text-decoration: underline; }
img { max-width: 100%; height: auto; display: block; margin: 16px auto; border: 1px solid #eef0f3; border-radius: 8px; }
blockquote {
  margin: 16px 0;
  padding: 10px 16px;
  background: #f7f9ff;
  border-left: 4px solid #b9ccff;
  color: #5a6573;
  border-radius: 0 6px 6px 0;
}
blockquote p { margin: 4px 0; }
ul { margin: 12px 0; padding-left: 22px; }
li { margin: 4px 0; }
code { background: #f2f3f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: "SFMono-Regular", Consolas, monospace; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
th, td { border: 1px solid #e6e8eb; padding: 8px 12px; text-align: left; vertical-align: top; }
th { background: #f5f7fa; font-weight: 600; white-space: nowrap; }
tr:nth-child(even) td { background: #fafbfc; }
"""


def _inline(text: str) -> str:
    """Render inline markdown (escape first, then re-introduce safe tags)."""
    text = html.escape(text)
    # images ![alt](src) — leave src raw, resolved later
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img alt="\1" src="\2">', text)
    # links [text](url)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', text)
    # bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # inline code `code`
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    return text


def _embed_images(html_text: str, base_dir: Path) -> str:
    def repl(m: re.Match) -> str:
        src = m.group("src")
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        img_path = (base_dir / src).resolve()
        if not img_path.exists():
            return m.group(0)
        mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return m.group(0).replace(f'src="{src}"', f'src="data:{mime};base64,{b64}"')

    return re.sub(r'<img [^>]*src="(?P<src>[^"]+)"[^>]*>', repl, html_text)


def md_to_html_body(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # blank
        if not stripped:
            close_list()
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # table: current line and next line look like a pipe row + separator
        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            close_list()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("<table><thead><tr>")
            for c in header:
                out.append(f"<th>{_inline(c)}</th>")
            out.append("</tr></thead><tbody>")
            i += 2  # skip header + separator
            while i < n and "|" in lines[i] and lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{_inline(c)}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        # blockquote
        if stripped.startswith(">"):
            close_list()
            buf: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(_inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote>" + "".join(f"<p>{b}</p>" for b in buf) + "</blockquote>")
            continue

        # list item
        if re.match(r"^[-*]\s+", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped)
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue

        # standalone image paragraph or plain paragraph
        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    close_list()
    return "\n".join(out)


def convert(src: Path, dst: Path) -> None:
    md = src.read_text(encoding="utf-8")
    title = src.stem
    m = re.search(r"^#\s+(.*)$", md, re.MULTILINE)
    if m:
        title = m.group(1).strip()
    body = md_to_html_body(md)
    body = _embed_images(body, src.parent)
    doc = (
        "<!DOCTYPE html>\n"
        f'<html lang="zh-CN"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div class="page">{body}</div></body></html>'
    )
    dst.write_text(doc, encoding="utf-8")
    print(str(dst))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src = Path(argv[1])
    dst = Path(argv[2]) if len(argv) >= 3 else src.with_suffix(".html")
    convert(src, dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
