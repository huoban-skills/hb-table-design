#!/usr/bin/env python3
"""Convert 表结构设计.md to a self-contained HTML with interactive features.

Images embedded as base64. Includes copy PlantUML code, download flow SVG,
and download ER image — all client-side, no server needed.

Usage:
    python3 md_to_html.py 表结构设计.md
    python3 md_to_html.py 表结构设计.md output.html
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
.action-bar {
  display: flex; gap: 8px; justify-content: center; margin: 4px 0 20px;
}
.action-bar button {
  background: #f5f7fa; border: 1px solid #e0e4ea; border-radius: 6px;
  color: #3370ff; cursor: pointer; font-size: 13px; padding: 6px 16px;
  font-family: inherit; transition: all .2s;
}
.action-bar button:hover { background: #eef3ff; border-color: #b9ccff; }
.action-bar button:active { transform: scale(.97); }
.toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #1f2329; color: #fff; padding: 10px 24px; border-radius: 8px;
  font-size: 14px; opacity: 0; transition: opacity .3s; z-index: 999;
  pointer-events: none;
}
.toast.show { opacity: 1; }
"""

JS = """
function showToast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(function() { t.classList.remove('show'); }, 2000);
}
function b64ToText(b64) {
  var bytes = Uint8Array.from(atob(b64), function(c) { return c.charCodeAt(0); });
  return new TextDecoder().decode(bytes);
}
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(function() {
      showToast('PlantUML 代码已复制到剪贴板');
    });
  } else {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('PlantUML 代码已复制到剪贴板');
  }
}
function copyPlantUML() {
  var el = document.getElementById('puml-source');
  if (!el) return;
  copyText(b64ToText(el.textContent));
}
function downloadByAlt(alt, filename) {
  var img = document.querySelector('img[alt="' + alt + '"]');
  if (!img || !img.src.startsWith('data:')) return;
  var a = document.createElement('a');
  a.href = img.src;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
function downloadFlowSVG() { downloadByAlt('业务流程图', 'flow.svg'); }
function downloadERImage() { downloadByAlt('ER 图', 'er.png'); }
"""


def _inline(text: str) -> str:
    """Render inline markdown (escape first, then re-introduce safe tags)."""
    text = html.escape(text)
    text = re.sub(r"!\[(.*?)\]\((.*?)\)", r'<img alt="\1" src="\2">', text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
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

        if not stripped:
            close_list()
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            close_list()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("<table><thead><tr>")
            for c in header:
                out.append(f"<th>{_inline(c)}</th>")
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{_inline(c)}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        if stripped.startswith(">"):
            close_list()
            buf: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(_inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            out.append("<blockquote>" + "".join(f"<p>{b}</p>" for b in buf) + "</blockquote>")
            continue

        if re.match(r"^[-*]\s+", stripped):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped)
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue

        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    close_list()
    return "\n".join(out)


def _embed_assets(base_dir: Path) -> str:
    """Embed PlantUML source as hidden data for the copy button."""
    puml = base_dir / "er.puml"
    if puml.exists():
        b64 = base64.b64encode(puml.read_bytes()).decode("ascii")
        return f'<script type="text/plain" id="puml-source">{b64}</script>'
    return ""


def _insert_action_buttons(body: str, base_dir: Path) -> str:
    """Insert interactive buttons after flow and ER diagram images."""
    has_flow = (base_dir / "flow.svg").exists()
    has_puml = (base_dir / "er.puml").exists()
    has_er = (base_dir / "er.png").exists()

    if has_flow:
        btn = ('<div class="action-bar">'
               '<button onclick="downloadFlowSVG()">下载流程图</button></div>')
        body = re.sub(
            r'<p>(<img\s[^>]*alt="业务流程图"[^>]*>)</p>',
            lambda m: m.group(1) + "\n" + btn,
            body,
        )

    if has_puml or has_er:
        btns = []
        if has_puml:
            btns.append('<button onclick="copyPlantUML()">复制 PlantUML 代码</button>')
        if has_er:
            btns.append('<button onclick="downloadERImage()">下载 ER 图</button>')
        bar = '<div class="action-bar">' + "".join(btns) + "</div>"
        body = re.sub(
            r'<p>(<img\s[^>]*alt="ER 图"[^>]*>)</p>',
            lambda m: m.group(1) + "\n" + bar,
            body,
        )

    return body


def convert(src: Path, dst: Path) -> None:
    md = src.read_text(encoding="utf-8")
    base_dir = src.parent
    title = src.stem
    m = re.search(r"^#\s+(.*)$", md, re.MULTILINE)
    if m:
        title = m.group(1).strip()
    body = md_to_html_body(md)
    body = _embed_images(body, base_dir)
    body = _insert_action_buttons(body, base_dir)
    assets = _embed_assets(base_dir)
    doc = (
        "<!DOCTYPE html>\n"
        f'<html lang="zh-CN"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div class="page">{body}</div>'
        f"{assets}"
        f'<div id="toast" class="toast"></div>'
        f"<script>{JS}</script>"
        f"</body></html>"
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
