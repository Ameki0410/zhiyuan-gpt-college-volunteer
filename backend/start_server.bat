@echo off
chcp 65001 >nul
title Zhiyuan Backend
cd /d "%~dp0"

REM ===== Choose python interpreter =====
if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON=..\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo ========================================
echo   Zhiyuan Backend Starting...
echo   URL: http://127.0.0.1:8000
echo   Press Ctrl+C to stop
echo ========================================
echo.

REM Check if port 8000 is already occupied, and kill if needed (best-effort)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
    echo Found existing PID %%a on port 8000, trying to release it...
    taskkill /F /PID %%a >nul 2>nul
)

REM Wait a moment after killing process
timeout /t 1 /nobreak >nul 2>nul

%PYTHON% -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Service stopped. Press any key to close this window...
pause >nul
