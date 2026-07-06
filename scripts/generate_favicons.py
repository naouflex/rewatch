#!/usr/bin/env python3
"""Generate Rewatch favicons (16x16, 32x32, 96x96) from a source image.

Usage:
    python scripts/generate_favicons.py [SOURCE] [OUTPUT_DIR]

Defaults:
    SOURCE     = client/app/assets/images/icon_small.png
    OUTPUT_DIR = client/app/assets/images/

Requires Pillow:
    pip install Pillow
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write(
        "Pillow is required. Install it with:\n  pip install Pillow\n"
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "client/app/assets/images/icon_small.png"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "client/app/assets/images"

FAVICON_SIZES = (16, 32, 96)
PWA_ICON_SIZES = {
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
}


def generate_favicons(source: Path, output_dir: Path) -> list[Path]:
    if not source.is_file():
        raise FileNotFoundError(f"Source image not found: {source}")

    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    with Image.open(source) as img:
        # Preserve transparency by working in RGBA mode.
        rgba = img.convert("RGBA")

        for size in FAVICON_SIZES:
            resized = rgba.resize((size, size), Image.Resampling.LANCZOS)
            target = output_dir / f"favicon-{size}x{size}.png"
            resized.save(target, format="PNG", optimize=True)
            written.append(target)
            print(f"Wrote {target} ({size}x{size})")

        for filename, size in PWA_ICON_SIZES.items():
            resized = rgba.resize((size, size), Image.Resampling.LANCZOS)
            target = output_dir / filename
            resized.save(target, format="PNG", optimize=True)
            written.append(target)
            print(f"Wrote {target} ({size}x{size})")

    return written


def main(argv: list[str]) -> int:
    source = Path(argv[1]).expanduser().resolve() if len(argv) > 1 else DEFAULT_SOURCE
    output_dir = (
        Path(argv[2]).expanduser().resolve() if len(argv) > 2 else DEFAULT_OUTPUT_DIR
    )

    generate_favicons(source, output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
