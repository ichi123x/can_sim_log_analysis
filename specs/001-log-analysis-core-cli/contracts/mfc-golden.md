# Contract: 正解生成プログラム `tools/mfc_golden`

FR-040a〜e。MFC 版の解析コードそのものから、[table-csv.md](table-csv.md) 形式の正解 CSV を作る。

## 構成

```text
tools/mfc_golden/
├── README.md          # 目的、作り直す手順、目視確認の手順
├── pch.h              # 差し替え用（#pragma once だけ）。reference/mfc/pch.h（MFC 込み）の代わりに読ませる
├── golden_main.cpp    # 入口。LogAnalysis.h の関数を呼び、4 つの表 CSV を書く
├── build.ps1          # vswhere で VS を探し、vcvars64 の環境で cl を呼ぶ
└── build/             # 生成物（版管理しない）
```

- `reference/mfc/` 配下のファイルは一切変更・コピーしない。`reference/mfc/CanSim/LogAnalysis.cpp` をコンパイル対象に直接指定する（research R-1）。

## ビルド

```powershell
tools/mfc_golden/build.ps1        # → tools/mfc_golden/build/mfc_golden.exe
```

- PowerShell（または cmd）から実行する。Bash から `.cmd` を直接実行しない。
- コンパイラ: Visual Studio 2022 以降の MSVC x64。`vswhere.exe` は PATH にないので
  `"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"` をフルパスで使う
  （`-latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`）。
- 出力ファイルはバイナリモードで開き、UTF-8（BOM なし）・LF で書く（plan.md「正解生成プログラムのビルドと出力の取り決め」）。
- オプション: `/nologo /std:c++17 /EHsc /O2 /utf-8 /W4 /I tools/mfc_golden /I reference/mfc/CanSim`。
  浮動小数点は既定（`/fp:precise`）のまま。`/fp:fast` や `/arch:AVX2` は付けない（research R-4）。

## 実行

```text
mfc_golden.exe LOG_CSV PROJECT_NAME OUT_DIR
```

- LOG_CSV を `CanSim::ReadLogRecords` で読み、`AnalyzeLatency`、`AnalyzeBusLoad`、`AnalyzeTxWait`、`AnalyzeJitter` の結果から
  `OUT_DIR/latency.csv`、`busload.csv`、`txwait.csv`、`jitter.csv` を書く。
- 表題・注記・列見出しは `MFCApplication1.rc` の文言を UTF-8 の文字列リテラルとしてコピーする。
  セルは `AnalysisDlg.cpp` と同じ書式文字列（`ECU %02d`、`0x%03X`、`%lld`、`%.1f`、`%.3f`）で `snprintf` する。
  空欄にする条件（全体の行、jitter の count 0）も `AnalysisDlg.cpp` の `CreateContent` と同じ。
- 読み込みエラーなら標準エラーに MFC のメッセージを出し、終了コード 1。

## 正解 CSV の置き場所

```text
tests/data/<ログ名>/golden/{latency,busload,txwait,jitter}.csv
tests/data/<ログ名>/golden/VERIFIED.md   # 目視確認の記録（FR-040e）
```

- VERIFIED.md には、確認した日、確認した人、確認した画面（例: 送信待ち時間）、使った MFC 版のビルド、結果（一致／不一致と箇所）を書く。
- 正解 CSV を作り直したら、git の差分で変化を確認してからコミットする。
