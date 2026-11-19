@echo off
title DOI CONG KHOI CHAY - CHECK HOA DON DIEN TU
color 0B
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Doc cong hien tai tu file PORT.txt neu co
set "CURRENT_PORT=8000"
if exist "%~dp0PORT.txt" (
    set /p CURRENT_PORT=<"%~dp0PORT.txt"
)

cls
echo ================================================================
echo           TIEN ICH DOI CONG KHOI CHAY (CHANGE PORT)
echo ================================================================
echo.
echo Cong hien tai dang cau hinh: [ %CURRENT_PORT% ]
echo.
echo Hay chon cong ban muon su dung:
echo   [1] Cong 8000 (Mac dinh)
echo   [2] Cong 8080 (Khenh thuong dung)
echo   [3] Cong 8888
echo   [4] Cong 5000
echo   [5] Tu nhap so cong khac...
echo   [0] Giu nguyen cong %CURRENT_PORT% va Khoi chay ngay
echo.
set /p CHOOSE="Nhap lua chon cua ban (0-5) roi nhan Enter: "

if "%CHOOSE%"=="1" set "NEW_PORT=8000" & goto :SAVE_PORT
if "%CHOOSE%"=="2" set "NEW_PORT=8080" & goto :SAVE_PORT
if "%CHOOSE%"=="3" set "NEW_PORT=8888" & goto :SAVE_PORT
if "%CHOOSE%"=="4" set "NEW_PORT=5000" & goto :SAVE_PORT
if "%CHOOSE%"=="0" set "NEW_PORT=%CURRENT_PORT%" & goto :SAVE_PORT
if "%CHOOSE%"=="5" goto :CUSTOM_PORT

echo Lua chon khong hop le, giu nguyen cong %CURRENT_PORT%.
set "NEW_PORT=%CURRENT_PORT%"
goto :SAVE_PORT

:CUSTOM_PORT
echo.
set /p NEW_PORT="Nhap so cong moi (vi du 8001, 9000): "
if "%NEW_PORT%"=="" set "NEW_PORT=8080"

:SAVE_PORT
echo %NEW_PORT%> "%~dp0PORT.txt"
echo.
echo ================================================================
echo [OK] Da luu cau hinh cong moi: %NEW_PORT%
echo Dang khoi dong ung dung tai dia chi: http://127.0.0.1:%NEW_PORT% ...
echo ================================================================
echo.

:: Khoi dong qua start_app.py
if exist "%~dp0python_env\python.exe" (
    "%~dp0python_env\python.exe" "%~dp0start_app.py" %NEW_PORT%
) else (
    python "%~dp0start_app.py" %NEW_PORT%
)

pause
