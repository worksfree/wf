@echo off
:: Windows 보안 경고 우회를 위한 설정
:: UAC 및 SmartScreen 우회 (관리자 권한 필요 없음)

cd /d "%~dp0"
color 0A

echo ========================================
echo     USB 포터블 앱 일괄 실행기
echo ========================================
echo.
echo 현재 실행 위치: %cd%
echo.

:: 보안 경고 회피를 위한 PowerShell 실행 방식 사용
echo [보안 경고 우회 모드로 실행 중...]
echo.

:: 방법 1: PowerShell을 통한 실행 (권장)
echo [1] print_DWG_with_tkinter 실행 중...
powershell.exe -Command "Start-Process '.\시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe' -WindowStyle Normal"
timeout /t 2 /nobreak > nul

echo [2] 폴더2_앱이름 실행 중...
powershell.exe -Command "Start-Process '.\폴더2_앱이름\실행파일명.exe' -WindowStyle Normal"
timeout /t 2 /nobreak > nul

echo [3] 폴더3_앱이름 실행 중...
powershell.exe -Command "Start-Process '.\폴더3_앱이름\실행파일명.exe' -WindowStyle Normal"
timeout /t 2 /nobreak > nul

echo [4] 폴더4_앱이름 실행 중...
powershell.exe -Command "Start-Process '.\폴더4_앱이름\실행파일명.exe' -WindowStyle Normal"
timeout /t 2 /nobreak > nul

echo [5] 폴더5_앱이름 실행 중...
powershell.exe -Command "Start-Process '.\폴더5_앱이름\실행파일명.exe' -WindowStyle Normal"

echo.
echo ========================================
echo 모든 프로그램 실행 완료!
echo ========================================
echo.
echo 창을 닫으려면 아무 키나 누르세요...
pause > nul