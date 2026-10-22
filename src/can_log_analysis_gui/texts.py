"""画面の文言（reference/mfc/MFCApplication1.rc からコピー。research.md R-8）。

%s・%d は MFC の書式指定のまま。メニューの & は Qt でもアクセスキーとして働く。
表の文言（表題、列見出し、注記）は機能 001 の can_log_analysis.formatting にある。
"""

# ---- IDR_MAINMENU ----
MENU_FILE = "ファイル(&F)"
MENU_LOAD_PROJECT = "プロジェクト読込み(&O)..."
MENU_EXIT = "終了(&X)"  # not in the MFC menu; 元仕様 AR-090
MENU_ANALYSIS = "解析(&A)"
MENU_TXWAIT = "送信待ち時間(&W)..."
MENU_LATENCY = "受信完了時間(&R)..."
MENU_JITTER = "送信ジッター(&J)..."
MENU_BUSLOAD = "CAN バス負荷(&B)..."

# ---- messages ----
IDS_LOG_NONE_NOPROJECT = ("プロジェクトファイルがないため、シミュレーションログはありません。\n"
                          "プロジェクトを保存または読み込んでから「開始」でシミュレーションを実行すると、ログが作られます。")
IDS_LOG_NONE = "プロジェクト「%s」のシミュレーションログはありません。\n「開始」でシミュレーションを実行すると、ログが作られます。"
IDS_LOG_READ_ERROR = "シミュレーションログを読み込めませんでした。\n%s"
IDS_LOAD_ERROR = "プロジェクトを読み込めませんでした。現在の内容は変更していません。\n\n%s"
IDS_PROJECT_FILTER = "CAN プロジェクト (*.canprj)|*.canprj|すべてのファイル (*.*)|*.*||"
IDS_PROJECT_PATH_LABEL = "プロジェクト名："

# ---- graph ----
IDS_ANALYSIS_NO_DATA = "データがありません"
IDS_LAT_AXIS_X = "時間 (µs)"
IDS_LAT_AXIS_Y = "件数"
IDS_BUS_AXIS_X = "時刻 (ms)"
IDS_BUS_AXIS_Y = "負荷 (%)"
IDS_JIT_AXIS_Y = "ずれ (µs)"
IDS_BUS_AVERAGE = "平均"

# ---- IDD_ANALYSIS_PROGRESS ----
PROGRESS_TITLE = "解析中"
PROGRESS_STOP = "中断"
IDS_ANALYZING_READ = "ログを読み込んでいます..."
IDS_ANALYZING_CALC = "集計しています..."
IDS_ANALYZING_CANCEL = "中断しています..."

# ---- this tool (no MFC counterpart; research.md R-8) ----
APP_TITLE = "CAN ログ解析"


def qt_project_filter() -> str:
    """MFC のファイル選択の絞り込み（"名前|パターン|...||"）を Qt の書式（"名前;;名前"）にする。"""
    parts = [p for p in IDS_PROJECT_FILTER.split("|") if p]
    return ";;".join(parts[i] for i in range(0, len(parts), 2))
