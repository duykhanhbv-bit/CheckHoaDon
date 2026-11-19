@echo off
title DONG GOI VA NANG PHIEN BAN - CHECKHOADON
color 0A
cd /d "%~dp0"

echo ================================================================
echo    TIEN ICH DONG GOI VA TU DONG NANG PHIEN BAN - CHECKHOADON
echo ================================================================
echo.

if exist "%~dp0python_env\python.exe" (
    set "PY_CMD=%~dp0python_env\python.exe"
) else (
    set "PY_CMD=python"
)

"%PY_CMD%" "%~dp0package.py" %*

echo.
echo ================================================================
echo Nhan phim bat ky de dong cua so...
pause >nul
