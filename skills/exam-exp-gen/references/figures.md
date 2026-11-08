---
title: 図の作り方
description: 解説に載せる図の作り方（切り出し・書き込み・データ図・模式図）の選び方と、figkit を使った作図の手順。手順 4 で読む。
---

# 図の作り方

## 方針

- 解説の理解に必要な図だけを作る。装飾のための図は作らない。
- 図はすべて **Python のスクリプト** で作り、スクリプトを残す。直すときは、スクリプトを直して実行し直す。
- 作図は `scripts/figkit`（matplotlib と Pillow）で行う。Linux・macOS・Windows で同じように動く。
  外部のコマンド（rsvg-convert、inkscape、graphviz、ImageMagick）は使わない。

## 作り方を選ぶ

図を作る前に、次の 4 つのどれで作るかを決める。科目では決めない。

| 作り方 | 対象 | 例 | figkit |
|---|---|---|---|
| **A. 切り出し** | 問題に載っている図、写真、地図、写実的な絵 | 実験装置の図、資料写真、地形図、グラフ | `fk.crop` |
| **B. 書き込み** | 問題の図に、解答の線・印・注記を重ねる | 補助線、角の印、地図上の位置、グラフの読み取り線 | `fk.on_image` |
| **C. データ図** | 数値から描くグラフ | 関数、実験結果、雨温図、人口ピラミッド、統計の推移 | `fk.chart` |
| **D. 模式図** | 図形や部品を組み合わせて描く図 | 回路、てこ、光の道すじ、天体の配置、幾何図形、年表、因果関係の図 | `fk.canvas` |

- **問題の図は、再描画せず A で切り出す。** 原本と同じ図になり、読み間違いも入らない。
- 解説に描き足すときは、まず B（切り出した図に重ねる）を考える。問題の図と見比べやすい。
- 新しく描くのは C と D だけ。
- **写実的な絵（動物・植物・器具の写真の代わり）と、新しい地図は描かない。** 問題の図を切り出すか、文章で説明する。
  地図を作るライブラリ（cartopy など）は重く、OS によって入らないため使わない。
- 迷ったら、作る図と作り方を書き出して、ユーザーに確認する。

## ファイルの置き場所と名前

```
<試験ディレクトリ>/intermediates/
├── figs/                 # 図のスクリプト（1 つの図に 1 つ）
│   ├── q6_fig_1.py
│   └── a6_fig_angles.py
└── images/               # できた PNG（スクリプトと同じ名前）
    ├── q6_fig_1.png
    └── a6_fig_angles.png
```

- 問題の図は `q<番号>_fig_*.py`、解説の図は `a<番号>_fig_*.py`。
- `fk.save(fig, __file__)` と書くと、`images/<スクリプト名>.png` に保存される。名前は自動でそろう。
- md（`intermediates/` にある）からは、`images/…` の相対パスで参照する。

## 実行のしかた

プロジェクトのルートで実行する。figkit を読み込めるようにしてから、図のスクリプトを実行する。

```bash
uv run <スキルのディレクトリ>/scripts/fig.py <試験ディレクトリ>/intermediates/figs/a6_fig_angles.py
uv run <スキルのディレクトリ>/scripts/fig.py <試験ディレクトリ>/intermediates/figs     # すべて
```

- フォルダを渡すと、`q*`（切り出し）を先に、`a*` をあとに実行する。`a*` が `q*` の画像を下地に使えるようにするため。
- `_` で始まるファイルは実行しない（共通の部品を置くときに使う）。
- 使われるフォントと LibreOffice は `uv run <スキルのディレクトリ>/scripts/fig.py --env` で確認できる。

## 書き方

### A. 切り出し

```python
import figkit as fk

page = fk.image(__file__, "page-2.png")             # intermediates/images/page-2.png
fk.crop(page, (990, 540, 1470, 920), __file__)      # (左, 上, 右, 下) の画素
```

- ページ画像は 200dpi で書き出したもの（SKILL.md の手順 1）を使う。
- 切り出す座標は、方眼を重ねた画像で読み取る。方眼の画像は一時フォルダに作られ、成果物には入らない。

  ```bash
  uv run <スキルのディレクトリ>/scripts/fig.py --grid <試験ディレクトリ>/intermediates/images/page-2.png
  ```

- 切り出したら画像を開いて、はみ出しや欠けがないか見る。図の見出し（「図 1」など）が入ってもよい。
- **手書きの書き込みや汚れは、原本にないものとして扱う。** 解説の根拠にしない。
  - スキャンの汚れ（薄い線、かすれ、点）で、図の意味に影響しないものは、無視してそのまま切り出す。
  - 印刷された印か、書き込みか、汚れかの区別に迷うときは、推測せずユーザーに確認する（グラフ上の丸印が書き込みだった例がある）。
    確認するときは、該当箇所の位置と、どう見えるかを添える。
  - 書き込みを消すときは、周りの格子線がつながるように、同じ格子の別の場所の画素を貼って埋める（Pillow の `crop` と `paste`）。白で塗りつぶすと、線が途切れる。
  - 消す前の画像は残さない。図を差し替えたら、代替テキストと、その図を根拠にした解説の記述も見直す。

### B. 書き込み

```python
import figkit as fk

fig, ax = fk.on_image(fk.image(__file__, "q6_fig_2.png"))
# 座標は画像の画素。左上が原点で、y は下向き
ax.plot([10, 360], [120, 300], color=fk.ALERT)
ax.text(200, 180, "補助線", color=fk.ALERT, fontsize=fk.LABEL_PT)
fk.save(fig, __file__)
```

- 書き込む位置は、切り出した画像に `--grid` を使って読み取る。

### C. データ図

```python
import figkit as fk

fig, ax = fk.chart(h=7)                     # 高さ 7 cm（幅は本文幅）
ax.plot(x, y, color=fk.MAIN, label="かずきさん")
ax.set_xlabel("時間〔分〕")
ax.set_ylabel("道のり〔m〕")
fig.legend(loc="outside upper center", ncols=2)   # 凡例は図の外（上）
fk.save(fig, __file__)
```

- 上と右の枠線は消してある。横の格子線だけ薄く出る（`grid=False` で消せる）。
- 軸の名前の単位は、原本の書き方（〔 〕、( ) など）に合わせる。

### D. 模式図

```python
import figkit as fk
from matplotlib.patches import Circle, Polygon, Rectangle

fig, ax = fk.canvas((0, 10), (0, 4))        # x：0〜10、y：0〜4。縦横は同じ縮尺。軸なし
ax.add_patch(Rectangle((0.5, 2), 9, 0.2, color=fk.INK))        # てこの棒
ax.add_patch(Polygon([(5, 2), (4.5, 1), (5.5, 1)], color=fk.SUB))  # 支点
ax.annotate("", (2, 0.8), (2, 2), arrowprops=dict(arrowstyle="-|>", color=fk.MAIN, lw=2))
ax.text(2, 0.5, "30 g", ha="center", color=fk.MAIN, fontsize=fk.LABEL_PT)
fk.save(fig, __file__)
```

- 座標は、問題の数値（長さ・角度）に合わせて決める。正確な縮尺で描けるのが、模式図を描く利点。
- 円・多角形・曲線（`matplotlib.patches`、`matplotlib.path.Path`）の組み合わせで描く。
- 同じ部品を何度も使うときは、`figs/_parts.py` に関数として置き、図のスクリプトから `from _parts import …` で読む。

## 体裁（figkit の既定値）

figkit を読み込むと、次の体裁が設定される。個別の図で変えるのは、必要なときだけにする。

| 項目 | 値 | 理由 |
|---|---|---|
| 幅 | 13.8 cm（`fk.WIDTH_CM`） | md2odt.py は、どの画像もこの幅で ODT に載せる。この幅で描けば、pt がそのまま印刷の大きさになる |
| 解像度 | 200dpi | 印刷に足りる |
| 文字 | 注記・目盛り 10pt（`fk.FONT_PT`）、軸の名前・主な語 11pt（`fk.LABEL_PT`） | 本文（11pt）と同じくらいに見える |
| フォント | OS の日本語フォント（下の「フォント」） | 本文と同じ |
| 式 | `$...$` で書く。字体は Computer Modern | md2odt.py の数式と同じ見た目 |
| 線 | 図の線 1.4pt（`fk.LINE_W`）、補助線 0.8pt（`fk.THIN_W`） | |

### 色

1 つの図で使うのは 2〜3 色まで。同じものは同じ色で通す（等しい辺や角、2 人の動きなど）。

| 名前 | 用途 |
|---|---|
| `fk.INK` | 線・文字の基本（黒に近い灰色） |
| `fk.MAIN` | 主役（ODT の見出しと同じ青） |
| `fk.ACCENT` | 比べる相手、増えた分（橙） |
| `fk.ALERT` | 答え、強調したい差（赤） |
| `fk.SUB` | 補助線、参考（灰色） |
| `fk.COLORS["fill"]`、`fk.COLORS["fill2"]` | `MAIN`、`ACCENT` の薄い塗り |

### 注記

- 注記が線や軸に重なっていないか、画像で確かめる。白い下地で隠すと、線が途切れて見えるので使わない。
- 凡例は、図の外（上）に出す。
- 図の見出し（タイトル）は、なるべく図に入れず、md の本文で説明する。
- 文の途中の式は `$F \times \ell$` のように書ける。日本語は `$...$` の外に書く（式の字体には日本語の字形がない）。

## フォント

- 日本語フォントは、インストールされているものから次の順で選ぶ（`scripts/figkit/env.py`）。
  Noto Sans CJK JP（Linux）→ Noto Sans JP → ヒラギノ角ゴシック（macOS）→ 游ゴシック → メイリオ（Windows）→ IPAex ゴシック。
- 別のフォントを使いたいときは、環境変数 `EXAM_EXP_GEN_FONT` にフォント名を入れる。
- ODT の本文も同じフォントになる。OS が違うと、同じ md でも字形が少し変わる。

## 確認

- 作ったら画像を開いて、次を確かめる。
  - 文字の欠け・はみ出し・重なり
  - 原本の図・数値と合っているか（座標、長さ、記号）
- 字形のない文字（絵文字、フォントにない記号）が入ると、`fk.save` は保存せずにエラーで止まる。別の文字に置き換える。
