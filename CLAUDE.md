# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

返答は日本語で。

## リポジトリの現状

このリポジトリ (`can_sim_log_analysis`) は、MFC 版 CAN バスシミュレータ（`C:\work\claude\can_simulator`）が出力した
フレームログを解析する Python ツールで、[GitHub Spec Kit](https://github.com/github/spec-kit) による
Spec-Driven Development (SDD) で開発している。

- 憲章: `.specify/memory/constitution.md`（v1.0.0）。最重要は原則 I「MFC 版との数値互換」: 表のセルが MFC 版と文字列一致すること。
- 機能 001（`specs/001-log-analysis-core-cli/`）: 画面なしの解析コア `src/can_log_analysis/` とコマンドライン `can-log-analysis`。
  受信完了時間・送信待ち時間・送信ジッタ・CAN バス負荷の 4 表を MFC 版と同じ書式の CSV で出す。画面（PySide6）は次の機能。
- `reference/mfc/` は MFC 版のソース（正解の資料）。**変更もコピーもしない**。`Doc/` は仕様書。
- `tools/mfc_golden/` は `reference/mfc/CanSim/LogAnalysis.cpp` をそのままビルドして正解 CSV（`tests/data/*/golden/`）を作る C++ プログラム。
  golden テストが合わないときは Python 側を直し、正解 CSV は直さない。
- `tests/data/` はバイト単位で比較するので `.gitattributes` で改行変換を止めている（正解 CSV は UTF-8・LF、シミュレータのログは CRLF）。

## コマンド（PowerShell から実行）

```powershell
py -3.12 -m venv .venv               # 初回だけ（Python 3.11 以上）
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest                               # unit + integration（golden を含む）
pytest tests/unit/test_jitter.py -k period   # 1 ファイル・一部だけ
pytest -m perf -s                    # 300 万行の性能テスト（時間とピークメモリ。1 分弱）
can-log-analysis tests\data\as001\as001.canprj -a txwait   # python -m can_log_analysis でも同じ
tools\mfc_golden\build.ps1           # 正解生成プログラムのビルド（Visual Studio 2022 以降が必要）
```

- Bash から `.cmd`／`.bat` を直接実行しない（`build.ps1` は PowerShell から）。
- 書くファイルは UTF-8（BOM なし）・LF。Windows PowerShell 5.1 で .ps1 に日本語を書くと読めないので、.ps1 は ASCII にする。

## Spec-Driven Development (Spec Kit) ワークフロー

このプロジェクトは **Claude Code integration (`script: ps` = PowerShell, sequential feature numbering)** で初期化されている
(`.specify/init-options.json`, `.specify/integration.json` 参照)。機能開発は基本的にコードを直接書き始めるのではなく、
以下の Claude Code スキル（`/speckit-xxx` スラッシュコマンド）を順番に使って進める。

| 順序 | コマンド | 役割 |
|---|---|---|
| 1 | `/speckit-constitution` | プロジェクトの原則（憲章）を作成・更新する |
| 2 | `/speckit-specify` | 自然言語の機能説明から `specs/<番号>-<短い名前>/spec.md` を生成する |
| 3 | `/speckit-clarify` | spec.md の曖昧な点を最大5つの質問で明確化し、spec に反映する |
| 4 | `/speckit-plan` | spec.md から実装計画 (`plan.md` 等の設計アーティファクト) を生成する |
| 5 | `/speckit-tasks` | plan から依存関係順の `tasks.md` を生成する |
| 6 | `/speckit-analyze` | spec.md / plan.md / tasks.md の整合性・品質を非破壊的にチェックする |
| 7 | `/speckit-checklist` | 要件に応じたカスタムチェックリストを生成する |
| 8 | `/speckit-implement` | tasks.md のタスクを順に実行し実装する |
| - | `/speckit-converge` | 実装済みコードと spec/plan/tasks を比較し、未実装分を tasks.md に追記する |
| - | `/speckit-taskstoissues` | tasks.md から GitHub Issue を生成する |

機能ごとに `specs/<NNN>-<short-name>/` ディレクトリが作られ、その中に `spec.md` → `plan.md` → `tasks.md` が積み上がっていく
(`.specify/scripts/powershell/create-new-feature.ps1` が番号付けとディレクトリ作成を行う)。番号は3桁の連番で、
`specs/` 内の既存ディレクトリから自動算出される。

これらのスキルの実体は `.claude/skills/speckit-*/SKILL.md` にあり、裏側では `.specify/scripts/powershell/*.ps1`
(`create-new-feature.ps1`, `setup-plan.ps1`, `setup-tasks.ps1`, `check-prerequisites.ps1`, `resolve-template.ps1`, `common.ps1`)
を呼び出し、`.specify/templates/*-template.md` をもとにドキュメントを生成する。テンプレートを変更すれば、以後生成される
spec/plan/tasks/checklist の構成が変わる。

## 開発を始める際の注意

- コードを書く前に、対応する `specs/<feature>/spec.md` と `plan.md` が存在するか確認し、Spec Kit ワークフローに沿っているか確認すること。存在しない場合は、ユーザーに `/speckit-specify` から始めるべきか確認する。
- `.gitignore` 冒頭のコメントにある通り、この `.gitignore` は「SDDプロジェクトのベース作成ツール」によって種別（MFC / Web など）を問わず常に同一内容が書き込まれる想定になっている。プロジェクト種別の判定・記録は `/speckit-constitution` が憲章ファイルに行うものであり、`.gitignore` 自体は種別に依存しない内容を保つ設計。ただしこのリポジトリでは、プロジェクトオーナーの判断（2026-10-22）で末尾に「# ---- Python ----」の節（`.venv/` など）を足している。
