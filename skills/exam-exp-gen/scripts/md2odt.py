# encoding: utf-8
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "markdown",
#     "matplotlib",
# ]
# ///

"""
markdown を ODT に変換する。
使い方: uv run md2odt.py a5.md                           (a5.odt を出力)
        uv run md2odt.py a5.md a6.md a7.md -o solutions.odt  (1 つの ODT にまとめる。2 つ目からページを改める)
        uv run md2odt.py a5.md -o solutions.odt --pdf intermediates/solutions.pdf  (確認用の PDF も作る)

フォントと LibreOffice（soffice）は、OS に合わせて figkit/env.py が探す（環境変数で上書きできる）。

数式: 行頭の `$$ ... $$` は、変換時に画像（PNG）にして埋め込む。画像ファイルは作らない。
  - 日本語の部分は本文と同じフォント、それ以外は LaTeX 風の記法（matplotlib の mathtext）で描く。
  - `\\\\`（バックスラッシュ 2 つ）で区切ると、複数行の式になる。
  - 描けない記法や、字形のない文字があれば、エラーで止める。
  - matplotlib は、フォントの探索にも使う。
"""

import argparse
import base64
import io
import logging
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from html import escape
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figkit.env import jp_font, mono_font, soffice, utf8_console  # noqa: E402

CSS = """
@page { size: A4; margin: 1.8cm; }
body { font-family: '__FONT__'; font-size: 11pt; line-height: 1.25; }
h1, h2, h3, h4, th, td { font-family: '__FONT__'; }
p, li, td, th, blockquote { line-height: 1.25; margin-top: 0; margin-bottom: 3pt; }
h1 { font-size: 20pt; border-bottom: 2px solid #1e64c8; color: #1e64c8; }
h2 { font-size: 15pt; background: #e1ebfa; padding: 2pt 6pt; margin-top: 10pt; margin-bottom: 4pt; }
h3 { font-size: 12.5pt; margin-top: 8pt; margin-bottom: 2pt; color: #1e64c8; }
h4 { font-size: 11.5pt; margin-top: 6pt; margin-bottom: 2pt; }
table { border-collapse: collapse; }
th, td { border: 1px solid #888; padding: 3pt 6pt; }
th { background: #e1ebfa; }
pre { line-height: 1.2; margin: 2pt 0; font-family: '__MONO__'; background: #f3f3f3; padding: 6pt; }
blockquote { border-left: 4px solid #1e64c8; background: #f5f8fd; margin-left: 0; padding: 2pt 10pt; }
img { max-width: 100%; }
"""


IMG_WIDTH = 520  # px。A4 の本文幅に収まる大きさ


def embed_images(html: str, base: Path) -> str:
    def repl(m):
        data = base.joinpath(m.group(1)).read_bytes()
        w, h = struct.unpack(">II", data[16:24])  # PNG の IHDR から画素数を読む
        return (f'src="data:image/png;base64,{base64.b64encode(data).decode()}" '
                f'width="{IMG_WIDTH}" height="{round(IMG_WIDTH * h / w)}"')

    return re.sub(r'src="([^"]+\.png)"', repl, html)


EQ_DPI = 200
EQ_FONT_PT = 12  # 本文（11pt）より少し大きく
CJK_RUN = re.compile(r"([℃　-ヿ㐀-鿿＀-￯]+)")  # ℃・かな・漢字・全角
EQ_BLOCK = re.compile(r"^[ \t]*\$\$(.+?)\$\$[ \t]*$", re.S | re.M)


def render_formula(row: str) -> bytes:
    """式 1 行を PNG にする。mathtext は日本語の字形を持たないので、日本語の部分は別に描いて基準線をそろえる。"""
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    problems = []

    class Catch(logging.Handler):  # 字形がないときの警告を、見逃さないために集める
        def emit(self, record):
            problems.append(record.getMessage())

    logger = logging.getLogger("matplotlib")
    handler = Catch(level=logging.WARNING)
    logger.addHandler(handler)
    try:
        with matplotlib.rc_context({"font.family": jp_font(), "mathtext.fontset": "cm"}):
            fig = Figure(figsize=(20, 2), dpi=EQ_DPI)
            FigureCanvasAgg(fig)
            renderer = fig.canvas.get_renderer()
            w, h = fig.bbox.width, fig.bbox.height
            gap = EQ_FONT_PT * EQ_DPI / 72 * 0.25
            x = 0.0
            for part in CJK_RUN.split(row):
                s = part if CJK_RUN.fullmatch(part) else part.strip()
                if not s:
                    continue
                if not CJK_RUN.fullmatch(part):
                    s = f"${s}$"
                t = fig.text(x / w, 0.5, s, fontsize=EQ_FONT_PT, va="baseline", ha="left")
                x += t.get_window_extent(renderer).width + gap
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=EQ_DPI, bbox_inches="tight", pad_inches=0.04)
    except ValueError as e:  # mathtext の構文エラー
        detail = [ln for ln in str(e).splitlines() if ln.strip()]
        raise SystemExit(f"数式を描けません: {row}\n  " + "\n  ".join(detail[-3:]))
    finally:
        logger.removeHandler(handler)
    if problems:
        raise SystemExit(f"数式に字形のない文字があります: {row}\n  " + "\n  ".join(sorted(set(problems))))
    return buf.getvalue()


def formula_img(png: bytes, alt: str) -> str:
    w, h = struct.unpack(">II", png[16:24])
    scale = 96 / EQ_DPI  # 画素数 → HTML の px。EQ_FONT_PT がそのまま pt の大きさになる
    if w * scale > IMG_WIDTH:
        scale = IMG_WIDTH / w
    return (f'<img src="data:image/png;base64,{base64.b64encode(png).decode()}" '
            f'width="{round(w * scale)}" height="{round(h * scale)}" alt="{escape(alt)}">')


def extract_formulas(text: str):
    """`$$ ... $$` を、markdown に壊されない目印に置き換える。式は行ごとに分けて返す。"""
    blocks = []

    def repl(m):
        rows = [" ".join(r.split()) for r in m.group(1).split("\\\\")]
        blocks.append([r for r in rows if r])
        return f"\n\nEQBLOCK{len(blocks) - 1}EQ\n\n"

    return EQ_BLOCK.sub(repl, text), blocks


def embed_formulas(html: str, blocks) -> str:
    for i, rows in enumerate(blocks):
        paras = "".join(f'<p align="center">{formula_img(render_formula(r), r)}</p>' for r in rows)
        html = html.replace(f"<p>EQBLOCK{i}EQ</p>", paras)
    if "EQBLOCK" in html:
        raise SystemExit("数式の目印が残っています（`$$` を行頭に置いているか確認）")
    return html


# LibreOffice の HTML 取り込みは CSS の行送り・余白をほぼ無視するので、変換後に ODT 内のスタイルを直接書き換える
STYLE_PATCHES = [
    ('fo:line-height="160%"', 'fo:line-height="118%"'),
    ('fo:line-height="115%"', 'fo:line-height="118%"'),
    ('fo:margin-bottom="0.499cm"', 'fo:margin-bottom="0.15cm"'),
    ('fo:margin-bottom="0.247cm"', 'fo:margin-bottom="0.12cm"'),
    ('fo:margin-top="0.635cm"', 'fo:margin-top="0.35cm"'),
    ('fo:margin-top="0.423cm"', 'fo:margin-top="0.25cm"'),
    ('fo:margin-bottom="0.212cm"', 'fo:margin-bottom="0.1cm"'),
    ('fo:margin-top="0.212cm"', 'fo:margin-top="0.15cm"'),
    ('fo:margin-top="0.247cm"', 'fo:margin-top="0.15cm"'),
    ('fo:margin-top="2cm"', 'fo:margin-top="1.5cm"'),
    ('fo:margin-bottom="2cm"', 'fo:margin-bottom="1.5cm"'),
    # 表をページの途中で分けない（1 行目の途中で切れて、次のページに空行が出るのを防ぐ）
    ('<style:table-properties ', '<style:table-properties style:may-break-between-rows="false" '),
]


def tighten_spacing(odt: Path):
    with zipfile.ZipFile(odt) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(odt, "w") as z:
        for info, data in items:  # mimetype を先頭・無圧縮のまま書き戻す
            if info.filename in ("styles.xml", "content.xml"):
                text = data.decode("utf-8")
                for old, new in STYLE_PATCHES:
                    text = text.replace(old, new)
                data = text.encode("utf-8")
            z.writestr(info, data, compress_type=info.compress_type)


def md_to_body(src: Path) -> str:
    text, blocks = extract_formulas(src.read_text(encoding="utf-8"))
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    body = body.replace("<table>", '<table border="1" cellspacing="0" cellpadding="3">')
    return embed_formulas(embed_images(body, src.parent), blocks)


def run_soffice(*args: str):
    # 起動中の LibreOffice と設定を取り合わないよう、使い捨てのプロファイルで動かす
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run(
            [soffice(), f"-env:UserInstallation={Path(prof).as_uri()}", "--headless", *args],
            check=True,
        )


def to_pdf(odt: Path, pdf: Path):
    """確認用に ODT を PDF にする。"""
    with tempfile.TemporaryDirectory() as tmp:
        run_soffice("--convert-to", "pdf", "--outdir", tmp, str(odt))
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(Path(tmp) / f"{odt.stem}.pdf"), str(pdf))
    print(f"保存しました: {pdf}")


def main(srcs: list[Path], out: Path, pdf: Path | None = None):
    # 複数の md は、2 つ目からページを改めて 1 つの ODT にまとめる（画像は md ごとの場所から読む）
    bodies = [md_to_body(s) for s in srcs]
    bodies[1:] = [b.replace("<h1>", '<h1 style="page-break-before: always">', 1) for b in bodies[1:]]
    css = CSS.replace("__FONT__", jp_font()).replace("__MONO__", mono_font())
    html = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(bodies)}</body></html>'
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / f"{out.stem}.html"
        h.write_text(html, encoding="utf-8")
        run_soffice("--infilter=HTML (StarWriter)", "--convert-to", "odt:writer8", "--outdir", str(out.parent), str(h))
    tighten_spacing(out)
    print(f"保存しました: {out}（フォント: {jp_font()}）")
    if pdf:
        to_pdf(out, pdf)


if __name__ == "__main__":
    utf8_console()
    ap = argparse.ArgumentParser(description="markdown を ODT に変換する")
    ap.add_argument("md", nargs="+", type=Path, help="変換する md（複数なら 1 つの ODT にまとめる）")
    ap.add_argument("-o", "--output", type=Path, help="出力する ODT（md が複数のときは必須）")
    ap.add_argument("--pdf", type=Path, help="確認用の PDF も作る（出力先のパス）")
    args = ap.parse_args()
    if len(args.md) > 1 and not args.output:
        ap.error("md が複数のときは -o で出力先を指定する")
    srcs = [p.resolve() for p in args.md]
    main(srcs, (args.output or srcs[0].with_suffix(".odt")).resolve(), args.pdf.resolve() if args.pdf else None)
