// golden_main.cpp
// Writes the four analysis tables of a frame log as table CSV files
// (specs/001-log-analysis-core-cli/contracts/table-csv.md), computed by the
// unchanged MFC code reference/mfc/CanSim/LogAnalysis.cpp. The cells use the
// same format strings as reference/mfc/AnalysisDlg.cpp, and the texts are the
// strings of reference/mfc/MFCApplication1.rc, so the files are what the MFC
// analysis windows show.
//
// usage: mfc_golden.exe LOG_CSV PROJECT_NAME OUT_DIR
//
// Source file encoding: UTF-8; build with /utf-8 so the literals stay UTF-8.

#include "LogAnalysis.h"

#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    // ---- MFCApplication1.rc (string table) ----
    const char* const kLatTitle = "受信完了時間 - %s";
    const char* const kLatColumns = "送信 ECU|受信 ECU|件数|最小 (µs)|平均 (µs)|最大 (µs)|95% (µs)";
    const char* const kLatAll = "全体";
    const char* const kLatNote = "送信要求 → 受信完了の時間（再送は届いた 1 回を 1 件）。破棄（OVERWRITE）%d 件は含みません。";
    const char* const kBusTitle = "CAN バス負荷 - %s";
    const char* const kBusSummary = "平均負荷 %s%%　最大負荷 %s%%（%s〜%s ms）　範囲 0〜%s ms（10 ms ごと）";
    const char* const kBusColumns = "ECU|送信フレーム数|使用率 (%)";
    const char* const kWaitTitle = "送信待ち時間 - %s";
    const char* const kWaitColumns = "CAN ID|送信 ECU|件数|最小 (µs)|平均 (µs)|最大 (µs)|95% (µs)";
    const char* const kWaitNote = "送信要求 → 送信開始の時間（送信 1 回を 1 件。再送は送れた 1 回）。破棄（OVERWRITE）%d 件は含みません。";
    const char* const kJitTitle = "送信ジッター - %s";
    const char* const kJitColumns = "CAN ID|送信 ECU|周期 (ms)|件数|最小 (µs)|最大 (µs)|標準偏差 (µs)";
    const char* const kJitNote = "連続する送信開始の間隔 − 送信要求の間隔（正は遅れ、負は早まり）。標準偏差は件数で割った値です。";

    template <typename... Args>
    std::string Format(const char* format, Args... args)
    {
        const int n = std::snprintf(nullptr, 0, format, args...);
        if (n < 0)
            throw std::runtime_error("snprintf failed");
        std::vector<char> buffer(static_cast<std::size_t>(n) + 1);
        std::snprintf(buffer.data(), buffer.size(), format, args...);
        return std::string(buffer.data(), static_cast<std::size_t>(n));
    }

    // ---- AnalysisDlg.cpp ----
    std::string Fixed1(double value) { return Format("%.1f", value); }
    std::string EcuName(int node) { return Format("ECU %02d", node); }
    std::string CanIdText(unsigned id) { return Format("0x%03X", id); }
    std::string Integer(long long value) { return Format("%lld", value); }

    std::string PeriodText(long long periodUs)
    {
        if (periodUs % 1000 == 0)
            return Format("%lld", periodUs / 1000);
        return Format("%.3f", static_cast<double>(periodUs) / 1000.0);
    }

    struct Table
    {
        std::string Title;
        std::string Note;
        std::vector<std::string> Columns;
        std::vector<std::vector<std::string>> Rows;
    };

    std::vector<std::string> SplitColumns(const char* columns)
    {
        std::vector<std::string> out;
        std::string cell;
        for (const char* p = columns; *p != '\0'; ++p)
        {
            if (*p == '|')
            {
                out.push_back(cell);
                cell.clear();
            }
            else
                cell += *p;
        }
        out.push_back(cell);
        return out;
    }

    // CLatencyDlg::CreateContent
    Table LatencyTable(const CanSim::LatencyAnalysis& a, const std::string& project)
    {
        Table t;
        t.Title = Format(kLatTitle, project.c_str());
        t.Note = Format(kLatNote, static_cast<int>(a.OverwriteCount));
        t.Columns = SplitColumns(kLatColumns);
        for (std::size_t i = 0; i < a.Rows.size(); ++i)
        {
            const CanSim::LatencyRow& row = a.Rows[i];
            t.Rows.push_back({ i == 0 ? std::string(kLatAll) : EcuName(row.TxNode), i == 0 ? std::string() : EcuName(row.RxNode),
                Integer(row.Count), Integer(row.MinUs), Fixed1(row.MeanUs), Integer(row.MaxUs), Integer(row.P95Us) });
        }
        return t;
    }

    // CBusLoadDlg::CreateContent
    Table BusLoadTable(const CanSim::BusLoadAnalysis& a, const std::string& project)
    {
        Table t;
        t.Title = Format(kBusTitle, project.c_str());
        const long long sectionMs = a.SectionUs / 1000;
        const std::string from = Integer(static_cast<long long>(a.MaxSection) * sectionMs);
        const std::string to = Integer((static_cast<long long>(a.MaxSection) + 1) * sectionMs);
        const std::string range = Integer(a.RangeUs / 1000);
        t.Note = Format(kBusSummary, Fixed1(a.AveragePct).c_str(), Fixed1(a.MaxPct).c_str(), from.c_str(), to.c_str(), range.c_str());
        t.Columns = SplitColumns(kBusColumns);
        for (const CanSim::EcuBusUsage& e : a.Ecus)
            t.Rows.push_back({ EcuName(e.Node), Integer(e.FrameCount), Fixed1(e.UsagePct) });
        return t;
    }

    // CTxWaitDlg::CreateContent
    Table TxWaitTable(const CanSim::TxWaitAnalysis& a, const std::string& project)
    {
        Table t;
        t.Title = Format(kWaitTitle, project.c_str());
        t.Note = Format(kWaitNote, static_cast<int>(a.OverwriteCount));
        t.Columns = SplitColumns(kWaitColumns);
        for (const CanSim::TxWaitRow& row : a.Rows)
        {
            t.Rows.push_back({ row.All ? std::string(kLatAll) : CanIdText(row.CanId), row.All ? std::string() : EcuName(row.TxNode),
                Integer(row.Count), Integer(row.MinUs), Fixed1(row.MeanUs), Integer(row.MaxUs), Integer(row.P95Us) });
        }
        return t;
    }

    // CJitterDlg::CreateContent
    Table JitterTable(const CanSim::JitterAnalysis& a, const std::string& project)
    {
        Table t;
        t.Title = Format(kJitTitle, project.c_str());
        t.Note = kJitNote;
        t.Columns = SplitColumns(kJitColumns);
        for (const CanSim::JitterRow& row : a.Rows)
        {
            if (row.Count == 0) // sent once: no period and no jitter
            {
                t.Rows.push_back({ CanIdText(row.CanId), EcuName(row.TxNode), std::string(), Integer(row.Count),
                    std::string(), std::string(), std::string() });
                continue;
            }
            t.Rows.push_back({ CanIdText(row.CanId), EcuName(row.TxNode), PeriodText(row.PeriodUs), Integer(row.Count),
                Integer(row.MinUs), Integer(row.MaxUs), Fixed1(row.StdDevUs) });
        }
        return t;
    }

    void CheckCell(const std::string& cell)
    {
        if (cell.find_first_of(",\"\r\n") != std::string::npos)
            throw std::runtime_error("a cell contains a comma, a quote or a line break: " + cell);
    }

    void WriteLine(std::ofstream& out, const std::vector<std::string>& cells)
    {
        for (std::size_t i = 0; i < cells.size(); ++i)
        {
            CheckCell(cells[i]);
            if (i > 0)
                out << ',';
            out << cells[i];
        }
        out << '\n';
    }

    // UTF-8 without BOM, LF; binary mode so that '\n' is not turned into CR LF.
    void WriteTable(const std::filesystem::path& path, const Table& t)
    {
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out)
            throw std::runtime_error("cannot write " + path.u8string());
        WriteLine(out, { t.Title });
        WriteLine(out, { t.Note });
        WriteLine(out, t.Columns);
        for (const std::vector<std::string>& row : t.Rows)
            WriteLine(out, row);
        if (!out)
            throw std::runtime_error("cannot write " + path.u8string());
    }
}

int wmain(int argc, wchar_t** argv)
{
    if (argc != 4)
    {
        std::cerr << "usage: mfc_golden.exe LOG_CSV PROJECT_NAME OUT_DIR\n";
        return 2;
    }
    try
    {
        const std::wstring logPath = argv[1];
        const std::string project = std::filesystem::path(argv[2]).u8string();
        const std::filesystem::path outDir = argv[3];

        std::vector<CanSim::LogRecord> records;
        std::string error;
        if (!CanSim::ReadLogRecords(logPath, records, error))
        {
            std::cerr << error << '\n';
            return 1;
        }

        std::filesystem::create_directories(outDir);
        WriteTable(outDir / "latency.csv", LatencyTable(CanSim::AnalyzeLatency(records), project));
        WriteTable(outDir / "busload.csv", BusLoadTable(CanSim::AnalyzeBusLoad(records), project));
        WriteTable(outDir / "txwait.csv", TxWaitTable(CanSim::AnalyzeTxWait(records), project));
        WriteTable(outDir / "jitter.csv", JitterTable(CanSim::AnalyzeJitter(records), project));
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
