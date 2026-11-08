# encoding: utf-8
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "markdown",
#     "markdown-it-py",
#     "matplotlib",
#     "python-docx",
#     "pywin32; sys_platform == 'win32'",
# ]
# ///

"""
markdown を DOCX（Word）に変換する。LibreOffice は要らない（python-docx で直接作る）。
使い方: uv run md2docx.py a5.md                            (a5.docx を出力)
        uv run md2docx.py a5.md a6.md a7.md -o solutions.docx (1 つの DOCX にまとめる。2 つ目からページを改める)
        uv run md2docx.py a5.md -o solutions.docx --pdf intermediates/solutions.pdf  (確認用の PDF も作る)

確認用の PDF は、LibreOffice があればそれで、なければ（Windows で）Word で作る。

数式: 行頭の `$$ ... $$` は、md2odt.py と同じ方法で画像（PNG）にして埋め込む。
対応する記法: 見出し（#〜####）、段落、太字・斜体・コード、箇条書き（入れ子あり）・番号付きリスト、
             引用、表、コードブロック、画像、水平線。
"""

import argparse
import io
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from markdown_it import MarkdownIt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figkit.env import jp_font, mono_font, utf8_console  # noqa: E402
from md2odt import EQ_DPI, extract_formulas, render_formula  # noqa: E402

ACCENT = RGBColor(0x1E, 0x64, 0xC8)
ACCENT_HEX = "1E64C8"
H2_BG = "E1EBFA"
TH_BG = "E1EBFA"
QUOTE_BG = "F5F8FD"
CODE_BG = "F3F3F3"
IMG_WIDTH = Cm(13.8)  # md2odt.py の 520px 相当
IMG_MAX_HEIGHT = Cm(9.5)  # 縦長の図が 1 ページを占めないように
TEXT_WIDTH = Cm(21.0 - 1.8 * 2)
# 行送りは固定値にする。倍数で指定すると、字の上下の余白が大きいフォント（Noto Sans JP など）で広がりすぎる
LINE_PT = 16
EQ_PLACEHOLDER = re.compile(r"^EQBLOCK(\d+)EQ$")

HEADING_SIZES = {1: 20, 2: 15, 3: 12.5, 4: 11.5}


# ---- 書式の部品 ---------------------------------------------------------------

def set_font(target, name: str):
    """run またはスタイルのフォントを、欧文・和文とも name にする（テーマのフォント指定は外す）。"""
    target.font.name = name
    rpr = target.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attr}"), name)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rfonts.attrib.pop(qn(f"w:{attr}"), None)


def shade(el_pr, fill: str):
    """段落（pPr）またはセル（tcPr）に背景色を付ける。"""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    el_pr.append(shd)


def para_border(paragraph, side: str, color: str, size: int = 12, space: int = 4):
    """段落に罫線を付ける（side は top / left / bottom / right）。"""
    ppr = paragraph._p.get_or_add_pPr()
    bdr = ppr.find(qn("w:pBdr"))
    if bdr is None:
        bdr = OxmlElement("w:pBdr")
        ppr.append(bdr)
    b = OxmlElement(f"w:{side}")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(size))
    b.set(qn("w:space"), str(space))
    b.set(qn("w:color"), color)
    bdr.append(b)


def setup_styles(doc: Document):
    font = jp_font()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.5)

    normal = doc.styles["Normal"]
    set_font(normal, font)
    normal.font.size = Pt(11)
    pf = normal.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(3), Pt(LINE_PT)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY

    for level, size in HEADING_SIZES.items():
        st = doc.styles[f"Heading {level}"]
        set_font(st, font)
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = ACCENT if level in (1, 3) else RGBColor(0, 0, 0)
        hf = st.paragraph_format
        hf.space_before = Pt({1: 0, 2: 10, 3: 8, 4: 6}[level])
        hf.space_after = Pt({1: 6, 2: 4, 3: 2, 4: 2}[level])
        hf.keep_with_next = True
        hf.line_spacing = Pt(round(size * 1.4))
        hf.line_spacing_rule = WD_LINE_SPACING.EXACTLY

    for name in ("List Bullet", "List Bullet 2", "List Bullet 3", "List Number", "List Number 2", "List Number 3"):
        doc.styles[name].paragraph_format.space_after = Pt(2)


# ---- inline ---------------------------------------------------------------

def add_inline(paragraph, children, base: Path, bold=False):
    """インラインのトークン列を、段落に run として足す。"""
    b, i = bold, False
    for t in children or []:
        if t.type == "strong_open":
            b = True
        elif t.type == "strong_close":
            b = bold
        elif t.type == "em_open":
            i = True
        elif t.type == "em_close":
            i = False
        elif t.type in ("text", "html_inline"):
            if t.content:
                r = paragraph.add_run(t.content)
                r.bold, r.italic = b, i
        elif t.type == "code_inline":
            r = paragraph.add_run(t.content)
            set_font(r, mono_font())
            r.bold = b
        elif t.type == "softbreak":
            paragraph.add_run(" ")
        elif t.type == "hardbreak":
            paragraph.add_run().add_break(WD_BREAK.LINE)
        elif t.type == "image":
            add_picture(paragraph, base / t.attrGet("src"))
        # link_open / link_close は文字だけ残す


def picture_para(paragraph):
    """画像の段落。行送りが固定値のままだと画像が切れるので、1 行に戻す。"""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    paragraph.paragraph_format.keep_together = True


def add_picture(paragraph, path: Path):
    data = path.read_bytes()
    w, h = struct.unpack(">II", data[16:24])  # PNG の IHDR から画素数を読む
    width = min(IMG_WIDTH, int(IMG_MAX_HEIGHT * w / h))
    picture_para(paragraph)
    paragraph.add_run().add_picture(io.BytesIO(data), width=width)


def add_formula(doc, rows):
    for row in rows:
        png = render_formula(row)
        w, _ = struct.unpack(">II", png[16:24])
        width = min(Cm(w / EQ_DPI * 2.54), TEXT_WIDTH)  # EQ_FONT_PT がそのまま pt の大きさになる
        p = doc.add_paragraph()
        picture_para(p)
        p.add_run().add_picture(io.BytesIO(png), width=width)


# ---- block ----------------------------------------------------------------

class Builder:
    def __init__(self, doc: Document, base: Path, formulas, page_break: bool):
        self.doc = doc
        self.base = base
        self.formulas = formulas
        self.page_break = page_break  # 最初の h1 の前でページを改める
        self.lists = []  # 入れ子のリスト（"bullet" / "ordered"）
        self.quote = 0
        self.first_in_item = False

    def new_para(self, style=None):
        p = self.doc.add_paragraph(style=style)
        if self.quote:
            p.paragraph_format.left_indent = Cm(0.4)
            para_border(p, "left", ACCENT_HEX, size=24, space=8)
            shade(p._p.get_or_add_pPr(), QUOTE_BG)
        return p

    def list_para(self):
        kind = self.lists[-1]
        level = min(len(self.lists), 3)
        base = "List Bullet" if kind == "bullet" else "List Number"
        if self.first_in_item:
            self.first_in_item = False
            return self.new_para(base if level == 1 else f"{base} {level}")
        # 同じ項目の 2 段落目は、記号なしで字下げだけ合わせる
        p = self.new_para()
        p.paragraph_format.left_indent = Cm(0.63 * level)
        return p

    def run(self, tokens):
        i = 0
        while i < len(tokens):
            t = tokens[i]
            ty = t.type
            if ty == "heading_open":
                level = int(t.tag[1])
                p = self.doc.add_paragraph(style=f"Heading {min(level, 4)}")
                add_inline(p, tokens[i + 1].children, self.base)
                if level == 1:
                    para_border(p, "bottom", ACCENT_HEX, size=12, space=2)
                    if self.page_break:
                        p.paragraph_format.page_break_before = True
                        self.page_break = False
                elif level == 2:
                    shade(p._p.get_or_add_pPr(), H2_BG)
                i += 3
            elif ty == "paragraph_open":
                inline = tokens[i + 1]
                m = EQ_PLACEHOLDER.match(inline.content.strip())
                if m:
                    add_formula(self.doc, self.formulas[int(m.group(1))])
                else:
                    p = self.list_para() if self.lists else self.new_para()
                    add_inline(p, inline.children, self.base)
                i += 3
            elif ty in ("bullet_list_open", "ordered_list_open"):
                self.lists.append("bullet" if ty == "bullet_list_open" else "ordered")
                i += 1
            elif ty in ("bullet_list_close", "ordered_list_close"):
                self.lists.pop()
                i += 1
            elif ty == "list_item_open":
                self.first_in_item = True
                i += 1
            elif ty == "list_item_close":
                self.first_in_item = False
                i += 1
            elif ty == "blockquote_open":
                self.quote += 1
                i += 1
            elif ty == "blockquote_close":
                self.quote -= 1
                i += 1
            elif ty in ("fence", "code_block"):
                self.code(t.content)
                i += 1
            elif ty == "hr":
                p = self.doc.add_paragraph()
                para_border(p, "bottom", "AAAAAA", size=6, space=1)
                i += 1
            elif ty == "table_open":
                j = next(k for k in range(i, len(tokens)) if tokens[k].type == "table_close")
                self.table(tokens[i:j + 1])
                i = j + 1
            else:
                i += 1

    def code(self, text: str):
        p = self.new_para()
        shade(p._p.get_or_add_pPr(), CODE_BG)
        p.paragraph_format.left_indent = Cm(0.3)
        p.paragraph_format.line_spacing = Pt(LINE_PT - 2)
        p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(3)
        for n, line in enumerate(text.rstrip("\n").split("\n")):
            if n:
                p.add_run().add_break(WD_BREAK.LINE)
            set_font(p.add_run(line), mono_font())

    @staticmethod
    def col_widths(rows, ncols):
        """列幅を、各列の文字数に合わせて本文幅に割り振る（短い列は詰め、長い列を広げる）。"""
        def length(children):
            return sum(len(t.content) for t in children or [] if t.type in ("text", "code_inline"))

        longest = [max((length(r[c][1]) for r in rows if c < len(r)), default=1) for c in range(ncols)]
        header = [length(rows[0][c][1]) if c < len(rows[0]) else 0 for c in range(ncols)]
        # 文字数がそのまま幅にならないよう、上限を付ける。
        # 短い列は、太字の見出しが折り返さない幅を確保する（全角 1 字 ≒ 2、セルの余白 ≒ 3）
        weights = [min(max(n, 2 * h + 3, 4), 40) for n, h in zip(longest, header)]
        total = sum(weights)
        return [int(TEXT_WIDTH * w / total) for w in weights]

    def table(self, tokens):
        rows, cur, aligns = [], None, []
        for k, t in enumerate(tokens):
            if t.type == "tr_open":
                cur = []
            elif t.type == "tr_close":
                rows.append(cur)
            elif t.type in ("th_open", "td_open"):
                cur.append((t.type == "th_open", tokens[k + 1].children))
                if not rows:
                    style = t.attrGet("style") or ""
                    aligns.append("center" if "center" in style else "right" if "right" in style else None)
        ncols = max(len(r) for r in rows)
        tbl = self.doc.add_table(rows=len(rows), cols=ncols)
        tbl.style = self.doc.styles["Table Grid"]
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        for c, w in enumerate(self.col_widths(rows, ncols)):
            tbl.columns[c].width = w  # 表の格子（gridCol）と、各セル（tcW）の両方に入れる
            for cell in tbl.columns[c].cells:
                cell.width = w
        for r, row in enumerate(rows):
            trpr = tbl.rows[r]._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))  # 行の途中でページを分けない
            if r == 0:
                trpr.append(OxmlElement("w:tblHeader"))  # ページをまたいだら見出し行を繰り返す
            for c, (is_th, children) in enumerate(row):
                cell = tbl.cell(r, c)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                if is_th:
                    shade(cell._tc.get_or_add_tcPr(), TH_BG)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif c < len(aligns) and aligns[c]:
                    p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT}[aligns[c]]
                add_inline(p, children, self.base, bold=is_th)
        # 表の直後に少し余白を入れる
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)


# ---- 変換 -----------------------------------------------------------------

def convert(srcs: list[Path], out: Path):
    doc = Document()
    setup_styles(doc)
    md = MarkdownIt("commonmark").enable("table")
    for n, src in enumerate(srcs):
        text, formulas = extract_formulas(src.read_text(encoding="utf-8"))
        Builder(doc, src.parent, formulas, page_break=n > 0).run(md.parse(text))
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print(f"保存しました: {out}（フォント: {jp_font()}）")


def to_pdf(docx: Path, pdf: Path):
    """確認用に DOCX を PDF にする。LibreOffice があればそれを、なければ Word（Windows）を使う。"""
    from figkit.env import soffice
    from md2odt import run_soffice

    pdf.parent.mkdir(parents=True, exist_ok=True)
    try:
        soffice()
    except SystemExit:
        if sys.platform != "win32":
            raise
        word_to_pdf(docx, pdf)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            run_soffice("--convert-to", "pdf", "--outdir", tmp, str(docx))
            shutil.move(str(Path(tmp) / f"{docx.stem}.pdf"), str(pdf))
    print(f"保存しました: {pdf}")


def word_to_pdf(docx: Path, pdf: Path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        d = word.Documents.Open(str(docx), ReadOnly=True, AddToRecentFiles=False)
        try:
            d.SaveAs2(str(pdf), FileFormat=17)  # wdFormatPDF
        finally:
            d.Close(False)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"Word で PDF にできませんでした: {e}")
    finally:
        word.Quit()


if __name__ == "__main__":
    utf8_console()
    ap = argparse.ArgumentParser(description="markdown を DOCX に変換する")
    ap.add_argument("md", nargs="+", type=Path, help="変換する md（複数なら 1 つの DOCX にまとめる）")
    ap.add_argument("-o", "--output", type=Path, help="出力する DOCX（md が複数のときは必須）")
    ap.add_argument("--pdf", type=Path, help="確認用の PDF も作る（出力先のパス）")
    args = ap.parse_args()
    if len(args.md) > 1 and not args.output:
        ap.error("md が複数のときは -o で出力先を指定する")
    srcs = [p.resolve() for p in args.md]
    out = (args.output or srcs[0].with_suffix(".docx")).resolve()
    convert(srcs, out)
    if args.pdf:
        to_pdf(out, args.pdf.resolve())
