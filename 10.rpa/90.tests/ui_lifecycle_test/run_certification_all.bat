@echo off
chcp 65001 > nul
title WF-ACT - 전체 앱 인증 (DEV 모드)

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  WF-ACT - 전체 앱 인증 (7개 앱, DEV 모드)                     ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo   시작 시간: %date% %time%
echo   모드: DEV (Python 소스 코드)
echo   레벨: FULL (146개 테스트 × 7개 앱 = 1,022개)
echo   앱: be, dp, ar, dc, cv, kfn, qr
echo.
echo ────────────────────────────────────────────────────────────────
echo.

cd /d "%~dp0"

REM Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되지 않았습니다.
    pause
    exit /b 1
)

REM 전체 앱 인증 실행
python run_certification.py --app be dp ar dc cv kfn qr -l full

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  인증 완료                                                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo   종료 시간: %date% %time%
echo.

pause
