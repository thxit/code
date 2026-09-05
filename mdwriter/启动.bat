@echo off
chcp 65001 >nul 2>nul
title Markdown Editor (Dev)
cd /d "%~dp0"

set "NODE_PATH=C:\Program Files\nodejs"
set "PATH=%NODE_PATH%;%PATH%"

where node >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%NODE_PATH%\node.exe" set "PATH=%NODE_PATH%;%PATH%"
)
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org/
    pause
    exit /b 1
)

if not exist "node_modules\" (
    echo [INFO] Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo [INFO] Starting Markdown Editor (Dev Mode)...
call "node_modules\.bin\electron.cmd" .
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Exit code: %errorlevel%
    pause
)
