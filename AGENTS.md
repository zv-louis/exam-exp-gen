# exam-exp-gen プロジェクト

## このプロジェクトについて

試験問題（スキャン PDF・画像・テキスト）を読み込み、解説を生成する Claude Code プラグインを開発している。
プラグインに入っているのは、スキル `exam-exp-gen` の 1 つだけ。

- 使い方と必要なものは [README.md](README.md)。スクリプトのコマンドは、この AGENTS.md の「スクリプトのコマンド」。
- Claude が従う手順は [skills/exam-exp-gen/SKILL.md](skills/exam-exp-gen/SKILL.md)。

## ディレクトリ構成

```text
README.md                       プラグインの説明（人向け）
LICENSE                         ライセンス（MIT）
AGENTS.md                       開発の決まり（このファイル）
.claude-plugin/plugin.json      プラグインの定義（name: exam-exp-gen）
skills/exam-exp-gen/
├── SKILL.md                    スキルの手順（Claude 向け）
├── references/                 手順ごとの詳細（SKILL.md から参照する）
└── scripts/                    変換・作図のスクリプト（uv run で実行）
.data/                          試しに使う試験データ（git の管理外）
```

- `.data/<試験ディレクトリ>/` は、スキルを試すための実データ。原本の PDF と、作った解説が入っている。コミットしない。
- `.claude/skills/exam-exp-gen` は、スキルを手元で読み込ませるための自分自身へのリンク（git の管理外）。

`references/` には、解説の書き方の決まりがある。

| ファイル | 内容 |
| --- | --- |
| [output-layout.md](skills/exam-exp-gen/references/output-layout.md) | 試験ディレクトリの構成、問題の書き起こしの書式 |
| [explanation-style.md](skills/exam-exp-gen/references/explanation-style.md) | 解説の構成と文体 |
| [formulas.md](skills/exam-exp-gen/references/formulas.md) | 数式・記号の書き方（Unicode と `$$ ... $$`） |
| [figures.md](skills/exam-exp-gen/references/figures.md) | 図の作り方 |
| [odt-export.md](skills/exam-exp-gen/references/odt-export.md) | ODT への変換と、LibreOffice の制約 |
| [docx-export.md](skills/exam-exp-gen/references/docx-export.md) | DOCX への変換と、Word での見た目の調整 |

## 開発の決まり

### スクリプト

- Linux・macOS・Windows のどれでも動くようにする。
- 実行は、プロジェクトのルートから `uv run <スクリプト>` で行う。依存は各スクリプトの先頭に PEP 723 の inline metadata で書く。依存は pip で入るものに限る。
- 外部コマンド（pandoc、pdftoppm、ImageMagick など）は使わない。例外は LibreOffice（ODT の作成と、確認用 PDF の作成）と、Windows の Word（確認用 PDF の作成だけ）。
- OS ごとの違い（日本語フォント、LibreOffice の場所、コンソールの文字コード）は `scripts/figkit/env.py` にまとめる。ほかのスクリプトに OS の分岐を書かない。
  - 例外：`md2docx.py` の確認用 PDF は、LibreOffice がない Windows でだけ Word を使う。
- `md2docx.py` は、数式の描画などを `md2odt.py` から読み込んでいる。`md2odt.py` の関数を変えるときは、`md2docx.py` も動かして確かめる。

### 出力形式

| 形式 | スクリプト | 必要なもの |
| --- | --- | --- |
| ODT | `md2odt.py` | LibreOffice |
| DOCX | `md2docx.py` | なし（python-docx で直接作る） |
| 確認用 PDF（`--pdf`） | 両方 | LibreOffice、なければ Windows の Word（DOCX のときだけ） |

### スクリプトのコマンド

どれもプロジェクトのルートで `uv run` で実行する。`<試験>` は試験ディレクトリ。

#### `pdf2png.py`

PDF をページごとの PNG にする。

```bash
uv run skills/exam-exp-gen/scripts/pdf2png.py <試験>/<原本>.pdf -o <試験>/intermediates/images
```

- `-o, --outdir DIR`：出力先。なければ作る。
- `--dpi DPI`：解像度。既定は 200。読むだけなら 120、ODT・DOCX の確認は 70 以上にする。
- `--prefix PREFIX`：ファイル名の頭。既定は `page`（`page-1.png`）。
- `--pages N [N ...]`：書き出すページ（1 始まり）。省くとすべて。
- `--sheet`：全ページを並べた `<prefix>-sheet.png` も作る。
- `--info`：ページ数を表示するだけ。

#### `fig.py`

図のスクリプト（`intermediates/figs/*.py`）を実行する。作図の共通部品は `scripts/figkit/`。

```bash
uv run skills/exam-exp-gen/scripts/fig.py <試験>/intermediates/figs
```

- `paths`：図のスクリプト、またはそれを入れたフォルダ。
- `--grid IMAGE`：方眼を重ねた画像を作る。切り出し位置を測るときに使う。
- `--step N`：方眼の間隔（画素）。
- `--env`：使うフォントと soffice を表示する。

#### `md2docx.py`

md を DOCX にする。python-docx で直接作るので、LibreOffice は要らない。

```bash
uv run skills/exam-exp-gen/scripts/md2docx.py <試験>/intermediates/a5.md <試験>/intermediates/a6.md \
    -o <試験>/solutions.docx --pdf <試験>/intermediates/solutions.pdf
```

- `md`：変換する md。複数なら 1 つの DOCX にまとめる。
- `-o, --output FILE`：出力する DOCX。md が複数のときは必須。
- `--pdf FILE`：確認用の PDF も作る。

#### `md2odt.py`

md を ODT にする。LibreOffice を使う。引数は `md2docx.py` と同じ。

```bash
uv run skills/exam-exp-gen/scripts/md2odt.py <試験>/intermediates/a5.md -o <試験>/solutions.odt
```

#### 見た目の確認

確認用の PDF をページ画像にして見る。

```bash
uv run skills/exam-exp-gen/scripts/pdf2png.py <試験>/intermediates/solutions.pdf \
    -o <試験>/intermediates/check --dpi 100 --sheet
```

### 変更したら確かめること

- 変換スクリプトや体裁を変えたら、`.data/` の試験で実際に変換し、PDF を画像にして見た目を確かめる（手順は `references/odt-export.md`・`references/docx-export.md` の「見た目の確認」）。
  - 確認する点：ページ数、表の列幅と改ページ、図の大きさ、数式、見出しのフォント。
  - 低い解像度では文字が小さく見えるので、70dpi 以上で見る。
- 見つかった問題と対処は、対応する `references/*.md` の「起きた問題と対処」に追記する。

### 文書の書き方

- SKILL.md・references・README は日本語で、短い文で書く。
- SKILL.md・references には、プロジェクト名や特定の試験ディレクトリ名を書かない。パスは `<スキルのディレクトリ>`、`<試験ディレクトリ>` のように書く。
  - README はプラグインの説明なので、プラグイン名（exam-exp-gen）を書いてよい。特定の試験ディレクトリ名は書かない。
- 手順を変えたら、SKILL.md、該当する references、ルートの README の 3 つをそろえる。
