# Research: CANログ解析コアとコマンドライン

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-22

Technical Context に残った不明点と、MFC 版と文字列一致させるために調べたことをまとめる。

## R-1 正解生成プログラムで reference/mfc を書き換えずにビルドできるか

- **Decision**: `tools/mfc_golden/pch.h` に中身のない（`#pragma once` だけの）差し替え用ヘッダを置き、
  `/I tools/mfc_golden /I reference/mfc/CanSim` を付けて `reference/mfc/CanSim/LogAnalysis.cpp` をそのままコンパイルする。
- **Rationale**: `LogAnalysis.cpp` の先頭は `#include "pch.h"` で、`reference/mfc/pch.h` は `framework.h` 経由で MFC
  （`afxwin.h` 等）を読み込む。MSVC は `"..."` のインクルードを、まずインクルードしたファイルのディレクトリ
  （`reference/mfc/CanSim/`、ここに pch.h はない）で探し、次に `/I` で探すので、差し替え用の pch.h が使われる。
  `LogAnalysis.cpp` 自体は標準ライブラリしか使わない。
  2026-10-22 に scratchpad で試し、Visual Studio 2022 Professional（`vcvars64.bat`、`cl /std:c++17 /EHsc /O2 /utf-8`）で
  警告なしにビルドでき、`sample_vehicle_16ecu` のログを 16080 行読んで 4 つの解析が動くことを確認した
  （送信待ち時間 32 行、受信完了時間 54 行、ジッタ 31 行、範囲 5000 ms）。
- **Alternatives considered**: `reference/mfc/CanSim/LogAnalysis.cpp` を tools にコピーして pch 行を消す
  → コピーが本物とずれる危険があり、FR-040b（そのまま使う）に反する。MFC 込みでビルド → 不要な依存で、MFC がない環境で作れない。

## R-2 Python のバージョン

- **Decision**: Python 3.11 以上（憲章どおり）。開発 PC には現在 Python 3.9.13 しかないので、
  実装の前に 3.11 以上（3.12 推奨）を入れる（quickstart の前提条件）。
- **Rationale**: 憲章「技術的制約」で 3.11 以上と決めている。次の画面機能で使う PySide6 の新しい版も 3.9 を外していく。
- **Alternatives considered**: 3.9 に下げる → 憲章の改定が必要で、得るものがない。

## R-3 ログの読み込み方法（pandas / csv モジュール / 自前）

- **Decision**: 標準ライブラリだけで、MFC 版 `ReadLogRecords` と同じ手順の自前パーサを書く。
  ファイルを 4 MB ずつバイナリで読み、`\n` で行に分け、行末の `\r` を 1 つ除き、`,` で分割する。
  値は MFC と同じ規則で検査してから `int()` で変換する（後述）。読んだ結果は列ごとの `array('q')`（8 バイト整数）に詰める。
- **Rationale**:
  - エラーメッセージ（`line N: bad number` 等）と行番号の数え方（空行も 1 行と数える、ヘッダの誤りは常に line 1）を
    MFC と一致させるには、行ごとの判定を自分で書く必要がある。pandas はエラーの文言・行番号を制御できない。
  - `csv` モジュールは引用符を解釈するが、MFC は引用符を解釈しない。違う結果になりうる。
  - Python の `int()` は `" 12"`、`"1_000"` を受け付けるが MFC は受け付けない。
    そこで「先頭の `+`/`-` を除いた残りが 1 文字以上で、`bytes.isdigit()` が真」のときだけ変換する。
    CAN_ID は「`0x`/`0X` + 16 進 1 文字以上」を正規表現 `rb"0[xX][0-9A-Fa-f]+"` の完全一致で検査する。
  - 300 万行を 1 行ずつ Python オブジェクトにすると数 GB 使うので、列ごとの整数配列にする（憲章 原則 IV）。
    8 列 × 300 万行 × 8 バイト ≒ 190 MB。
    解析の途中で集める値（受信完了時間の全体・組ごと、送信待ち時間の全体・ID ごと）も `list[int]` ではなく `array('q')` に入れる。
    `list[int]` だと 256 を超える値は 1 つ 28 バイトの int オブジェクト＋8 バイトの参照になり、受信完了時間だけで
    300 万 × 2 × 36 バイト ≒ 216 MB 増える。`array('q')` なら 1 つ 8 バイト。並べ替えは `array('q', sorted(a))` で行う
    （一時的に list ができるが、解析ごとに解放される）。（/speckit-analyze C1 の解決）
  - 見積もり: 1 行あたり分割＋7 回の検査・変換で 3〜5 µs → 300 万行で 10〜15 秒。解析を含めて SC-003 の 1 分に収まる。
    実測は性能テスト（tests/perf）で確かめる。
- **Alternatives considered**: pandas（速いがエラー互換が取れず、依存が重い）、numpy の `loadtxt`（同じ理由）、
  1 行 1 オブジェクトの dataclass（メモリ不足）。

## R-4 浮動小数点の結果を MFC と同じ文字列にする方法

MFC 版の数値のうち浮動小数点を通るのは、平均、ジッタの標準偏差、負荷率（%）、ヒストグラムのビン幅。
次の方針で、計算の手順を C++ と同じにする。

- **平均**: C++ は整数値を double に変えて順に足し、件数で割る。値はどれも整数で、合計が 2^53 未満なら
  途中の和はすべて正確なので、Python では `float(sum(values)) / count` で同じ値になる（合計 2^53 µs ≒ 285 年分なので超えない）。
- **標準偏差**: `mean = float(sum) / n` のあと、時系列順に `d = float(v) - mean; squares += d * d` を 1 つずつ足し、
  `math.sqrt(squares / n)` を取る。足す順番が結果の最後の桁に効くので、`statistics.pstdev`、`math.fsum`、numpy
  （ペアワイズ加算）は使わない。MSVC x64 の既定（SSE2、`/fp:precise`、FMA へのまとめなし）と Python の float は
  どちらも IEEE 754 倍精度で、四則演算と `sqrt` は正しく丸められるので、同じ順で計算すれば同じ値になる。
- **負荷率**: `100.0 * busy / section` を同じ順（掛けてから割る）で計算する。
- **小数 1 桁・3 桁の表示**: MFC の `CString::Format("%.1f")` は UCRT の printf で、VS2019 以降は正しく丸める
  （2 進数の値を 10 進に正確に変換して丸める）。Python の `"%.1f" % x` も正しく丸めるので一致する。
  Python 側も `%` 書式を使い、`round()`（銀行丸め）は使わない。
- **ヒストグラムのビン幅（NiceCeil）**: `math.log10`、`math.floor`、`math.pow(10.0, …)` を使い、`1e-9` の許容も C++ と同じにする。
  CPython の Windows 版は MSVC の CRT の数学関数を呼ぶので結果も同じ。`std::llround` は 0.5 を 0 から遠いほうへ丸めるので、
  正の値について `math.floor(x + 0.5)` で置き換える（ビン幅は常に正）。
- **周期の表示**: `PeriodUs % 1000 == 0` なら整数 ms（`PeriodUs // 1000`、負の周期では C++ の切り捨て除算と違うので
  `int(PeriodUs / 1000)` ではなく、C++ と同じ 0 方向への切り捨てを使う）、そうでなければ `"%.3f" % (PeriodUs / 1000.0)`。
  負の剰余も C++（0 方向）に合わせる。
- **Rationale**: 憲章 原則 I。正解 CSV は同じ C++ コードから作るので、ずれがあれば golden テストで必ず見つかる。

## R-5 送信のまとめ方（CollectTransmissions と AnalyzeBusLoad の違い）

- **Decision**: 2 つの関数を別々に移植し、まとめ方を共通化しない。
  - 送信待ち時間・ジッタ（`CollectTransmissions`）: OVERWRITE を数えて除き、Tx_Request と Tx_Start が 0 以上の行だけを
    使う。キー (CanId, TxStart, TxNode) が最初に出た行を残し、(CanId, TxStart, TxNode) の昇順に並べる。
  - バス負荷（`AnalyzeBusLoad`）: OVERWRITE、Tx_Start < 0、Tx_End ≦ Tx_Start の行を除く（Tx_Request は見ない）。
    キー (TxNode, CanId, TxStart) が最初に出た行の Tx_End を使う。
- **Rationale**: 条件が少しずつ違う（Tx_Request の要否、Tx_End の条件）。共通化すると、どちらかの条件が変わりやすい。
  C++ の `CollectTransmissions` はバケットごとに「隣の重複を飛ばす → 並んでいなければ sort → unique」なので、
  同じキーで Tx_Request だけが違う行がある異常なログでは、どちらが残るかが `std::sort` の実装次第になる。
  シミュレータはそういうログを出さないので、Python は「最初に出た行を残す」に決め、research に記録する
  （ログが時刻順なら C++ と同じ結果）。
- **Alternatives considered**: C++ のバケット＋unique をそのまま再現 → 不安定ソートの結果までは再現できず、得るものがない。

## R-6 コマンドラインの形と出力形式

- **Decision**:
  - コマンド名 `can-log-analysis`（`python -m can_log_analysis` でも同じ）。引数は .canprj のパス、
    `--analysis {all,latency,busload,txwait,jitter}`（既定 all、複数回指定可）、`--output-dir DIR`。
  - 表の出力形式は「表 CSV」（[contracts/table-csv.md](contracts/table-csv.md)）。1 行目が表題、2 行目が注記または要約、
    3 行目が列見出し、4 行目以降が表の行。UTF-8（BOM なし）、改行 LF、引用符なし。
  - `--output-dir` があれば `latency.csv`、`busload.csv`、`txwait.csv`、`jitter.csv` に書く。なければ標準出力に、
    表の間を空行 1 行で区切って出す。
  - all のときの順は MFC の「解析」メニューの順（送信待ち時間、受信完了時間、送信ジッター、CAN バス負荷。
    `MFCApplication1.rc` の IDR_MAINMENU）。2026-10-22 修正: 当初は元仕様 AR-090 の並び（受信完了時間、CAN バス負荷、
    送信待ち時間、送信ジッタ）を MFC の順と取り違えていた。機能 002 の spec 作成時に .rc を確かめて判明し、MFC に合わせた。
- **Rationale**: 正解 CSV と同じ形式にすれば、golden テストはファイルの文字列比較だけで済む（FR-038）。
  表のセルには `,`・`"`・改行が入らない（列名・注記の区切りは全角の「、」）ので、引用符なしで曖昧さがない。
  念のため書き出し時に `,` `"` 改行を含むセルがあればエラーにする。
- **Alternatives considered**: JSON（人が見比べにくく、正解生成の C++ 側が重くなる）、タブ区切りの整形テキスト
  （比較はできるが、表計算ソフトで開きにくい）。

## R-7 標準出力の文字コード

- **Decision**: 標準出力・標準エラーは常に UTF-8 で書く（`sys.stdout.reconfigure(encoding="utf-8")`）。
- **Rationale**: 列名の「µ」(U+00B5) や「→」「−」は日本語 Windows の既定（cp932）で表せないか、別の文字に化ける。
  比較用の出力が環境で変わるのを避ける。コンソールで読むときは `chcp 65001` か Windows Terminal を使う（quickstart に記載）。
- **Alternatives considered**: コンソールの文字コードに合わせる → 出力が環境で変わり、FR-038 に反する。

## R-8 エラーと終了コード

- **Decision**: 解析コアは例外で失敗を伝える。`ProjectNotFoundError`、`LogNotFoundError`、
  `LogReadError(message)`（message は MFC と同じ英文 `line N: ...`、`cannot open the file`、`cannot read the file`）、
  `LogReadCancelled`。コマンドラインはメッセージを標準エラーに 1 行で出し、終了コードは
  入力の誤り 1、引数の誤り 2（argparse の既定）、Ctrl+C での中止 130（R-12）、成功 0。
- **Rationale**: Python の流儀に合い、画面機能でもそのまま `try/except` で使える。中止を例外にすると「中止されたか」を確実に区別できる（FR-007）。
- **ログがないときの文言**: `プロジェクト「<ファイル名>」のシミュレーションログはありません。`（IDS_LOG_NONE の 1 文目）。
  .canprj がないときは `プロジェクトファイルがありません: <パス>`（MFC には相当する文言がないため本ツールで決める。
  MFC の画面ではプロジェクトを開けないので解析に進まない、のと同じ扱い）。

## R-9 .canprj の読み方

- **Decision**: `configparser`（`interpolation=None`、`strict=False`、UTF-8）で読み、読めなければ
  `ProjectReadError`。この機能で使うのはパスとファイル名だけで、各セクションの値の検査はしない。
- **Rationale**: FR-002（INI として読む。値は計算に使わない）。MFC は .canprj が壊れていればプロジェクトを開けず解析に
  進まないので、読めないときに失敗するのは MFC と同じ扱い。値の検査は YAGNI（憲章 原則 V）。
- **プロジェクト名**: MFC の `ProjectFileName()` と同じく、パスの最後の `\` または `/` より後ろ（拡張子付き、例 `sample_vehicle_16ecu.canprj`）。

## R-10 テストの構成と性能テスト

- **Decision**: pytest。`tests/unit`（関数ごと・境界条件）、`tests/integration`（CLI と golden）、
  `tests/perf`（300 万行の合成ログ、`-m perf` を付けたときだけ実行）。合成ログはテスト中に一時フォルダへ生成し、版管理しない。
- **Rationale**: 憲章 原則 III。300 MB のファイルを毎回作るのは遅いので、性能テストは既定では動かさない。

## R-12 コマンドラインの進捗と中止（/speckit-analyze D1 の解決）

- **Decision**: CLI は `time.monotonic()` で開始時刻を取り、`read_log_records` に渡す `progress` の中で、0.5 秒を超えていれば
  標準エラーに `ログを読み込んでいます... N%` を出す。読み込み後に `集計しています...` を出す。`--quiet` で止める。
  Ctrl+C は `KeyboardInterrupt` を `main` で受け止め、`中断しました。` と終了コード 130（128 + SIGINT の慣例）。
  時刻の取得はテストで差し替えられるよう、`cli` モジュールの関数（例 `_now = time.monotonic`）経由にする。
- **Rationale**: 憲章 原則 IV の MUST（0.5 秒を超える処理は進捗表示と中止）をコマンドラインでも満たす。進捗を標準エラーだけに
  出せば、標準出力の表 CSV と golden の比較には影響しない。文言は MFC 版の「解析中」ウィンドウ（IDS_ANALYZING_READ、
  IDS_ANALYZING_CALC）と同じ。中止の文言は、MFC の IDS_ANALYZING_CANCEL（「中断しています...」）が途中経過の表現なので、
  終了時の表現として「中断しました。」とする。
- **Alternatives considered**: 進捗を出さない（憲章違反）、進捗バー用ライブラリ（依存が増える。R-11）、
  解析コアの中止（`progress` が False を返す）を Ctrl+C に使う → 計算中は止められないので `KeyboardInterrupt` を直接使う。

## R-11 依存ライブラリ

- **Decision**: 実行時の依存は標準ライブラリだけ。開発時は pytest のみ。numpy・matplotlib・PySide6 は次の画面機能で入れる。
- **Rationale**: 憲章 原則 V（いま必要な分だけ）。R-4 のとおり、numpy の加算順は MFC と違うので解析には使わない。
