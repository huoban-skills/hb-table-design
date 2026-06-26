#!/usr/bin/env python3
"""Render PlantUML source to PNG/SVG via official PlantUML server.

Usage:
    python3 plantuml_render.py input.puml output.png
    python3 plantuml_render.py input.puml output.svg

No Java, Graphviz, or curl required. Requires network access to www.plantuml.com.
"""
from __future__ import annotations

import sys
import ssl
import zlib
import urllib.request
from pathlib import Path

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

# Injected before encoding; not exposed in the user-facing .puml output
ER_STYLE = """\
skinparam defaultFontName "PingFang SC, Helvetica Neue, Arial"
skinparam defaultFontSize 13
skinparam BackgroundColor #FFFFFF
skinparam Shadowing false
skinparam Nodesep 45
skinparam Ranksep 55
skinparam ArrowColor #8A94A6
skinparam ArrowThickness 1.3
skinparam ArrowFontColor #5A6573
skinparam ArrowFontSize 12

skinparam package {
  BackgroundColor #F6F8FC
  BorderColor #C7D0E0
  BorderThickness 1
  FontColor #1F2329
  FontSize 14
  FontStyle bold
}

skinparam jsonBackgroundColor #FFFFFF
skinparam jsonBorderColor #C7D0E0
skinparam jsonFontColor #1F2329
skinparam jsonHeaderBackgroundColor #3370FF
skinparam jsonHeaderFontColor #FFFFFF
"""


def inject_style(text: str) -> str:
    """Insert ER_STYLE after the @startuml line without modifying the source file."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("@startuml"):
            lines.insert(i + 1, ER_STYLE)
            return "".join(lines)
    return text


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return "".join(ALPHABET[c & 0x3F] for c in (c1, c2, c3, c4))


def plantuml_encode(text: str) -> str:
    compressor = zlib.compressobj(level=9, wbits=-15)
    data = compressor.compress(text.encode("utf-8")) + compressor.flush()
    result: list[str] = []
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        if len(chunk) == 3:
            result.append(_append3bytes(chunk[0], chunk[1], chunk[2]))
        elif len(chunk) == 2:
            result.append(_append3bytes(chunk[0], chunk[1], 0)[:3])
        else:
            result.append(_append3bytes(chunk[0], 0, 0)[:2])
    return "".join(result)


def _make_ctx(verify: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch(url: str) -> tuple[bytes, str]:
    import urllib.error
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # Try with SSL verification first; fall back to unverified (common on macOS)
    for verify in (True, False):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_make_ctx(verify)) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.URLError as e:
            is_ssl_err = isinstance(e.reason, ssl.SSLCertVerificationError) or isinstance(e.reason, ssl.SSLError)
            if not verify or not is_ssl_err:
                raise
    raise RuntimeError("unreachable")


def render(input_path: Path, output_path: Path) -> None:
    text = input_path.read_text(encoding="utf-8")
    suffix = output_path.suffix.lower().lstrip(".") or "png"
    if suffix not in {"png", "svg"}:
        raise SystemExit("output extension must be .png or .svg")

    url = f"https://www.plantuml.com/plantuml/{suffix}/{plantuml_encode(inject_style(text))}"
    data, content_type = fetch(url)

    if suffix == "png" and not data.startswith(b"\x89PNG"):
        raise SystemExit(f"render failed: expected PNG, got {content_type}, {len(data)} bytes")
    if suffix == "svg" and b"<svg" not in data[:500].lower():
        raise SystemExit(f"render failed: expected SVG, got {content_type}, {len(data)} bytes")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    if suffix == "png":
        _remove_header_gray(output_path)
    print(str(output_path))


def _remove_header_gray(path: Path) -> None:
    """Replace PlantUML's hardcoded header gray (#F1F1F1) with white."""
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(path).convert("RGBA")
        arr = np.array(img)
        mask = (arr[:,:,0] == 241) & (arr[:,:,1] == 241) & (arr[:,:,2] == 241)
        arr[mask] = [255, 255, 255, 255]
        Image.fromarray(arr).save(path)
    except Exception:
        pass


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    render(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

