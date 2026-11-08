"""
OS ごとに違うものを、ここで吸収する（Linux・macOS・Windows）。

- 日本語フォント：インストールされている候補から選ぶ。
- LibreOffice（soffice）：PATH と、OS ごとの既定のインストール先から探す。
- コンソール：Windows でも日本語が化けないよう、標準出力を UTF-8 にする。

どれも環境変数で上書きできる。
  EXAM_EXP_GEN_FONT      本文・図のフォント名（例：Yu Gothic）
  EXAM_EXP_GEN_MONO_FONT コードブロックのフォント名
  EXAM_EXP_GEN_SOFFICE   soffice の実行ファイルのパス
"""

import os
import shutil
import sys
from functools import cache
from pathlib import Path

# 上から順に探す。Linux（Noto）→ macOS（ヒラギノ）→ Windows（游ゴシック・メイリオ）→ その他
JP_FONTS = [
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "Hiragino Sans",
    "Hiragino Kaku Gothic ProN",
    "Yu Gothic",
    "Meiryo",
    "IPAexGothic",
    "IPAGothic",
    "MS Gothic",
]
MONO_FONTS = [
    "Noto Sans Mono CJK JP",
    "Osaka-Mono",
    "MS Gothic",
    "IPAGothic",
]


def utf8_console():
    """標準出力・標準エラーを UTF-8 にする（Windows のコンソールで日本語が化けるのを防ぐ）。"""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")


@cache
def _installed_fonts() -> set[str]:
    from matplotlib import font_manager

    return {f.name for f in font_manager.fontManager.ttflist}


def _pick(env: str, candidates: list[str]) -> str | None:
    if name := os.environ.get(env):
        if name not in _installed_fonts():
            raise SystemExit(f"{env}={name} のフォントが見つかりません")
        return name
    return next((n for n in candidates if n in _installed_fonts()), None)


@cache
def jp_font() -> str:
    """本文・図に使う日本語フォントの名前。見つからなければ止める（黙って字化けさせない）。"""
    name = _pick("EXAM_EXP_GEN_FONT", JP_FONTS)
    if name is None:
        raise SystemExit(
            "日本語フォントが見つかりません。次のどれかを入れるか、EXAM_EXP_GEN_FONT で指定してください：\n  "
            + "、".join(JP_FONTS)
        )
    return name


@cache
def mono_font() -> str:
    """コードブロック用の等幅フォント。なければ本文のフォントで代用する。"""
    return _pick("EXAM_EXP_GEN_MONO_FONT", MONO_FONTS) or jp_font()


def _soffice_candidates():
    if path := os.environ.get("EXAM_EXP_GEN_SOFFICE"):
        yield Path(path)
        return
    for cmd in ("soffice", "libreoffice"):
        if found := shutil.which(cmd):
            yield Path(found)
    if sys.platform == "darwin":
        yield Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        yield Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice"
    elif sys.platform == "win32":
        for env in ("ProgramFiles", "ProgramFiles(x86)"):
            if base := os.environ.get(env):
                yield Path(base) / "LibreOffice/program/soffice.exe"


@cache
def soffice() -> str:
    """LibreOffice の実行ファイルのパス。見つからなければ止める。"""
    for p in _soffice_candidates():
        if p.is_file():
            return str(p)
    raise SystemExit(
        "LibreOffice（soffice）が見つかりません。インストールするか、"
        "EXAM_EXP_GEN_SOFFICE に実行ファイルのパスを指定してください"
    )


def report():
    """使われるフォントと soffice を表示する。"""
    print(f"日本語フォント : {jp_font()}")
    print(f"等幅フォント   : {mono_font()}")
    try:
        print(f"soffice        : {soffice()}")
    except SystemExit as e:
        print(f"soffice        : （なし）{e}")
