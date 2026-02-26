@echo off
chcp 65001 >nul
title Restart Word2LaTeX Backend

echo ==========================================
echo  Dang dung backend cu...
echo ==========================================
REM Kill tat ca uvicorn/python process tren port 8000
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 "') do (
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo ==========================================
echo  Khoi dong backend moi (port 8000)...
echo ==========================================

set ROOT=%~dp0
if exist "%ROOT%.venv\Scripts\python.exe" (
    set PYTHON=%ROOT%.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

start "Word2LaTeX Backend (NEW)" cmd /k "cd /d %ROOT%backend && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir . --reload-dir %ROOT%src"

echo.
echo Backend da duoc restart!
echo Mo: http://localhost:8000/api/templates
echo.
timeout /t 3 /nobreak >nul
start "" "http://localhost:8000/health"
pause
