# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "matplotlib",
# ]
# ///

"""
図のスクリプトを実行する。figkit を読み込めるようにしてから、スクリプトを順に実行する。

使い方:
  uv run fig.py <試験ディレクトリ>/intermediates/figs/a5_fig_dewpoint.py   (1 つ)
  uv run fig.py <試験ディレクトリ>/intermediates/figs                       (フォルダ内のすべて)
  uv run fig.py --grid <試験ディレクトリ>/intermediates/images/page-2.png   (切り出し位置を測る方眼つき画像)
  uv run fig.py --env                                                       (使うフォント・soffice を表示)
"""

import argparse
import runpy
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from figkit.env import report, utf8_console  # noqa: E402


def run(scripts: list[Path]):
    import matplotlib.pyplot as plt

    import figkit  # noqa: F401  既定の体裁をここで設定する

    for s in scripts:
        print(f"実行: {s}")
        folder = str(s.resolve().parent)  # 同じフォルダの _parts.py などを import できるように
        sys.path.insert(0, folder)
        try:
            runpy.run_path(str(s), run_name="__main__")
        finally:
            sys.path.remove(folder)
            plt.close("all")


def grid(src: Path, step: int = 100) -> Path:
    """画素の座標を読み取るための方眼を重ねた画像を、一時フォルダに作る（成果物には入れない）。"""
    from PIL import Image, ImageDraw

    img = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(img)
    w, h = img.size
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(255, 0, 0) if x % (step * 5) == 0 else (255, 160, 160), width=1)
        d.text((x + 2, 2), str(x), fill=(200, 0, 0))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(255, 0, 0) if y % (step * 5) == 0 else (255, 160, 160), width=1)
        d.text((2, y + 2), str(y), fill=(200, 0, 0))
    out = Path(tempfile.gettempdir()) / f"{src.stem}_grid.png"
    img.save(out)
    return out


if __name__ == "__main__":
    utf8_console()
    ap = argparse.ArgumentParser(description="図のスクリプトを実行する")
    ap.add_argument("paths", nargs="*", type=Path, help="図のスクリプト、またはそれを入れたフォルダ")
    ap.add_argument("--grid", type=Path, help="方眼を重ねた画像を作る（切り出し位置を測る）")
    ap.add_argument("--step", type=int, default=100, help="方眼の間隔（画素）")
    ap.add_argument("--env", action="store_true", help="使うフォントと soffice を表示する")
    args = ap.parse_args()

    if args.env:
        report()
    if args.grid:
        print(f"方眼つき画像: {grid(args.grid, args.step)}")
    scripts = []
    for p in args.paths:
        if p.is_dir():
            # 問題の図（q*：切り出し）を先に作る。解説の図（a*）がそれを下地に使うため
            found = [q for q in p.glob("*.py") if not q.name.startswith("_")]
            scripts += sorted(found, key=lambda q: (not q.name.startswith("q"), q.name))
        elif p.is_file():
            scripts.append(p)
        else:
            ap.error(f"見つかりません: {p}")
    if not (scripts or args.grid or args.env):
        ap.error("図のスクリプトを指定してください")
    run(scripts)
