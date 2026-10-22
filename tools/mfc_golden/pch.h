// pch.h (tools/mfc_golden)
// Stand-in for reference/mfc/pch.h, which pulls in MFC through framework.h.
// reference/mfc/CanSim/LogAnalysis.cpp starts with #include "pch.h"; with
// /I tools/mfc_golden this empty header is found instead, so the MFC analysis
// code builds unchanged without MFC (research.md R-1).

#pragma once
