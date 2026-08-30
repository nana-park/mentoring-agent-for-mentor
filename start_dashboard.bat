@echo off
chcp 65001 >nul
title Mentoring Agent Dashboard
echo ===================================================
echo Mentoring Agent Web Dashboard
echo ===================================================
echo.
echo Starting local web server...
echo Please do not close this window while using the dashboard.
echo To access the dashboard, open your browser and go to:
echo http://localhost:5000
echo.
cd /d "C:\Users\user\Documents\antigravity\mysterious-lavoisier\tools\mentoring"
"C:\Users\able2\AppData\Local\Programs\Python\Python312\python.exe" app.py
pause
