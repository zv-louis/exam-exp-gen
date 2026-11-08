---
title: ODT への変換
description: markdown の解説を ODT にする手順、uv の環境、LibreOffice の制約と対処。手順 5 で読む。
---

# ODT への変換

markdown の解説を、配布用の ODT にする。
`a5.md` を `a5.odt` にしたときの試行錯誤をまとめてある。

## 仕組み

```
markdown ─(python-markdown)→ HTML ─(LibreOffice)→ ODT ─(zip を書き換え)→ 完成
```

- 変換スクリプトは、このスキルの `scripts/md2odt.py`（`<スキルのディレクトリ>` は SKILL.md のある場所）。
- 前提は uv と LibreOffice。pandoc は使わない（試した環境になかった）。
- スクリプトには **inline metadata（PEP 723）で依存（`markdown`、`matplotlib`）を書いてある。** `uv run` で実行すれば、依存は uv が自動で用意する。
  仮想環境を作る必要も、`uv pip install` する必要もない。
  ほかのパッケージが必要になったら、スクリプト先頭の `dependencies` に足す。
- 本文のフォントと LibreOffice の場所は、OS に合わせて `scripts/figkit/env.py` が探す（[figures.md](figures.md) の「フォント」）。
  LibreOffice が見つからないときは、環境変数 `EXAM_EXP_GEN_SOFFICE` に実行ファイルのパスを入れる。
  例：macOS は `/Applications/LibreOffice.app/Contents/MacOS/soffice`、Windows は `C:/Program Files/LibreOffice/program/soffice.exe`（どちらも自動で探す場所）。
- 実行は、プロジェクトのルートで行う。

  ```bash
  uv run <スキルのディレクトリ>/scripts/md2odt.py <試験ディレクトリ>/intermediates/a5.md -o <試験ディレクトリ>/solutions.odt
  ```

  `-o` を省くと、md と同じ場所（`intermediates/`）に ODT ができる。解説のアウトプットは試験ディレクトリ直下に出すので、`-o` で指定する。
  画像は md からの相対パスで読む（md と画像はどちらも `intermediates/` 以下にあるので、md には `images/…` と書く）。
- **複数の md は、1 つの ODT にまとめられる。** 大問ごとに `a<番号>.md` を作った試験は、次のようにまとめる（出力先は `-o` で指定）。

  ```bash
  uv run <スキルのディレクトリ>/scripts/md2odt.py <試験ディレクトリ>/intermediates/a5.md <試験ディレクトリ>/intermediates/a6.md <試験ディレクトリ>/intermediates/a7.md -o <試験ディレクトリ>/solutions.odt
  ```

  - 2 つ目以降の md は、先頭の `# 見出し` からページを改める。
  - 配布用の ODT は、特に指定がなければこの形（試験ごとに 1 ファイル、名前は `solutions.odt`）にする。大問ごとの ODT は作らない。
- LibreOffice の呼び出し部分は次のとおり（`run_soffice`）。
  使い捨てのプロファイル（`-env:UserInstallation`）で動かすので、LibreOffice を開いたままでも変換できる。

  ```bash
  soffice -env:UserInstallation=<一時フォルダ> --headless --infilter="HTML (StarWriter)" --convert-to odt:writer8 --outdir <出力先> <入力.html>
  ```

## 数式

- 行頭の `$$ ... $$` は、変換時に自動で画像にして ODT に埋め込む。書き方は [formulas.md](formulas.md)。
- 数式の描画には matplotlib を使う（依存には入れてあるので、追加の準備は要らない）。
- 画像は HTML の `width`・`height` 属性で大きさを決めている（CSS が効かないため）。`EQ_FONT_PT` が、そのまま式の文字の pt になる。
- 式が描けないときは、終了コード 1 でエラーを出して止まる。ODT は作られない。

## 大事な注意点

- **LibreOffice の HTML 取り込みは CSS をほとんど無視する。** 効くのは `font-family` と `font-size` 程度。
  見た目を変えたいときは、次のどちらかにする。
  1. HTML の属性（`width`、`border` など）で指定する。
  2. 変換後に ODT 内のスタイルを直接書き換える。
- `@page { margin: ... }` を CSS に書いても、取り込み時には反映されない。ページ余白は `styles.xml` 側で変える。
- ODT は zip 形式。書き換えて保存し直すとき、**`mimetype` を先頭に置き、無圧縮のまま** にする。
  `zipfile.writestr(info, data, compress_type=info.compress_type)` で元の順序と圧縮方式を保つ。

## 起きた問題と対処

| 問題 | 原因 | 対処 |
|---|---|---|
| 画像が ODT に入らない恐れがあった | HTML の相対パス画像は、リンクのままになる可能性がある | PNG を base64 の data URI にして HTML に埋め込む。変換後の ODT の `Pictures/` に入ることを確認済み |
| 画像が用紙幅をはみ出して切れた | CSS の `max-width` が無視される | `<img>` に `width` と `height` の属性を付ける。縦横比は PNG ヘッダ（IHDR）から計算 |
| 表に罫線が出ない | CSS の `border` が無視される | `<table border="1" cellspacing="0" cellpadding="3">` と属性で指定する |
| 行送りが広い（6ページになった） | CSS の `line-height` と余白が無視され、`Standard` スタイルが 160% のままだった | 変換後に `styles.xml` と `content.xml` の値を書き換える。6ページが4ページになった |
| 表が 1 行目の途中でページをまたぎ、次のページの先頭に空行が出た | LibreOffice が表をページの途中で分割した | 変換後に `content.xml` の `<style:table-properties>` へ `style:may-break-between-rows="false"` を足し、表を分けないようにした（`STYLE_PATCHES` に入れてある） |
| 見出しだけ明朝体になった | 本文用のフォント指定が見出しに効かない | CSS で `h1`〜`h4`、`th`、`td` にも `font-family` を指定する |

## スタイルの調整

書き換える場所は `styles.xml` と `content.xml`。
`md2odt.py` の `STYLE_PATCHES` に「置換前 → 置換後」の組を並べてある。

- 行送り：`fo:line-height="160%"` → `118%`
- 段落や見出しの上下の余白：`fo:margin-top`、`fo:margin-bottom`
- ページ余白：`Mpm1` の上下 2cm → 1.5cm

行送りが窮屈なら、`118%` を `130%` 程度に上げる。

## 見た目の確認

ODT を目で見るために、PDF にしてから画像にする。
確認用の PDF と画像は `intermediates/` に置く（試験ディレクトリ直下には出さない）。

```bash
uv run <スキルのディレクトリ>/scripts/md2odt.py <a*.md …> -o <試験ディレクトリ>/solutions.odt --pdf <試験ディレクトリ>/intermediates/solutions.pdf
uv run <スキルのディレクトリ>/scripts/pdf2png.py <試験ディレクトリ>/intermediates/solutions.pdf --info     # ページ数
uv run <スキルのディレクトリ>/scripts/pdf2png.py <試験ディレクトリ>/intermediates/solutions.pdf -o <試験ディレクトリ>/intermediates/check --dpi 70 --sheet
```

- `--sheet` を付けると、全ページを 1 枚に並べた `page-sheet.png` もできる。全体の崩れを一度に確認できる。
- 低い解像度（50dpi）で見ると、文字が実際より小さく見える。最初「文字が小さすぎる」と誤認した。確認は 70dpi 以上で行う。

## 残っている課題

- 表を分けない設定にしたので、表がページ下端に来ると、表ごと次のページに送られ、ページ下に空きが残る。
  ページ全体より大きい表は、この設定では収まらない。その場合は表を 2 つに分ける。
- 表の導入文と表が別のページに分かれることがある。
- 表の直後に続く箇条書き（まとめ）は、表との間の余白が狭い。
- さらにページ数を減らすなら、図を小さくするか、表を簡略にする。

## 試していない代替案

- **pandoc**（`pandoc a5.md -o a5.odt`）：スタイルを参照用 ODT で一括指定でき、後処理が不要になる。インストールできれば最有力。
- **odfpy** による ODT の直接生成：スタイルを完全に制御できるが、markdown の解析を自前で書く必要がある。
