"""Inline every PNG referenced by an SVG as a base64 data URI.

Graphviz emits absolute filesystem paths for `<image xlink:href="...">` nodes.
That works on the machine that rendered the SVG and nowhere else — VS Code's
preview, browsers loading from `file://`, and GitHub all refuse to fetch a
local path from inside an SVG, so the diagram displays with no icons.

This script walks each SVG, reads every PNG it references, base64-encodes the
bytes, and rewrites the href to a `data:image/png;base64,...` URI.  After it
runs, the SVG is fully self-contained and renders the same everywhere.

Idempotent: an SVG that's already been processed has no `xlink:href` pointing
at a file path, so a second run is a no-op.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

DIAGRAMS_DIR = Path(__file__).parent

# Match either xlink:href="..." or href="..." pointing to a PNG file path.
_HREF_RE = re.compile(r'(xlink:href|href)="([^"]+\.png)"')


def _embed(match: re.Match[str]) -> str:
    attr, path_str = match.group(1), match.group(2)
    if path_str.startswith("data:"):
        return match.group(0)
    path = Path(path_str)
    if not path.is_absolute():
        path = DIAGRAMS_DIR / path
    if not path.exists():
        return match.group(0)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'{attr}="data:image/png;base64,{encoded}"'


def embed_svg(svg_path: Path) -> int:
    """Rewrite SVG in place. Returns the number of images embedded."""
    text = svg_path.read_text(encoding="utf-8")
    embedded = 0

    def _wrap(match: re.Match[str]) -> str:
        nonlocal embedded
        replacement = _embed(match)
        if replacement != match.group(0):
            embedded += 1
        return replacement

    new_text = _HREF_RE.sub(_wrap, text)
    if embedded:
        svg_path.write_text(new_text, encoding="utf-8")
    return embedded


def main() -> int:
    svgs = sorted(DIAGRAMS_DIR.glob("*.svg"))
    if not svgs:
        print("no SVGs found", file=sys.stderr)
        return 1
    total = 0
    for svg in svgs:
        n = embed_svg(svg)
        print(f"  embedded {n:3d} images into {svg.name}")
        total += n
    print(f"total: {total} images embedded across {len(svgs)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
