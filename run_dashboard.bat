@echo off
setlocal
echo ===================================================
echo   Codebase Intelligence - Web Dashboard Launcher
echo ===================================================

:: Check virtual environment
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Target repository (default to demo_project if not provided)
set "TARGET_REPO=%~1"
if "%TARGET_REPO%"=="" (
    set "TARGET_REPO=demo_project"
)

echo [*] Indexing repository: %TARGET_REPO%
"%PYTHON_EXE%" "%~dp0cli.py" index "%TARGET_REPO%"

echo.
echo [*] Starting web dashboard at http://127.0.0.1:5050 ...
"%PYTHON_EXE%" "%~dp0demo_dashboard\server.py"

endlocal
