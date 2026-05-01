"""Generate placeholder brand PNGs for any logo that is missing from assets/.

Real logos come from `assets/fetch.sh`.  When that script can't reach a brand's
CDN (offline build, corporate proxy, transient DNS), we still want every node
to render with something visible — not a 1px transparent fallback.

This script writes a 256x256 PNG with the brand's initials on a coloured
background to any path that doesn't already exist.  It never overwrites a real
logo, so re-running fetch.sh later upgrades placeholders to the real thing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent / "assets"

# (filename, label, hex bg colour) — colours are taken from each brand's
# official palette where known, otherwise a neutral grey-blue.
PLACEHOLDERS: list[tuple[str, str, str]] = [
    ("mlflow.png", "ML", "#0194E2"),
    ("opentelemetry.png", "OTel", "#425CC7"),
    ("victoriametrics.png", "VM", "#621773"),
    ("redpanda.png", "Rp", "#E10D2B"),
    ("duckdb.png", "Duck", "#FFF000"),
    ("binance.png", "BNB", "#F0B90B"),
    ("coinbase.png", "CB", "#0052FF"),
    ("open_meteo.png", "OM", "#00897B"),
    ("minio.png", "MinIO", "#C72E29"),
]

SIZE = 256


def _font(size: int) -> ImageFont.ImageFont:
    """Pick a bold sans font that exists on macOS or fall back to default."""
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_colour(bg_hex: str) -> str:
    """Black text on light backgrounds, white on dark."""
    r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return "#111111" if luma > 160 else "#ffffff"


def make_placeholder(path: Path, label: str, bg: str) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=40, fill=bg)
    fg = _text_colour(bg)
    font = _font(72 if len(label) <= 3 else 56)
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((SIZE - tw) / 2 - bbox[0], (SIZE - th) / 2 - bbox[1]),
        label,
        fill=fg,
        font=font,
    )
    img.save(path, "PNG")


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for filename, label, bg in PLACEHOLDERS:
        path = ASSETS_DIR / filename
        if path.exists():
            continue
        make_placeholder(path, label, bg)
        created += 1
    print(
        f"placeholders: created {created}, kept {len(PLACEHOLDERS) - created} existing"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
