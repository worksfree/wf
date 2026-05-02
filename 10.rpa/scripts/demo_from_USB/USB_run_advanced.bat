@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title USB 포터블 앱 실행기

echo ========================================
echo     USB 포터블 앱 일괄 실행기 v2.0
echo ========================================
echo.
echo 실행 위치: %cd%
echo USB 드라이브: %~d0
echo.

REM 실행할 앱 목록 설정 (폴더명\실행파일명.exe 형식)
set "app[1]=시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
set "app[2]=시연_excel_automation\excel_automation.exe"
set "app[3]=시연_cad_converter\cad_converter.exe"
set "app[4]=시연_batch_processor\batch_processor.exe"
set "app[5]=시연_file_manager\file_manager.exe"

REM 앱 이름 설정 (표시용)
set "name[1]=DWG 프린터 (tkinter)"
set "name[2]=Excel 자동화"
set "name[3]=CAD 변환기"
set "name[4]=배치 프로세서"
set "name[5]=파일 관리자"

REM 실행 전 파일 체크
echo [파일 확인 중...]
echo ----------------------------------------
set "missing=0"
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [✓] !name[%%i]! - 정상
    ) else (
        echo [✗] !name[%%i]! - 파일 없음
        echo     경로: .\!app[%%i]!
        set "missing=1"
    )
)

if "!missing!"=="1" (
    echo.
    echo [경고] 일부 파일을 찾을 수 없습니다.
    echo 계속 진행하시겠습니까?
    set /p continue="진행하려면 Y 입력 (N=종료): "
    if /i not "!continue!"=="Y" goto :end
)

echo.
echo ========================================
echo 실행 옵션을 선택하세요:
echo ========================================
echo [1] 모든 앱 동시 실행
echo [2] 순차 실행 (안정적)
echo [3] 선택 실행
echo [4] 개별 선택 실행
echo [0] 종료
echo.
set /p choice="선택 (0-4): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :run_all
if "%choice%"=="2" goto :run_sequential
if "%choice%"=="3" goto :select_run
if "%choice%"=="4" goto :individual_run
goto :end

:run_all
echo.
echo [동시 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i] !name[%%i]! 실행 중...
        start "" ".\!app[%%i]!"
    )
)
goto :complete

:run_sequential
echo.
echo [순차 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i] !name[%%i]! 실행 중...
        start /wait "" ".\!app[%%i]!"
        echo     완료
    )
)
goto :complete

:select_run
echo.
echo [선택 실행 모드]
echo ----------------------------------------
echo 실행할 앱 번호를 입력하세요.
echo (예: 1,3,5 또는 1-3)
echo.
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo [%%i] !name[%%i]!
    )
)
echo.
set /p selection="선택: "

REM 간단한 선택 처리 (1,2,3 형식)
for %%a in (%selection%) do (
    set "num=%%a"
    if exist ".\!app[%%a]!" (
        echo [%%a] !name[%%a]! 실행 중...
        start "" ".\!app[%%a]!"
    )
)
goto :complete

:individual_run
echo.
echo [개별 선택 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist ".\!app[%%i]!" (
        echo.
        echo [%%i] !name[%%i]!를 실행하시겠습니까?
        set /p confirm="실행: Y / 건너뛰기: N : "
        if /i "!confirm!"=="Y" (
            start "" ".\!app[%%i]!"
            echo     → 실행됨
        ) else (
            echo     → 건너뜀
        )
    )
)
goto :complete

:complete
echo.
echo ========================================
echo          모든 작업 완료!
echo ========================================
echo.
echo USB를 안전하게 제거하려면 모든 앱을 종료하세요.
echo.
pause
goto :end

:end
endlocal
exit