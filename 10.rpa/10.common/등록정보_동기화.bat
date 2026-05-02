@echo off
chcp 65001 >nul
REM ============================================================================
REM WorksFree 등록정보 동기화
REM ============================================================================
REM
REM 로컬에 저장된 등록 정보를 Google Sheets에 동기화합니다.
REM 네트워크 문제로 등록이 완료되지 않은 경우 사용하세요.
REM
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo WorksFree 등록정보 동기화
echo ========================================
echo.

REM 현재 폴더에서 EXE 파일 찾기
set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"

set "EXE_FILE="
for %%F in (*.exe) do (
    set "EXE_FILE=%%F"
    goto :found_exe
)

:found_exe
if not defined EXE_FILE (
    echo [오류] EXE 파일을 찾을 수 없습니다.
    echo 이 스크립트는 앱 실행 파일과 같은 폴더에 있어야 합니다.
    pause
    exit /b 1
)

echo 앱 실행 파일: %EXE_FILE%
echo.
echo 등록정보를 Google Sheets에 동기화합니다...
echo.

REM 앱을 --sync-registration 인자로 실행
"%CURRENT_DIR%%EXE_FILE%" --sync-registration

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================
    echo   동기화 완료!
    echo ========================================
) else (
    echo.
    echo [오류] 동기화 중 문제가 발생했습니다.
    echo 네트워크 연결을 확인하고 다시 시도하세요.
)

echo.
pause
