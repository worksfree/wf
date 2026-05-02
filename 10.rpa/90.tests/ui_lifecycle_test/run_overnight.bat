@echo off
chcp 65001 > nul
title WorksFree E2E Overnight Test

echo ============================================================
echo   WorksFree E2E Overnight Test
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

REM 필수 패키지 설치
echo [1/3] 필수 패키지 확인 중...
pip install pyautogui pygetwindow Pillow pyperclip --quiet

REM 테스트 데이터 폴더 생성
echo [2/3] 테스트 데이터 폴더 확인 중...
python setup_test_data.py

echo.
echo [3/3] E2E 테스트 시작...
echo.
echo ============================================================
echo   테스트가 실행되는 동안 마우스/키보드를 건드리지 마세요!
echo   비상 중지: 마우스를 화면 모서리로 빠르게 이동
echo ============================================================
echo.

REM 야간 모드로 전체 테스트 실행
python test_full_e2e.py --overnight --repeat 3

echo.
echo ============================================================
echo   테스트 완료
echo   종료 시간: %date% %time%
echo ============================================================
echo.
echo 결과 폴더: test_results\e2e\
echo.

pause
