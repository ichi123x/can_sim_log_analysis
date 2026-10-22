# Quickstart: CANログ解析コアとコマンドライン

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

この機能ができたことを、端から端まで確かめる手順。コマンドはリポジトリのルートで PowerShell から実行する。

## 前提

- Python 3.11 以上（`py -3.12 --version` などで確認）。2026-10-22 時点の開発 PC は 3.9.13 だけなので、先に入れる
  （例 `winget install Python.Python.3.12`）。
- 正解 CSV を作り直すときだけ: Visual Studio 2022 以降の「C++ によるデスクトップ開発」。

## 1. 環境を作る

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 2. テストを流す

```powershell
pytest                 # unit + integration（golden を含む）
pytest -m perf         # 300 万行の性能テスト（数分かかる。SC-003）
```

期待: すべて成功。`tests/integration/test_golden.py` が sample_vehicle_16ecu の 4 表を正解 CSV と比べる（SC-002）。

## 3. AS-001 を手で確かめる（SC-001）

```powershell
can-log-analysis tests\data\as001\as001.canprj -a txwait -a latency
```

期待: [contracts/table-csv.md](contracts/table-csv.md) の「例」と同じ 2 つの表（txwait → latency の順。MFC の「解析」メニューの順）。
コンソールの文字化けは `chcp 65001` で直る（出力は常に UTF-8。research R-7）。

## 4. サンプルの 4 表をファイルに出して正解と比べる（SC-002）

```powershell
can-log-analysis tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj -o $env:TEMP\cla_out
foreach ($k in 'latency','busload','txwait','jitter') {
  if ((Get-FileHash "$env:TEMP\cla_out\$k.csv").Hash -ne (Get-FileHash "tests\data\sample_vehicle_16ecu\golden\$k.csv").Hash) { "DIFF $k" }
}
```

期待: 何も表示されない（4 ファイルともバイト一致）。

## 5. エラーを確かめる（SC-004）

```powershell
can-log-analysis tests\data\errors\bad_number.canprj ; $LASTEXITCODE
can-log-analysis no_such.canprj ; $LASTEXITCODE
```

期待: 標準エラーに `…bad_number.canprj.log.csv: line 5: bad number`、`プロジェクトファイルがありません: no_such.canprj`、
終了コードはどちらも 1。表は出ない。

## 6. 解析コアが画面ライブラリなしで動く（SC-005）

PySide6 などを入れていない上の環境で 2〜5 が通ること自体が確認になる。加えて `tests/unit/test_no_gui_import.py` が
`can_log_analysis` 配下の import を調べる。

## 7. 正解 CSV を作り直す（必要なときだけ）

```powershell
tools\mfc_golden\build.ps1
tools\mfc_golden\build\mfc_golden.exe tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj.log.csv sample_vehicle_16ecu.canprj tests\data\sample_vehicle_16ecu\golden
git diff --stat tests\data\sample_vehicle_16ecu\golden
```

詳細は [contracts/mfc-golden.md](contracts/mfc-golden.md)。

## 8. 目視確認（FR-040e、I.H）

MFC 版で `sample_vehicle_16ecu.canprj` を開き、「解析」メニューの画面を 1 つ（例: 送信待ち時間）開いて、
表の全セルを `tests\data\sample_vehicle_16ecu\golden\txwait.csv` と見比べる。結果を `golden\VERIFIED.md` に書く。
