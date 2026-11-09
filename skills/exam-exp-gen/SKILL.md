---
name: exam-exp-gen
description: 試験問題（PDF・画像・テキスト）を読み込み、解説を markdown で生成するスキル。作成途中の問題の書き起こし（q*.md）と解説（a*.md）は intermediates/、画像類は intermediates/images/ に置き、解説のアウトプット（ODT または DOCX）は試験ディレクトリ直下に出す。「この問題の解説を作って」「試験問題を解説して」「過去問の解説を書いて」といった依頼で使う。
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(uv run:*)
---

# 試験問題の解説生成

試験問題を読み込み、解説文書を作る。
成果物は試験ごとのディレクトリに置く。

- 作成途中のファイルは、`<試験ディレクトリ>/intermediates/` に置く。
  - 問題・解説の md（`q<番号>.md`、`a<番号>.md`）は `intermediates/` 直下。
  - 画像類（PDF のページ画像、図、切り出した画像）は `intermediates/images/`。
  - 図を作るスクリプトは `intermediates/figs/`。
- 解説のアウトプット（`solutions.odt` または `solutions.docx`）は、`<試験ディレクトリ>` 直下に出す。
- `intermediates/` と `intermediates/images/` は、なければ作る。

学年・科目・読み手は、作成依頼に従う。スキルでは特定しない。読み手の指定がなければ、書き始める前にユーザーに確認する（手順 1）。

## 全体の流れ

1. **入力を確認する**：試験ディレクトリと、その中の PDF・画像を特定する。
2. **問題を書き起こす**：`intermediates/q<問題番号>.md` を作る。
3. **解説を書く**：`intermediates/a<問題番号>.md` を作る。
4. **図を作る**：必要な図を `intermediates/images/` に作り、md から参照する。
5. **（任意）ODT または DOCX に変換する**：解説のアウトプットとして、試験ディレクトリ直下に `.odt` か `.docx` を作る。

各段階の詳細は `references/` を参照する。

| 段階 | 参照する資料 |
|---|---|
| 1〜2 | [references/output-layout.md](references/output-layout.md) |
| 3 | [references/explanation-style.md](references/explanation-style.md) |
| 2〜3 | [references/formulas.md](references/formulas.md)（数式・記号） |
| 4 | [references/figures.md](references/figures.md) |
| 5 | [references/odt-export.md](references/odt-export.md)（ODT）、[references/docx-export.md](references/docx-export.md)（DOCX） |

## 手順

### 1. 入力を確認する

- 試験ディレクトリ（`YYYYMMDD` または `YYYYMMDD_<名前>`）を特定する。
  指定がなければユーザーに聞く。
- スキャン PDF は画像として読む。
  図・表・設問番号・取り消し線など、読み取りにくい箇所は推測せず、ユーザーに確認する。
- **解説の対象と粒度は、問題から判断できないときは、書き始める前にユーザーに問い合わせる。**
  - 対象：どの大問・設問を解説するか。依頼に「すべて」などの指定がなく、PDF に複数の大問があるとき。
  - 読み手：学年と前提知識。依頼にも、試験ディレクトリの既存の解説にも指定がなければ、必ず聞く。推測や既定値で進めない。
  - 粒度：途中式をどこまで書くか、別解や発展を入れるか、図をどこまで作るか。依頼や既存の解説から決められないとき。
  - 問い合わせは、選択肢を添えて 1 回にまとめる。推奨があれば先頭に書く。
  - 依頼から判断できることは、聞かずに進める。聞くのは、答えで成果物が大きく変わるときだけにする。

- PDF は、`<試験ディレクトリ>/intermediates/images/` にページ画像（`page-1.png`、`page-2.png` …）として書き出して読む（ディレクトリは自動で作られる）。

  ```bash
  uv run <スキルのディレクトリ>/scripts/pdf2png.py <試験ディレクトリ>/<原本>.pdf -o <試験ディレクトリ>/intermediates/images
  ```

  既定の 200dpi は、図の切り出しにも使える解像度。読むだけなら `--dpi 120` でも足りる。
- 科目は理科に限らない（数学もある）。大問ごとに `intermediates/q<番号>.md`、`intermediates/a<番号>.md` を作る。

### 2. 問題を書き起こす

- `intermediates/q<番号>.md` に、問題文・図・表・選択肢を markdown で書き起こす。
- 書式は [references/output-layout.md](references/output-layout.md) に従う。
- 問題文の数式・記号は、原本のとおりに写す（[references/formulas.md](references/formulas.md)）。
- 書き起こしたら、原本と照合できるようユーザーに内容を見せる。

### 3. 解説を書く

- `intermediates/a<番号>.md` に書く。構成と文体は [references/explanation-style.md](references/explanation-style.md) に従う。
- 計算問題は途中式を省略しない。数値は問題文・表から取り直して検算する。
- 数式と記号は原本の記法を忠実に再現する。単純な式は Unicode の記号で、分数や根号などは行頭の `$$ ... $$` で書く（ODT・DOCX への変換時に自動で画像になる）。方針は [references/formulas.md](references/formulas.md)。
- 日本語の文章規範は `japanese-tech-writing` と `natural-japanese` のスキルを参照する。使えない環境では、[references/explanation-style.md](references/explanation-style.md) の「文体」だけに従う。
- 書き終えたら、`natural-japanese` など日本語を整えるスキルが使える環境では、解説の文章の推敲に使ってよい。使えない環境では、この工程を省く。
  - 推敲で変えてよいのは、文の言い回しと並び順だけ。数式・数値・用語・見出しの構成・`$$ ... $$` の記法は変えない。
  - です・ます調と短い文を保つ。読み手の水準（[references/explanation-style.md](references/explanation-style.md) の「文体」）を超えて、硬い文体にしない。
  - 推敲のあと、数値と答えが変わっていないかを問題の書き起こしと見比べる。

### 4. 図を作る

- 解説の理解に必要な図だけを作る。手順と方針は [references/figures.md](references/figures.md)。
- まず、図ごとに作り方を決める：A. 切り出し、B. 書き込み、C. データ図、D. 模式図。
  問題の図は再描画せず切り出す。写実的な絵と新しい地図は描かない。
- 図は 1 つずつスクリプト（`intermediates/figs/<図の名前>.py`）にし、`scripts/fig.py` で実行して `intermediates/images/` に PNG を作る。
- 作った画像は必ず開いて、文字の欠け・重なりと、原本との一致を確かめる。

### 5. ODT または DOCX に変換する（任意）

- ユーザーが配布用の文書を求めたときだけ行う。
- 形式は、ユーザーの指定に従う。指定がなければ、LibreOffice があれば ODT、なければ DOCX にする（`fig.py --env` で確認できる）。
- **DOCX のとき**は `scripts/md2docx.py` を使う。LibreOffice は要らない。手順は [references/docx-export.md](references/docx-export.md)。出力は `<試験ディレクトリ>/solutions.docx`。以下の ODT についての注意（1 ファイルにまとめる、出力場所、PDF での確認）は DOCX にも当てはまる。
- 大問が複数あるときは、すべての `intermediates/a<番号>.md` を **1 つの ODT**（`<試験ディレクトリ>/solutions.odt`）にまとめる。大問ごとには作らない。
- ODT は、試験ディレクトリ直下に出す。`intermediates/` には出さない。
- 手順と注意点は [references/odt-export.md](references/odt-export.md)。
  LibreOffice は CSS をほとんど無視するため、見た目は HTML 属性と変換後のスタイル書き換えで整える。
- 変換時に `--pdf` で PDF も作り、`pdf2png.py` で 70dpi 以上の画像にして崩れを確認する。

## 実行環境

Linux・macOS・Windows のどれでも動くようにする。

- 前提は **uv** と **LibreOffice**（ODT に変換するときだけ）。DOCX は LibreOffice なしで作れる（確認用の PDF は、LibreOffice がなければ Word で作る）。ほかのコマンド（pdftoppm、pandoc、ImageMagick など）は使わない。
- スクリプトはすべて、プロジェクトのルートから `uv run <スクリプト>` で実行する。
  依存は各スクリプトの先頭に PEP 723 の inline metadata で書いてあり、uv が自動で用意する。仮想環境の作成や `pip install` は要らない。
- 新しくスクリプトを作るときも、PEP 723 で依存を書き、`uv run` で動くようにする。依存は pip で入るものに限る。
- OS ごとの違い（日本語フォント、LibreOffice の場所、コンソールの文字コード）は `scripts/figkit/env.py` で吸収する。
  使われるものは `uv run <スキルのディレクトリ>/scripts/fig.py --env` で確認できる。見つからないときは、表示に従って環境変数で指定する。
- パスは `/` で区切って書く（Windows の PowerShell でも通る）。ディレクトリは各スクリプトが作るので、`mkdir` は要らない。

| スクリプト | 用途 |
|---|---|
| `scripts/pdf2png.py` | PDF をページ画像にする（手順 1、変換後の確認） |
| `scripts/fig.py` | 図のスクリプトを実行する（手順 4） |
| `scripts/figkit/` | 作図の共通部品と、OS ごとの違いの吸収 |
| `scripts/md2odt.py` | md を ODT にする（手順 5） |
| `scripts/md2docx.py` | md を DOCX にする（手順 5。LibreOffice は要らない） |

## パスの書き方

- このスキルのファイルは、SKILL.md のある場所（`<スキルのディレクトリ>`）からの相対パスで参照する。
- 成果物は、プロジェクトのルートからの相対パスで扱う。
- プロジェクト名や、特定の試験ディレクトリ名は、手順に書かない。

## 守ること

- 解説の対象や粒度が判断できないまま書き始めない。迷ったら、先に聞く（手順 1）。
- 問題の内容を書き換えない。誤字や取り消しがあれば、そのまま書き起こして注記する。
- 答えは、問題文と表から導けることを確認してから書く。
- 試験ディレクトリの外にファイルを作らない。

<!-- TODO: 実際に使って見つかった落とし穴を、ここに追記していく -->


