@echo off
chcp 65001 >nul 2>nul
title Trae Data Migration to D Drive

echo ============================================
echo   Trae Data Migration: C Drive -> D Drive
echo ============================================
echo.

:: Check Trae is not running
tasklist /FI "IMAGENAME eq Trae*" 2>nul | find /i "Trae" >nul
if %errorlevel% equ 0 (
    echo [ERROR] Trae is still running. Please close Trae first.
    pause
    exit /b 1
)

set "DEST=D:\TraeData"
set "ROAMING_SRC=%APPDATA%\Trae CN"
set "ROAMING_DST=%DEST%\Roaming"
set "TRAECN_SRC=%USERPROFILE%\.trae-cn"
set "TRAECN_DST=%DEST%\trae-cn"

echo [1/5] Creating destination directory: %DEST%
if not exist "%DEST%" mkdir "%DEST%"
echo     Done.
echo.

echo [2/5] Migrating AppData\Roaming\Trae CN
if exist "%ROAMING_SRC%" (
    if exist "%ROAMING_DST%" (
        echo     [SKIP] Destination already exists: %ROAMING_DST%
    ) else (
        echo     Moving data...
        robocopy "%ROAMING_SRC%" "%ROAMING_DST%" /E /MOVE /NFL /NDL /NJH /NJS /NC /NS >nul 2>nul
        if exist "%ROAMING_SRC%" rmdir /S /Q "%ROAMING_SRC%" 2>nul
        mklink /J "%ROAMING_SRC%" "%ROAMING_DST%"
        echo     Done.
    )
) else (
    echo     [SKIP] Source not found: %ROAMING_SRC%
)
echo.

echo [3/5] Migrating .trae-cn
if exist "%TRAECN_SRC%" (
    if exist "%TRAECN_DST%" (
        echo     [SKIP] Destination already exists: %TRAECN_DST%
    ) else (
        echo     Moving data...
        robocopy "%TRAECN_SRC%" "%TRAECN_DST%" /E /MOVE /NFL /NDL /NJH /NJS /NC /NS >nul 2>nul
        if exist "%TRAECN_SRC%" rmdir /S /Q "%TRAECN_SRC%" 2>nul
        mklink /J "%TRAECN_SRC%" "%TRAECN_DST%"
        echo     Done.
    )
) else (
    echo     [SKIP] Source not found: %TRAECN_SRC%
)
echo.

echo [4/5] Verifying symlinks
if exist "%ROAMING_SRC%" (
    echo     %ROAMING_SRC% -^> OK
) else (
    echo     [WARNING] %ROAMING_SRC% not found
)
if exist "%TRAECN_SRC%" (
    echo     %TRAECN_SRC% -^> OK
) else (
    echo     [WARNING] %TRAECN_SRC% not found
)
echo.

echo [5/5] Migration complete!
echo.
echo   Data now lives at: %DEST%
echo   Original locations are now symlinks pointing to D drive.
echo.
echo   You can now start Trae normally.
echo.
pause
