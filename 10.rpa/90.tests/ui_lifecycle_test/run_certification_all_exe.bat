@echo off
chcp 65001 > nul
title WF-ACT - 전체 앱 인증 (EXE 모드)

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  WF-ACT - 전체 앱 인증 (7개 앱, EXE 모드)                     ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo   시작 시간: %date% %time%
echo   모드: EXE (패키징된 실행 파일)
echo   레벨: FULL (146개 테스트 × 7개 앱 = 1,022개)
echo   앱: be, dp, ar, dc, cv, kfn, qr
echo   후보 폴더: D:\release\candidates
echo.
echo   주의: EXE 모드는 사용자 홈 폴더를 사용합니다.
echo         시작 시 ~/.wf_rpa 폴더가 초기화됩니다.
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

REM 전체 앱 인증 실행 (EXE 모드)
python run_certification.py --app be dp ar dc cv kfn qr -l full --exe --candidates-dir D:\release\candidates

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  인증 완료                                                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo   종료 시간: %date% %time%
echo.

pause
