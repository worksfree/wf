@echo off
chcp 65001 >nul 2>&1
echo.
echo ============================================================
echo   BOM Exporter 빌드 + 등록 테스트
echo ============================================================
echo.

cd /d "%~dp0"

:: 빌드 + 등록 테스트 (설정 리셋 포함)
powershell -ExecutionPolicy Bypass -File "build_and_test.ps1" -App be -Register -Reset

pause
