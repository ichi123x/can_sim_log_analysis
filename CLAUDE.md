# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリの現状

このリポジトリ (`can_sim_log_analysis`) は、[GitHub Spec Kit](https://github.com/github/spec-kit) によって
Spec-Driven Development (SDD) 用にスキャフォールドされた直後の状態であり、**実装コードはまだ存在しない**。

- `PythonApplication1/` は Visual Studio Python プロジェクトの初期テンプレートで、`PythonApplication1.py` は空ファイル。実装が始まっても、このフォルダ/プロジェクト名は仮のものである可能性が高いので、機能名に合わせて置き換え・削除してよい。
- `.specify/memory/constitution.md` はまだプレースホルダー (`[PRINCIPLE_1_NAME]` 等が未置換) のテンプレートのまま。プロジェクトの原則が定まったら `/speckit-constitution` で確定させる。
- `specs/` ディレクトリはまだ存在しない（最初の機能を specify した時点で作成される）。
- ビルド/lint/テストコマンドは、実装が入るまでは存在しない。

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
- `.gitignore` 冒頭のコメントにある通り、この `.gitignore` は「SDDプロジェクトのベース作成ツール」によって種別（MFC / Web など）を問わず常に同一内容が書き込まれる想定になっている。プロジェクト種別の判定・記録は `/speckit-constitution` が憲章ファイルに行うものであり、`.gitignore` 自体は種別に依存しない内容を保つ設計。
