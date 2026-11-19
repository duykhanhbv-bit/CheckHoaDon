@echo off
title TRA CUU HOA DON DIEN TU TU DONG (RPA PLAYWRIGHT)
color 0A
cd /d "%~dp0"

:: Thiet lap moi truong UTF-8 va duong dan Playwright
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PLAYWRIGHT_BROWSERS_PATH=%~dp0pw-browsers

echo ================================================================
echo        TRA CUU HOA DON DIEN TU TU DONG - GDT (RPA PLAYWRIGHT)
echo ================================================================
echo.

:: [1/2] Kiem tra moi truong Python
if exist "%~dp0python_env\python.exe" (
    echo [OK] Phat hien goi Python tich hop san - Portable Python.
    set "PY_CMD=%~dp0python_env\python.exe"
    goto :START_APP
)

echo [INFO] Dang kiem tra Python he thong...
where python >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python tren may tinh nay!
    echo Vui long cai dat Python hoac giu nguyen thu muc python_env.
    pause
    exit /b 1
)

set "PY_CMD=python"
"%PY_CMD%" -c "import fastapi, playwright, ddddocr, pymupdf, pdfplumber, PIL" >nul 2>&1
if errorlevel 1 (
    echo [CANH BAO] Dang tu dong cai dat thu vien con thieu...
    "%PY_CMD%" -m pip install -r "%~dp0requirements.txt"
    "%PY_CMD%" -m playwright install chromium
)

:START_APP
echo [OK] Moi truong Python va thu vien da san sang.
echo.

:: [2/2] Khoi dong ung dung thong minh qua start_app.py (Tu dong bat cong trong, cho Server san sang roi moi mo trinh duyet)
"%PY_CMD%" "%~dp0start_app.py" %*

pause
