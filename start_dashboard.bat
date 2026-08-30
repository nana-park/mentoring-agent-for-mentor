@echo off
chcp 65001 >nul
setlocal
title Mentoring Agent Dashboard
cd /d "%~dp0"
echo Open http://localhost:5000 after the server starts.
echo Keep this window open while using the dashboard.
if defined MENTORING_PYTHON (
    "%MENTORING_PYTHON%" app.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" app.py
) else (
    python app.py
)
pause
