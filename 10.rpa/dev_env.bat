@echo off
REM WorksFree 개발 환경 설정
REM Development Environment Setup for WorksFree

echo 🔧 WorksFree 개발 환경 설정 중...

REM 개발 모드 환경변수 설정
set WORKSFREE_DEV_MODE=true

REM Python 경로에 현재 디렉토리 추가
set PYTHONPATH=%CD%;%CD%\10.common;%PYTHONPATH%

echo ✅ 개발 환경 설정 완료!
echo.
echo 📝 현재 설정:
echo   - 개발 모드: %WORKSFREE_DEV_MODE%
echo   - Python 경로: %PYTHONPATH%
echo.
echo 🚀 사용법:
echo   독립 실행: python google_sheets_manager_dev.py
echo   모듈 테스트: python ui_register.py
echo   앱 실행: python ui_main.py
echo.

REM PowerShell 창 열기 (선택사항)
REM powershell -NoExit -Command "Write-Host '개발 환경이 준비되었습니다!' -ForegroundColor Green"

cmd /k