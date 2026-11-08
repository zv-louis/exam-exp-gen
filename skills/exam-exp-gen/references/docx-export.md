---
title: DOCX への変換
description: markdown の解説を DOCX（Word）にする手順と注意点。LibreOffice がない環境（Windows など）や、Word で配布したいときに、手順 5 で読む。
---

# DOCX への変換

markdown の解説を、配布用の DOCX にする。
LibreOffice を使わず、python-docx で直接作るので、LibreOffice が入っていない Windows でも使える。
`a5.md` を `solutions.docx` にしたときの試行錯誤をまとめてある。

## 仕組み

```
markdown ─(markdown-it-py)→ トークン ─(python-docx)→ DOCX
```

- 変換スクリプトは、このスキルの `scripts/md2docx.py`。依存は PEP 723 で書いてあり、`uv run` で動く。
- 数式（行頭の `$$ ... $$`）は、`md2odt.py` の関数をそのまま使って画像にする。書き方は [formulas.md](formulas.md)。
- フォントは `scripts/figkit/env.py` が選ぶ（ODT と同じ）。
- 実行は、プロジェクトのルートで行う。使い方は `md2odt.py` と同じ。

  ```bash
  uv run <スキルのディレクトリ>/scripts/md2docx.py <試験ディレクトリ>/intermediates/a5.md <試験ディレクトリ>/intermediates/a6.md -o <試験ディレクトリ>/solutions.docx
  ```

  - 複数の md は 1 つの DOCX にまとめ、2 つ目からは先頭の `# 見出し` でページを改める。
  - 出力は試験ディレクトリ直下に、名前は `solutions.docx` にする。

## 見た目の確認

```bash
uv run <スキルのディレクトリ>/scripts/md2docx.py <a*.md …> -o <試験ディレクトリ>/solutions.docx --pdf <試験ディレクトリ>/intermediates/solutions.pdf
uv run <スキルのディレクトリ>/scripts/pdf2png.py <試験ディレクトリ>/intermediates/solutions.pdf -o <試験ディレクトリ>/intermediates/check --dpi 100 --sheet
```

- `--pdf` は、LibreOffice があればそれで、なければ（Windows で）Word で PDF にする。Word は pywin32 経由で、画面に出さずに動かす。
- Word もないときは PDF を作れない。DOCX だけ作り、ユーザーに開いて確認してもらう。

## 対応する記法

見出し（`#`〜`####`）、段落、太字・斜体・インラインコード、箇条書き（3 段まで入れ子）・番号付きリスト、引用、表、コードブロック、画像、水平線、数式（`$$`）。
リンクは文字だけ残す。

## 起きた問題と対処

| 問題 | 原因 | 対処 |
|---|---|---|
| 7 ページになった（ODT は 4 ページ） | 行送りを倍数（1.18）で指定すると、字の上下の余白が大きいフォント（Noto Sans JP）で行が広がる | 行送りを固定値（`LINE_PT` = 16pt）にした。4 ページになった |
| 行送りを固定値にすると、画像が切れる | 固定値の行の高さに画像が収まらない | 画像と数式の段落だけ、行送りを 1 行（single）に戻す |
| 表が縦に長くなった | python-docx の表は列幅が均等 | 列幅を、各列の文字数に合わせて本文幅に割り振る（`col_widths`） |
| 列幅を指定しても、狭い列の見出しが折り返した | 見出しの字数を考えていなかった | 見出しの字数から最低幅を決める。幅はセル（`tcW`）と表の格子（`gridCol`）の両方に入れる |
| 縦長の図が 1 ページを占めた | 図の幅だけを決めていた | 高さを `IMG_MAX_HEIGHT`（9.5cm）までにする |

ODT と同じく、表は行の途中でページを分けない（`cantSplit`）。ページをまたいだときは、見出し行を繰り返す（`tblHeader`）。

## スタイルの調整

`md2docx.py` の先頭の定数で変える。

- 行送り：`LINE_PT`（窮屈なら 17〜18）
- 図の大きさ：`IMG_WIDTH`、`IMG_MAX_HEIGHT`
- 見出しの大きさ：`HEADING_SIZES`
- 色：`ACCENT`、`H2_BG` など
