@echo off
rem Starts the CAN log analysis tool (feature 002). Double-click, or drop a .canprj file on this file.
if not exist "%~dp0.venv\Scripts\can-log-analysis-gui.exe" (
  echo .venv not found. Create it as in specs/001-log-analysis-core-cli/quickstart.md and run: pip install -e ".[dev]"
  pause
  exit /b 1
)
start "" "%~dp0.venv\Scripts\can-log-analysis-gui.exe" %*
