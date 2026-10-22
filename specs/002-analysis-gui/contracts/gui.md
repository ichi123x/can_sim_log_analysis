# Contract: 画面（ウィンドウ・メニュー・振る舞い）

MFC 版（`reference/mfc/AnalysisDlg.cpp`、`MFCApplication1Dlg.cpp` の RunAnalysis／OnAnalysis*／CloseResultWindows、`MFCApplication1.rc`）に合わせる。
寸法は 96 dpi 換算（Qt の論理ピクセル）。文言は .rc のまま（research R-8）。

## 起動（FR-060）

```text
can-log-analysis-gui [PROJECT]          # .venv\Scripts\can-log-analysis-gui.exe（コンソールなし）
python -m can_log_analysis_gui [PROJECT]
can_log_analysis_gui.bat [PROJECT]      # リポジトリ直下。ダブルクリック・.canprj のドラッグ＆ドロップ
```

- PROJECT があれば起動時に開く。開けなければ IDS_LOAD_ERROR を出し、未選択のまま起動する。
- バッチは `.venv\Scripts\can-log-analysis-gui.exe` がなければ「.venv がありません。quickstart の手順で環境を作ってください。」と出して `pause` する。

## メインウィンドウ（FR-001〜FR-006）

- タイトル: 「CAN ログ解析」、プロジェクトを開いたら「CAN ログ解析 - <ファイル名>」。初期サイズ 900×600、最小 520×400。
- メニュー（IDR_MAINMENU）:

```text
ファイル(&F)
  プロジェクト読込み(&O)...      Ctrl+O
  ─────
  終了(&X)
解析(&A)
  送信待ち時間(&W)...
  受信完了時間(&R)...
  送信ジッター(&J)...
  ─────
  CAN バス負荷(&B)...
```

- 「プロジェクト読込み」: ファイル選択（絞り込み IDS_PROJECT_FILTER、最初のフォルダは前に開いたプロジェクトのフォルダ）。選んだら開く。
- 本体（上から）:
  1. プロジェクト: 「プロジェクト名：」（IDS_PROJECT_PATH_LABEL）＋ファイル名、パス、ログ（「<ファイル名>（<大きさ> MB）」／「なし」）。未選択なら「プロジェクトが開かれていません」。
  2. ネットワーク: 通信速度（125 kbps／250 kbps／500 kbps／1 Mbps／<値> bps）、ECU 数、シミュレーション時間（<秒> s）。
  3. ECU の一覧（表）: 「ECU」（ECU %02d）、「名前」、「ラベル」、「受信フィルタ」（なければ「全受信」）、「受信処理遅延(ms)」、「電源投入(ms)」、「初期化時間(ms)」。
  4. 送信フレームの一覧（表）: 「送信 ECU」、「No.」、「フレーム名」、「ID」（0x%03X）、「DLC」、「初回オフセット(ms)」、「送信周期(ms)」。
  - ms の書式は MFC FormatMs（整数 ms なら整数、それ以外は小数 3 桁）。値がなければ空欄。表は表示のみ（編集不可）、数値の列は右寄せ。
  - 3 と 4 は上下に並べ、境目をドラッグで動かせる。

## 解析の実行（FR-010〜FR-015、MFC RunAnalysis）

1. 同じ種類の解析画面が開いていれば前面に出して終わり（解析しない）。
2. プロジェクト未選択 → IDS_LOG_NONE_NOPROJECT（情報）。ログがない → IDS_LOG_NONE（情報、ファイル名入り）。
3. ジョブ開始。待ちカーソル、メインウィンドウと解析画面は入力を受け付けない。
4. 0.5 秒以内に終われば 6 へ。過ぎたら「解析中」ウィンドウ（モーダル、メインウィンドウの中央）:
   - タイトル「解析中」、文言 1 行、進捗バー（0〜1000）、ボタン「中断」。
   - 50 ms ごとに更新: 読み込み中は IDS_ANALYZING_READ とバー done × 1000 / total（total 0 なら 0）、計算中は IDS_ANALYZING_CALC とバー 1000。
   - 「中断」・Esc・閉じるボタン → 中断を指示、文言を IDS_ANALYZING_CANCEL、ボタンを無効。Enter では何もしない。
   - ジョブが終わったら（どの結果でも）閉じる。
5. カーソルと入力を元に戻す。
6. 結果: done → 解析画面を開く。cancelled → 何もしない。read_error → IDS_LOG_READ_ERROR（警告、ログのパス）。
7. 解析中（3〜5 の間）は、メインウィンドウを閉じる操作を受け付けない（MFC と同じ）。それでも `closeEvent` が届いたら（サインアウトなど）、ジョブの中断を指示し、スレッドが止まるのを待って（`QThread.wait()`）から、解析画面をすべて閉じて終わる（spec FR-016）。

## 解析画面（FR-020〜FR-041）

| kind | タイトル（Table.title） | 初期サイズ | 配置 |
|---|---|---|---|
| txwait | 送信待ち時間 - <P> | 900×640 | 表・注記・グラフ |
| latency | 受信完了時間 - <P> | 900×640 | 表・注記・グラフ |
| jitter | 送信ジッター - <P> | 900×640 | 表・注記・グラフ |
| busload | CAN バス負荷 - <P> | 960×680 | 要約・グラフ・表 |

- 大きさ（初期・最小）はタイトルバーと枠を含めたウィンドウ全体（`frameGeometry()`。MFC の `MoveWindow`・`ptMinTrackSize` と同じ）。
  Qt の `resize()`・`setMinimumSize()` は中身（枠の内側）の大きさなので、表示して枠の幅がわかってから枠の分を差し引いて渡す。
  配置の式（LayoutListNoteGraph など）は MFC と同じく中身の大きさで計算する。メインウィンドウの 900×600 も枠を含めた大きさ。
- 最小 520×400。MFC `CAnalysisDlgBase::OnInitDialog` と同じく、枠を含めた矩形をメインウィンドウ（枠を含む）の中央に置き、
  モニタの作業領域からはみ出せば右 → 下 → 左 → 上の順にずらす。モードレス。Esc と閉じるボタンで閉じる。Enter では閉じない。
- 表: 列見出しと全セルは Table.columns・Table.rows をそのまま。1 行単位で 1 行だけ選べる。罫線あり。列幅（96 dpi 換算）と右寄せの開始列は MFC CreateList と同じ:
  - txwait・latency: 幅 90, 90, 80, 100, 100, 100, 100、3 列目から右寄せ。
  - jitter: 幅 90, 90, 90, 80, 100, 100, 110、3 列目から右寄せ。
  - busload: 幅 100, 140, 120、2 列目から右寄せ。
- 配置「表・注記・グラフ」（LayoutListNoteGraph）: 余白 8、注記の高さ 22、内側の高さ = 高さ − 2×8 − 22 − 8、表の高さ = 内側 × 2 / 5、表の下 4 空けて注記、その下 4 空けてグラフ（残り全部）。
- 配置「要約・グラフ・表」（CBusLoadDlg::LayoutContent）: 余白 8、要約の高さ 22、要約の下 4 空けてグラフ（残りの 3/5）、その下 6 空けて表（残り）。
- 開いたとき: 表・注記・グラフの画面は 1 行目を選び、そのグラフ。バス負荷は表を選んでもグラフは変わらない。
- グラフ（行を選んだとき）:
  - txwait・latency: 件数 0 → NoData、それ以外 → Bars（`make_histogram(row.stats.values)`、横軸 IDS_LAT_AXIS_X、縦軸 IDS_LAT_AXIS_Y）。
  - jitter: 件数 0 → NoData、それ以外 → Deviation（row.points、横軸 IDS_BUS_AXIS_X、縦軸 IDS_JIT_AXIS_Y）。
  - busload: 送信 0 → NoData、それ以外 → Line（section_pct、section_us、average_pct、横軸 IDS_BUS_AXIS_X、縦軸 IDS_BUS_AXIS_Y）。

## グラフの描き方（CAnalysisGraph::Draw）

- 背景を塗り、外枠を描く。NoData なら文言を中央に書いて終わり。
- プロット領域 = 外枠から左 70・上 32・右 20・下 46 を除く。幅 < 40 または高さ < 30 なら何も描かない。
- 範囲と縦の目盛り:
  - Deviation: x = 0〜最後の点の時刻（ms。0 なら 1）。y の目盛り = 点のずれの最小〜最大が同じなら [−1, 0, 1]、違えば ticks_covering(min, max, 5)（min・max は 0 を含めて取る）。
  - Bars: x = start〜start + width × 本数。y の目盛り = ticks_from_zero(最大件数（1 以上）, min(5, 最大件数))。
  - Line: x = 0〜section_us × 区間数 / 1000（ms）。y の目盛り = 0, 20, 40, 60, 80, 100。
- 横線（目盛りごと）と縦の数値（format_tick、右寄せ）。横の目盛り = nice_ticks(xLo, xHi, max(2, プロット幅 / 90))、数値は中央寄せ。
- データ:
  - Deviation: 0 の横線。点の数 ≤ プロット幅なら点（3 px 角）を線で結ぶ。多ければ min_max_per_column(points, 0, 最後の時刻, プロット幅) の各列に最小〜最大の縦線、列の中点どうしを線で結ぶ。
  - Bars: 件数 0 のビンは描かない。棒の幅が 2 px を超えるときは右に 1 px の隙間。
  - Line: max_per_column(section_pct, プロット幅) の各値を列の中央に置いて線で結ぶ（100 を超える値は 100）。平均を破線で引き、「平均 <Fixed1>%」をその上に右寄せで書く。
- 軸（左と下）。横軸名を下中央、縦軸名を左上に書く。
- 色・フォント（既定 Meiryo UI）・線の太さは MFC に近ければよい（FR-052）。

## プロジェクトを開いたとき（FR-005、FR-006）

- 開けたら: 開いている解析画面をすべて閉じ、メインウィンドウの表示とタイトルを新しいプロジェクトにする。
- 開けなければ: IDS_LOAD_ERROR（警告、理由入り）。表示も解析画面もそのまま。
