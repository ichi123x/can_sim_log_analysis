# Quickstart: CANログ解析ツールの画面

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

この機能ができたことを確かめる手順。コマンドはリポジトリのルートで PowerShell から実行する。

## 前提

- 機能 001 の環境（`.venv`、Python 3.12）。[001 quickstart](../001-log-analysis-core-cli/quickstart.md) の 1。
- 画面のライブラリを入れる:

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"      # dev に PySide6 と pytest-qt が入る
```

## 1. テスト

```powershell
pytest                       # 機能 001 と 002 の unit・integration（画面は offscreen で動く）
pytest -m perf -s            # 300 万行: CLI の時間・メモリ（001）と、画面の応答性・中断（002）
```

期待: すべて成功。機能 001 の golden テストも引き続き通る。

## 2. 起動して sample を見る（US1〜US3）

```powershell
can-log-analysis-gui tests\data\sample_vehicle_16ecu\sample_vehicle_16ecu.canprj
```

またはエクスプローラーでリポジトリの `can_log_analysis_gui.bat` をダブルクリック（.canprj をこのバッチにドラッグ＆ドロップしてもよい）。

期待:
- メインウィンドウのタイトル「CAN ログ解析 - sample_vehicle_16ecu.canprj」。通信速度 500 kbps、ECU 16 台、送信フレーム 31 個が表に出る。
- 「解析 > 送信待ち時間」: 表 32 行が `tests\data\sample_vehicle_16ecu\golden\txwait.csv` と同じ。1 行目（全体）が選ばれ、ヒストグラムが出る。0x1A0 を選ぶと 0 µs の棒 1 本（50 件）。
- 「解析 > 受信完了時間」「送信ジッター」「CAN バス負荷」も、表・注記（要約）が golden の CSV と同じ。ジッターは時系列、バス負荷は折れ線と平均の破線。
- 同じ解析をもう一度選ぶと、新しい画面は開かず前面に出る。Esc で閉じ、Enter では閉じない。

## 3. MFC 版と見比べる（SC-002）

MFC 版（`C:\work\claude\can_simulator`）で同じプロジェクトを開き、少なくとも 2 画面（例: 送信ジッター、CAN バス負荷）で、
表の全セル・タイトル・メニュー・グラフの軸の範囲と目盛りの数値を見比べる。結果を `specs\002-analysis-gui\VERIFIED.md` に書く。

## 4. 大きなログ（US4、SC-003、SC-004）

`pytest -m perf` が作る 300 万行のログ（または同じ方法で作ったもの）を開いて解析を選ぶ。
期待: 0.5 秒後に「解析中」ウィンドウ。読み込み中に「中断」→ 2 秒以内に閉じ、解析画面は出ない。最後まで待てば 1 分以内に解析画面が開く。

## 5. メッセージ（US5）

- 起動直後に「解析 > 送信待ち時間」→ IDS_LOG_NONE_NOPROJECT。
- `tests\data\errors\no_log.canprj` を開いて解析 → IDS_LOG_NONE。
- `tests\data\errors\bad_number.canprj` を開いて解析 → 「シミュレーションログを読み込めませんでした。」とログのパス。
- `tests\data\errors\bad_project.canprj` を開く → 「プロジェクトを読み込めませんでした。現在の内容は変更していません。」と理由。前のプロジェクトのまま。
