from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    src_assets = _ROOT / "src" / "stream_cheremsha" / "assets"
    src_ico = src_assets / "icon.ico"
    src_png = src_assets / "icon.png"

    out_dir = _ROOT / "dist" / "nuitka"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_ico = out_dir / "icon.ico"

    if src_ico.is_file():
        shutil.copyfile(src_ico, out_ico)
        return

    if not src_png.is_file():
        raise SystemExit(f"Missing icon source: {src_png}")

    img = Image.open(src_png)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(out_ico, format="ICO", sizes=sizes)


if __name__ == "__main__":
    main()
