"""
解説用の図を作る共通の道具（figkit）。

図ごとのスクリプト（<試験ディレクトリ>/intermediates/figs/a5_fig_xxx.py）から使い、
`scripts/fig.py` で実行する。

    import figkit as fk

    fig, ax = fk.chart(h=7)          # C：データ図（グラフ）
    fig, ax = fk.canvas((0, 10), (0, 6))   # D：模式図（等倍の座標、軸なし）
    fig, ax = fk.on_image(fk.image(__file__, "q5_fig_1.png"))  # B：画像への書き込み
    fk.crop(fk.image(__file__, "page-2.png"), (x0, y0, x1, y1), __file__)  # A：切り出し
    fk.save(fig, __file__)           # → intermediates/images/<スクリプト名>.png

寸法の考え方：
  md2odt.py は、どの画像も本文幅 WIDTH_CM（13.8 cm）で ODT に載せる。
  図をこの幅で描けば、指定した pt がそのまま印刷時の文字の大きさになる。
"""

import logging
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from .env import jp_font  # noqa: E402

# ---- 寸法 -------------------------------------------------------------
WIDTH_CM = 13.8  # ODT に載せたときの幅（md2odt.py の IMG_WIDTH = 520px と同じ）
DPI = 200
CM = 1 / 2.54

# ---- 文字の大きさ（pt） -------------------------------------------------
FONT_PT = 10  # 注記・目盛り
LABEL_PT = 11  # 軸の名前・図の中の主な語
TITLE_PT = 12  # 図の見出し（なるべく使わず、本文で説明する）

# ---- 色 ---------------------------------------------------------------
# 1 つの図で使うのは 2〜3 色まで。同じものは同じ色で通す。
COLORS = {
    "ink": "#222222",  # 線・文字の基本
    "main": "#1e64c8",  # 主役（ODT の見出しと同じ青）
    "accent": "#e07a00",  # 比べる相手・増えた分
    "alert": "#d23c3c",  # 答え・強調したい差
    "sub": "#8a8a8a",  # 補助線・目盛り・参考
    "fill": "#dce8f8",  # main の塗り
    "fill2": "#fde8cc",  # accent の塗り
}
INK, MAIN, ACCENT, ALERT, SUB = (COLORS[k] for k in ("ink", "main", "accent", "alert", "sub"))

LINE_W = 1.4  # 図の線
THIN_W = 0.8  # 補助線・格子


def setup():
    """matplotlib の既定値を、このスキルの図の体裁にそろえる。"""
    plt.rcParams.update({
        "font.family": jp_font(),
        "mathtext.fontset": "cm",  # 式は md2odt.py の数式と同じ字体
        "axes.unicode_minus": True,  # マイナスは U+2212
        "font.size": FONT_PT,
        "axes.labelsize": LABEL_PT,
        "axes.titlesize": TITLE_PT,
        "xtick.labelsize": FONT_PT,
        "ytick.labelsize": FONT_PT,
        "legend.fontsize": FONT_PT,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "lines.linewidth": LINE_W,
        "axes.linewidth": THIN_W,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": "#dddddd",
        "grid.linewidth": THIN_W,
        "legend.frameon": False,
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.facecolor": "white",
    })


setup()


# ---- 図の用意 -----------------------------------------------------------
def chart(h: float = 8.0, w: float = WIDTH_CM, grid: bool = True):
    """データ図（グラフ）用。h・w は cm。上と右の枠線はなし。"""
    fig, ax = plt.subplots(figsize=(w * CM, h * CM), layout="constrained")
    if grid:
        ax.grid(True, axis="y")
        ax.set_axisbelow(True)
    return fig, ax


def canvas(xlim: tuple[float, float], ylim: tuple[float, float], w: float = WIDTH_CM):
    """模式図用。x・y を同じ縮尺にし、軸は消す。高さは縦横比から決まる。"""
    (x0, x1), (y0, y1) = xlim, ylim
    h = w * (y1 - y0) / (x1 - x0)
    fig = plt.figure(figsize=(w * CM, h * CM))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def on_image(src: str | Path, w: float = WIDTH_CM):
    """画像（切り出した問題の図など）の上に書き込む用。座標は画像の画素（左上が原点、y は下向き）。"""
    from PIL import Image

    img = Image.open(src)
    iw, ih = img.size
    fig = plt.figure(figsize=(w * CM, w * CM * ih / iw))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(img, extent=(0, iw, ih, 0), interpolation="lanczos")
    ax.set_xlim(0, iw)
    ax.set_ylim(ih, 0)
    ax.axis("off")
    return fig, ax


# ---- パス ---------------------------------------------------------------
def images_dir(script: str | Path) -> Path:
    """図のスクリプト（intermediates/figs/*.py）から見た intermediates/images/。"""
    return Path(script).resolve().parent.parent / "images"


def image(script: str | Path, name: str) -> Path:
    """intermediates/images/ にある画像のパス。"""
    p = images_dir(script) / name
    if not p.is_file():
        raise SystemExit(f"画像がありません: {p}")
    return p


def out_path(target: str | Path) -> Path:
    """保存先。.py を渡すと、intermediates/images/<スクリプト名>.png にする。"""
    target = Path(target)
    if target.suffix == ".py":
        return images_dir(target) / f"{target.stem}.png"
    return target


# ---- 保存 ---------------------------------------------------------------
class _Collect(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def save(fig, target: str | Path) -> Path:
    """PNG で保存する。字形のない文字やフォントの欠けがあれば、保存せずに止める。"""
    out = out_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    handler = _Collect()
    logger = logging.getLogger("matplotlib")
    logger.addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig.canvas.draw()
            problems = handler.messages + [str(w.message) for w in caught if "Glyph" in str(w.message)]
            if problems:
                raise SystemExit(f"図に描けない文字があります（{out.name}）:\n  " + "\n  ".join(sorted(set(problems))))
            fig.savefig(out, dpi=DPI, bbox_inches="tight", pad_inches=0.05)
    finally:
        logger.removeHandler(handler)
        plt.close(fig)
    print(f"保存しました: {out}")
    return out


def crop(src: str | Path, box: tuple[int, int, int, int], target: str | Path) -> Path:
    """画像の一部を切り出して保存する。box は (左, 上, 右, 下) の画素。"""
    from PIL import Image

    out = out_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).crop(box).save(out)
    print(f"保存しました: {out}")
    return out
