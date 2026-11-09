# exam-exp-gen

試験問題（スキャン PDF・画像・テキスト）から解説を作る、Claude Code プラグインです。

- [exam-exp-gen](#exam-exp-gen)
  - [1. 概要](#1-概要)
  - [2. 機能](#2-機能)
  - [3. 実行環境](#3-実行環境)
  - [4. インストール](#4-インストール)
    - [4-1. マーケットプレイスからインストールする](#4-1-マーケットプレイスからインストールする)
    - [4-2. npx skills でインストールする](#4-2-npx-skills-でインストールする)
    - [4-3. npx openskills でインストールする](#4-3-npx-openskills-でインストールする)
    - [4-4. 手元のディレクトリから読み込む](#4-4-手元のディレクトリから読み込む)
  - [5. 使い方](#5-使い方)
    - [5-1. スキルを使う](#5-1-スキルを使う)
    - [5-2. 作業の流れ](#5-2-作業の流れ)
    - [5-3. 成果物の置き場所](#5-3-成果物の置き場所)
  - [6. ライセンス](#6-ライセンス)

## 1. 概要

exam-exp-gen は、試験問題を読み込んで解説を作る Claude Code プラグインです。
問題の書き起こしと解説は markdown で作り、配布用に ODT または DOCX へ変換できます。

学年・科目・読み手は、作成依頼に従います。読み手の指定がなければ、解説を書き始める前に確認します。
プラグインに入っているスキルは `exam-exp-gen` の 1 つだけです。

プロジェクトの構成、開発の決まり、スクリプトのコマンドは [AGENTS.md](AGENTS.md) にあります。
Claude が従う手順は [SKILL.md](skills/exam-exp-gen/SKILL.md) にあります。

## 2. 機能

- スキャン PDF をページ画像にして問題を読み、`q<番号>.md` に書き起こします。
- 解説を `a<番号>.md` に書きます。途中式、検算、注意点が付きます。
- 解説に要る図を作ります。原本からの切り出し、書き込み、グラフ、模式図に対応しています。
- 数式を Unicode 記号と `$$ ... $$` で書き、文書に描画します。
- 解説を 1 つの文書（`solutions.odt` または `solutions.docx`）にまとめます。
- 変換した文書の確認用 PDF とページ画像を作り、見た目を確かめられます。

## 3. 実行環境

パッケージ管理に [uv](https://docs.astral.sh/uv/) を使います。
Python の依存は、各スクリプトの先頭に PEP 723 の inline metadata で書いてあります。`uv run` が自動で用意するので、仮想環境の作成や `pip install` は要りません。

| もの | 用途 | 必須か |
| --- | --- | --- |
| uv | すべてのスクリプトの実行 | 必須 |
| 日本語フォント | 図・数式・文書（Noto Sans CJK JP、ヒラギノ、游ゴシック、メイリオなど） | 必須 |
| LibreOffice | ODT の作成、確認用 PDF の作成 | ODT を作るときだけ |
| Microsoft Word | 確認用 PDF の作成（LibreOffice がないとき） | Windows で任意 |

OS ごとに要るものは次のとおりです。

| やること | Linux | Windows | macOS |
| --- | --- | --- | --- |
| DOCX を作る | 追加なし | 追加なし | 追加なし |
| DOCX の確認用 PDF | LibreOffice | LibreOffice か Word | LibreOffice |
| ODT を作る | LibreOffice | LibreOffice | LibreOffice |

確認用の PDF が作れない環境でも、DOCX は作れます。その場合は DOCX を開いて確かめてください。

使われるフォントと LibreOffice は、次のコマンドで確かめられます。

```bash
uv run skills/exam-exp-gen/scripts/fig.py --env
```

見つからないときは、環境変数で指定してください。

| 環境変数 | 内容 |
| --- | --- |
| `EXAM_EXP_GEN_FONT` | 本文・図のフォント名（例：`Yu Gothic`） |
| `EXAM_EXP_GEN_MONO_FONT` | コードブロックのフォント名 |
| `EXAM_EXP_GEN_SOFFICE` | LibreOffice（soffice）の実行ファイルのパス |

## 4. インストール

### 4-1. マーケットプレイスからインストールする

[zv-plugin-marketplace](https://github.com/zv-louis/zv-plugin-marketplace) から、Claude Code にインストールします。
Claude Code の中で、次のコマンドを実行してください。

```bash
/plugin marketplace add zv-louis/zv-plugin-marketplace
/plugin install exam-exp-gen@zv-plugins
```

マーケットプレイスを追加済みなら、2 行目だけで済みます。

### 4-2. npx skills でインストールする

[skills](https://github.com/vercel-labs/skills) CLI で、スキル `exam-exp-gen` だけを入れられます。Node.js が要ります。
Claude Code のほか、Codex や Cursor など、対応するエージェントにも入れられます。

```bash
# 現在のプロジェクトに入れる
npx skills add zv-louis/exam-exp-gen

# 全プロジェクトで使えるように、ユーザー領域に入れる
npx skills add zv-louis/exam-exp-gen --global

# Claude Code だけに入れる
npx skills add zv-louis/exam-exp-gen --agent claude-code
```

- 入れる前にスキルの一覧だけ見るには、`--list` を付けます。
- 更新は `npx skills update`、削除は `npx skills remove exam-exp-gen` です。
- この方法で入れたスキルは、`/exam-exp-gen` で呼び出します（プラグイン名の接頭辞は付きません）。

### 4-3. npx openskills でインストールする

[openskills](https://github.com/numman-ali/openskills) でも入れられます。
Claude Code 形式のスキルを、ほかのエージェントでも使えるようにするツールです。Node.js が要ります。

```bash
# 現在のプロジェクト（./.claude/skills）に入れる
npx openskills install zv-louis/exam-exp-gen

# ユーザー領域（~/.claude/skills）に入れる
npx openskills install zv-louis/exam-exp-gen --global
```

- Claude Code 以外のエージェントで使うときは、`--universal` を付けて `.agent/skills` に入れ、`npx openskills sync` で `AGENTS.md` にスキルの一覧を書き出します。
- 入れたスキルの確認は `npx openskills list`、更新は `npx openskills update` です。

### 4-4. 手元のディレクトリから読み込む

開発中のプラグインを試すときは、このプロジェクトのディレクトリを指定して、Claude Code を起動します。

```bash
claude --plugin-dir <このプロジェクトのパス>
```

## 5. 使い方

### 5-1. スキルを使う

試験問題の PDF や画像を置いたディレクトリ（試験ディレクトリ）で、Claude Code に依頼します。

```text
この問題の解説を作って
大問 5 の解説を書いて
解説を docx にして
```

スキルは `/exam-exp-gen:exam-exp-gen` で直接呼び出すこともできます。

### 5-2. 作業の流れ

スキルでは以下の手順で作業を進めます。  

1. **入力を確認する**：試験ディレクトリと、その中の PDF・画像を特定します。
2. **問題を書き起こす**：`intermediates/q<番号>.md` を作ります。
3. **解説を書く**：`intermediates/a<番号>.md` を作ります。`natural-japanese` など日本語を整えるスキルが入っていれば、書いた文章の推敲に使うことがあります（数式・数値・用語は変えません）。
4. **図を作る**：必要な図を `intermediates/images/` に作り、md から参照します。
5. **ODT または DOCX に変換する**（任意）：試験ディレクトリ直下に `.odt` か `.docx` を作ります。

### 5-3. 成果物の置き場所

試験ごとに 1 つのディレクトリを作り、その中に置きます。

```text
<試験ディレクトリ>/
├── <原本>.pdf
├── solutions.docx         ← 配布用（または solutions.odt）
└── intermediates/
    ├── q5.md              ← 問題の書き起こし
    ├── a5.md              ← 解説
    ├── images/            ← ページ画像・図の PNG
    ├── figs/              ← 図を作るスクリプト
    ├── solutions.pdf      ← 確認用
    └── check/             ← 確認用の PDF を画像にしたもの
```

## 6. ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
詳しくは [LICENSE](LICENSE) を参照してください。
