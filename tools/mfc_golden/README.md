# mfc_golden — 正解 CSV の生成プログラム

MFC 版 CAN バスシミュレータの解析コード（`reference/mfc/CanSim/LogAnalysis.cpp`）を**そのまま**ビルドし、
4 つの解析画面（受信完了時間、CAN バス負荷、送信待ち時間、送信ジッター）の表を
表 CSV（[contracts/table-csv.md](../../specs/001-log-analysis-core-cli/contracts/table-csv.md)）で書き出す。
Python 版（`can_log_analysis`）の golden テストは、このファイルとの文字列一致で MFC 版との一致を確かめる。

- `reference/mfc/` 配下は変更もコピーもしない。`LogAnalysis.cpp` 先頭の `#include "pch.h"` は、
  このフォルダの中身のない `pch.h` が読まれる（`reference/mfc/pch.h` は MFC を読み込むため）。
- セルの書式は `reference/mfc/AnalysisDlg.cpp` と同じ書式文字列（`ECU %02d`、`0x%03X`、`%lld`、`%.1f`、`%.3f`）、
  表題・注記・列見出しは `reference/mfc/MFCApplication1.rc` の文字列。
- 出力は UTF-8（BOM なし）・LF。

## ビルド

PowerShell（または cmd）から実行する。Bash から `.cmd`／`.bat` を直接実行しない。

```powershell
tools\mfc_golden\build.ps1
```

- Visual Studio 2022 以降の「C++ によるデスクトップ開発」が必要。`vswhere.exe` は
  `C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe` をフルパスで使う。
- 生成物は `tools\mfc_golden\build\mfc_golden.exe`（版管理しない）。

## 正解 CSV を作り直す

```powershell
tools\mfc_golden\build\mfc_golden.exe LOG_CSV PROJECT_NAME OUT_DIR
```

例:

```powershell
tools\mfc_golden\build\mfc_golden.exe tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj.log.csv sample_vehicle_16ecu.canprj tests\data\sample_vehicle_16ecu\golden
tools\mfc_golden\build\mfc_golden.exe tests\data\as001\as001.canprj.log.csv as001.canprj tests\data\as001\golden
git diff --stat tests\data
```

- PROJECT_NAME は .canprj のファイル名（拡張子付き）。表題に入る。
- 作り直したら `git diff` で変化を確かめてからコミットする。
- 読み込みエラーなら標準エラーに MFC と同じメッセージ（`line N: ...`）を出し、終了コード 1。

## 目視確認（spec FR-040e）

正解 CSV のうち 1 画面分を、MFC 版の画面と目で見比べる。

1. MFC 版で `tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj` を開く（ログは同じフォルダの `.log.csv`）。
2. 「解析」メニューから画面を 1 つ（例: 送信待ち時間）開く。
3. 表の全セルを `tests\data\sample_vehicle_16ecu\golden\<kind>.csv` の 4 行目以降と見比べる。表題（1 行目）と注記（2 行目）も確かめる。
4. 結果を `tests\data\sample_vehicle_16ecu\golden\VERIFIED.md` に書く: 確認日、確認者、確認した画面、使った MFC 版のビルド、結果（一致／不一致と箇所）。
