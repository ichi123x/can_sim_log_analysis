"""解析コアの例外（research.md R-8）。"""


class CanLogAnalysisError(Exception):
    """このパッケージの例外の基底。"""


class ProjectNotFoundError(CanLogAnalysisError):
    """.canprj がない。"""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path


class ProjectReadError(CanLogAnalysisError):
    """.canprj を UTF-8 の INI として読めない。"""

    def __init__(self, path, reason):
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


class LogNotFoundError(CanLogAnalysisError):
    """ログ（<.canprj のパス>.log.csv）がない。"""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path


class LogReadError(CanLogAnalysisError):
    """ログを読めない。message は MFC ReadLogRecords と同じ英文（"line N: bad number" など）。"""

    def __init__(self, path, message):
        super().__init__(message)
        self.path = path
        self.message = message


class LogReadCancelled(CanLogAnalysisError):
    """progress が False を返して読み込みを中止した（MFC kLogReadCancelled）。"""
