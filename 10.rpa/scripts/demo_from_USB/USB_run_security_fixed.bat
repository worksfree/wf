@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title USB 앱 실행기 - 보안 경고 해결 버전

echo ========================================
echo   USB 포터블 앱 실행기 (보안 우회)
echo ========================================
echo.

:: 실행할 앱 목록
set "app[1]=시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
set "app[2]=시연_excel_automation\excel_automation.exe"
set "app[3]=시연_cad_converter\cad_converter.exe"
set "app[4]=시연_batch_processor\batch_processor.exe"
set "app[5]=시연_file_manager\file_manager.exe"

set "name[1]=DWG 프린터"
set "name[2]=Excel 자동화"
set "name[3]=CAD 변환기"
set "name[4]=배치 프로세서"
set "name[5]=파일 관리자"

echo 실행 방법을 선택하세요:
echo ========================================
echo [1] PowerShell 모드 (보안 경고 최소화)
echo [2] CMD 직접 실행 (기본)
echo [3] 파일별 수동 확인 실행
echo ========================================
echo.
set /p mode="선택 (1-3): "

if "%mode%"=="1" goto :powershell_mode
if "%mode%"=="2" goto :cmd_mode
if "%mode%"=="3" goto :manual_mode
goto :powershell_mode

:powershell_mode
echo.
echo [PowerShell 모드 실행]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i/5] !name[%%i]! 실행 중...
        powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command "& {Start-Process '.\!app[%%i]!' -WindowStyle Normal}" 2>nul
        timeout /t 1 /nobreak > nul
    ) else (
        echo [%%i/5] !name[%%i]! - 파일 없음
    )
)
goto :complete

:cmd_mode
echo.
echo [CMD 직접 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i/5] !name[%%i]! 실행 중...
        start "" /B ".\!app[%%i]!"
        timeout /t 1 /nobreak > nul
    ) else (
        echo [%%i/5] !name[%%i]! - 파일 없음
    )
)
goto :complete

:manual_mode
echo.
echo [수동 확인 모드]
echo ----------------------------------------
echo 보안 경고가 뜨면 [확인]을 클릭하세요.
echo.
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i/5] !name[%%i]!
        echo 실행하려면 아무 키나 누르세요...
        pause > nul
        start "" ".\!app[%%i]!"
        echo 실행됨
        echo.
    ) else (
        echo [%%i/5] !name[%%i]! - 파일 없음
        echo.
    )
)
goto :complete

:complete
echo.
echo ========================================
echo          모든 작업 완료!
echo ========================================
echo.
pause
exit