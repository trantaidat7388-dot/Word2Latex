@echo off
chcp 65001 >nul
title Word2LaTeX - Starting...

echo ╔══════════════════════════════════════════╗
echo ║        Word2LaTeX - Khởi động            ║
echo ╚══════════════════════════════════════════╝
echo.

REM Kiểm tra thư mục
set ROOT=%~dp0
cd /d "%ROOT%"

REM ============================================
REM 1. Khởi động Backend (FastAPI + Uvicorn)
REM ============================================
echo [1/2] Đang khởi động Backend (port 8000)...

REM Kiểm tra .venv
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else if exist "backend\.venv\Scripts\python.exe" (
    set PYTHON=backend\.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

start "Word2LaTeX Backend" cmd /c "cd /d %ROOT%backend && %ROOT%%PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir . --reload-dir %ROOT%src"

REM Đợi backend khởi động
timeout /t 3 /nobreak >nul

REM ============================================
REM 2. Khởi động Frontend (Vite Dev Server)
REM ============================================
echo [2/2] Đang khởi động Frontend (port 5173)...

REM Kiểm tra node_modules
if not exist "frontend\node_modules" (
    echo     Đang cài đặt dependencies frontend...
    cd /d "%ROOT%frontend"
    call npm install
    cd /d "%ROOT%"
)

start "Word2LaTeX Frontend" cmd /c "cd /d %ROOT%frontend && npm run dev"

REM Đợi frontend khởi động
timeout /t 3 /nobreak >nul

REM ============================================
REM 3. Mở trình duyệt
REM ============================================
echo.
echo ╔══════════════════════════════════════════╗
echo ║  Backend:  http://localhost:8000         ║
echo ║  Frontend: http://localhost:5173         ║
echo ║  API Docs: http://localhost:8000/docs    ║
echo ╚══════════════════════════════════════════╝
echo.
echo Đang mở trình duyệt...
start "" "http://localhost:5173"

echo.
echo Nhấn phím bất kỳ để dừng cả hai server...
pause >nul

REM Dừng cả hai
echo Đang dừng servers...
taskkill /fi "WINDOWTITLE eq Word2LaTeX Backend" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Word2LaTeX Frontend" /f >nul 2>&1
echo Đã dừng. Tạm biệt!
