# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pypdfium2",
#     "pillow",
# ]
# ///

"""
PDF をページごとの PNG にする（pdftoppm・pdfinfo の代わり。Linux・macOS・Windows で動く）。

使い方:
  uv run pdf2png.py <原本>.pdf -o <試験ディレクトリ>/intermediates/images        (200dpi、page-1.png, page-2.png …)
  uv run pdf2png.py solutions.pdf -o <出力先> --dpi 70 --sheet                    (確認用。全ページを 1 枚に並べた画像も作る)
  uv run pdf2png.py solutions.pdf --info                                          (ページ数だけ表示)
"""

import argparse
import sys
from pathlib import Path

import pypdfium2 as pdfium


def utf8_console():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


def convert(pdf: Path, outdir: Path, dpi: int, prefix: str, pages: list[int] | None) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(pdf)
    outs = []
    for n in pages or range(1, len(doc) + 1):
        img = doc[n - 1].render(scale=dpi / 72).to_pil()
        out = outdir / f"{prefix}-{n}.png"
        img.save(out)
        outs.append(out)
        print(f"保存しました: {out}（{img.width}×{img.height}）")
    return outs


def sheet(images: list[Path], out: Path, cols: int = 4) -> Path:
    """ページ画像を格子状に並べた 1 枚を作る（全体の崩れを一度に見るため）。"""
    from PIL import Image

    ims = [Image.open(p) for p in images]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    cols = min(cols, len(ims))
    rows = -(-len(ims) // cols)
    gap = 10
    canvas = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), (160, 160, 160))
    for k, im in enumerate(ims):
        r, c = divmod(k, cols)
        canvas.paste(im, (gap + c * (w + gap), gap + r * (h + gap)))
    canvas.save(out)
    print(f"一覧画像: {out}")
    return out


if __name__ == "__main__":
    utf8_console()
    ap = argparse.ArgumentParser(description="PDF をページごとの PNG にする")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("-o", "--outdir", type=Path, help="出力先（なければ作る）")
    ap.add_argument("--dpi", type=int, default=200, help="解像度（既定 200。読むだけなら 120、ODT の確認は 70 以上）")
    ap.add_argument("--prefix", default="page", help="ファイル名の頭（既定 page → page-1.png）")
    ap.add_argument("--pages", type=int, nargs="+", help="書き出すページ（1 始まり）。省くとすべて")
    ap.add_argument("--sheet", action="store_true", help="全ページを並べた <prefix>-sheet.png も作る")
    ap.add_argument("--info", action="store_true", help="ページ数を表示するだけ")
    args = ap.parse_args()

    if args.info:
        print(f"ページ数: {len(pdfium.PdfDocument(args.pdf))}")
        sys.exit()
    if not args.outdir:
        ap.error("-o で出力先を指定してください")
    outs = convert(args.pdf, args.outdir, args.dpi, args.prefix, args.pages)
    if args.sheet:
        sheet(outs, args.outdir / f"{args.prefix}-sheet.png")
