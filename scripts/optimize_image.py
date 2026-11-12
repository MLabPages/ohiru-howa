#!/usr/bin/env python3
"""挿絵を幅およそ1200pxのJPEGにして images/ に保存する。"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_WIDTH = 1200
QUALITY = 82


def optimize(src: Path, dest: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow が必要です。先に pip install -r requirements.txt を実行してください。", file=sys.stderr)
        raise SystemExit(1)

    resample = getattr(Image, "Resampling", Image).LANCZOS
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > MAX_WIDTH:
            height = round(im.height * MAX_WIDTH / im.width)
            im = im.resize((MAX_WIDTH, height), resample)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        return im.width, im.height


def main() -> None:
    if len(sys.argv) != 3:
        print("使い方: python3 scripts/optimize_image.py 元画像.jpg images/05-name.jpg", file=sys.stderr)
        raise SystemExit(1)
    src = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    if not src.is_file():
        print(f"元画像が見つかりません: {src}", file=sys.stderr)
        raise SystemExit(1)
    width, height = optimize(src, dest)
    size = dest.stat().st_size
    print(f"保存しました: {dest} （{width}×{height}px、{size}バイト）")


if __name__ == "__main__":
    main()
