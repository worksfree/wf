@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================================
echo   BOM Exporter 빌드 + 테스트
echo ============================================================
echo.

cd /d "%~dp0"

:: 빌드 + 퀵 테스트 (기본)
powershell -ExecutionPolicy Bypass -File "build_and_test.ps1" -App be %*

pause
