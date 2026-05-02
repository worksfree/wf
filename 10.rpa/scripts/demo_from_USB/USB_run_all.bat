@echo off
cd /d "%~dp0"
echo ========================================
echo     USB 포터블 앱 일괄 실행기
echo ========================================
echo.
echo 현재 실행 위치: %cd%
echo.

REM 5개 앱 실행
echo [1] print_DWG_with_tkinter 실행 중...
start "" ".\시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
timeout /t 2 /nobreak > nul

echo [2] 폴더2_앱이름 실행 중...
start "" ".\폴더2_앱이름\실행파일명.exe"
timeout /t 2 /nobreak > nul

echo [3] 폴더3_앱이름 실행 중...
start "" ".\폴더3_앱이름\실행파일명.exe"
timeout /t 2 /nobreak > nul

echo [4] 폴더4_앱이름 실행 중...
start "" ".\폴더4_앱이름\실행파일명.exe"
timeout /t 2 /nobreak > nul

echo [5] 폴더5_앱이름 실행 중...
start "" ".\폴더5_앱이름\실행파일명.exe"

echo.
echo ========================================
echo 모든 프로그램 실행 완료!
echo ========================================
echo.
echo 창을 닫으려면 아무 키나 누르세요...
pause > nul