@echo off
chcp 65001 > nul
title WF-ACT - App Certification Toolkit

echo ============================================================
echo   WF-ACT - WF-RPA App Certification Toolkit
echo   시작 시간: %date% %time%
echo ============================================================
echo.

cd /d "%~dp0"

REM Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되지 않았습니다.
    pause
    exit /b 1
)

REM 인증 실행
python run_certification.py %*

echo.
echo ============================================================
echo   인증 완료
echo   종료 시간: %date% %time%
echo ============================================================
echo.

pause
