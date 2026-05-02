@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================================
echo   BOM Exporter 테스트만 (최신 빌드 사용)
echo ============================================================
echo.

cd /d "%~dp0"

:: 테스트만 (빌드 스킵)
powershell -ExecutionPolicy Bypass -File "build_and_test.ps1" -App be -TestOnly -Register -Reset

pause
