@echo off
setlocal enabledelayedexpansion
title 5개 폴더 EXE 일괄 실행기

echo ========================================
echo     5개 폴더 EXE 일괄 실행기 v1.0
echo ========================================
echo.

REM 실행할 exe 파일 경로 설정 (실제 경로로 수정 필요)
set "exe1=폴더1\실행파일명.exe"
set "exe2=폴더2\실행파일명.exe"
set "exe3=폴더3\실행파일명.exe"
set "exe4=폴더4\실행파일명.exe"
set "exe5=폴더5\실행파일명.exe"

REM 절대 경로 사용 예시 (필요시 주석 해제하여 사용)
REM set "exe1=C:\Program Files\App1\app1.exe"
REM set "exe2=D:\Tools\App2\app2.exe"
REM set "exe3=E:\Software\App3\app3.exe"
REM set "exe4=C:\Users\%USERNAME%\Desktop\App4\app4.exe"
REM set "exe5=D:\Projects\App5\app5.exe"

REM 실행 옵션 선택
echo 실행 옵션을 선택하세요:
echo [1] 모든 프로그램 동시 실행 (빠름)
echo [2] 순차적으로 실행 (안정적)
echo [3] 각 프로그램 실행 확인 후 다음 실행
echo [0] 종료
echo.
set /p choice="선택 (0-3): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :run_all
if "%choice%"=="2" goto :run_sequential
if "%choice%"=="3" goto :run_confirm
goto :end

:run_all
echo.
echo [동시 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist "!exe%%i!" (
        echo [%%i] !exe%%i! 실행 중...
        start "" "!exe%%i!"
    ) else (
        echo [%%i] 경고: !exe%%i! 파일을 찾을 수 없습니다.
    )
)
goto :complete

:run_sequential
echo.
echo [순차 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist "!exe%%i!" (
        echo [%%i] !exe%%i! 실행 중...
        start /wait "" "!exe%%i!"
        echo     완료
    ) else (
        echo [%%i] 경고: !exe%%i! 파일을 찾을 수 없습니다.
    )
)
goto :complete

:run_confirm
echo.
echo [확인 실행 모드]
echo ----------------------------------------
for /l %%i in (1,1,5) do (
    if exist "!exe%%i!" (
        echo.
        echo [%%i] 다음 파일을 실행하시겠습니까?
        echo     경로: !exe%%i!
        set /p confirm="실행하려면 Y 입력 (N=건너뛰기): "
        if /i "!confirm!"=="Y" (
            start "" "!exe%%i!"
            echo     실행됨
        ) else (
            echo     건너뛰었습니다.
        )
    ) else (
        echo [%%i] 경고: !exe%%i! 파일을 찾을 수 없습니다.
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
goto :end

:end
exit