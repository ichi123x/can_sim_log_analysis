"""性能テスト用: CLI の処理を 1 回実行し、このプロセスのピークメモリ（バイト）を標準出力に出す。

usage: python memory_probe.py PROJECT OUT_DIR
tracemalloc は使わない（遅くなり、ネイティブのメモリを数えないため。tasks.md T059）。
"""

import ctypes
import sys


def peak_bytes() -> int:
    if sys.platform == "win32":
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        get_process_memory_info = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        get_process_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        get_process_memory_info.restype = wintypes.BOOL
        process = ctypes.WinDLL("kernel32").GetCurrentProcess()
        if not get_process_memory_info(process, ctypes.byref(counters), counters.cb):
            raise OSError("GetProcessMemoryInfo failed")
        return counters.PeakWorkingSetSize
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024  # KiB on Linux


def main():
    from can_log_analysis.cli import main as cli_main

    project, out_dir = sys.argv[1], sys.argv[2]
    code = cli_main([project, "-o", out_dir, "-q"])
    if code != 0:
        raise SystemExit(code)
    print(peak_bytes())


if __name__ == "__main__":
    main()
