@echo off
echo ========================================
echo 5개 폴더의 EXE 파일 실행 시작
echo ========================================
echo.

REM 폴더1의 exe 실행
echo [1] 폴더1 실행 중...
start "" "폴더1\program.exe"
timeout /t 2 /nobreak > nul

REM 폴더2의 exe 실행
echo [2] 폴더2 실행 중...
start "" "폴더2\program.exe"
timeout /t 2 /nobreak > nul

REM 폴더3의 exe 실행
echo [3] 폴더3 실행 중...
start "" "폴더3\program.exe"
timeout /t 2 /nobreak > nul

REM 폴더4의 exe 실행
echo [4] 폴더4 실행 중...
start "" "폴더4\program.exe"
timeout /t 2 /nobreak > nul

REM 폴더5의 exe 실행
echo [5] 폴더5 실행 중...
start "" "폴더5\program.exe"

echo.
echo ========================================
echo 모든 프로그램 실행 완료!
echo ========================================
echo.
echo 창을 닫으려면 아무 키나 누르세요...
pause > nul