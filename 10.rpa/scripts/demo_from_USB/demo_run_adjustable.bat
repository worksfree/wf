@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   데모 앱 실행기 (조절 가능 버전)
echo ========================================
echo.

REM 실행 시간 설정 (초 단위)
set "display_time=5"

echo 각 앱을 %display_time%초간 실행 후 종료합니다.
echo.

REM 앱 목록과 실행 파일명 배열
set "app[1]=.\demo_b2e_new\b2e_new.0.8.exe"
set "exe[1]=b2e_new.0.8.exe"
set "name[1]=B2E New"

set "app[2]=.\demo_ConversionVerifier\conversion_verifier.exe"
set "exe[2]=conversion_verifier.exe"
set "name[2]=Conversion Verifier"

set "app[3]=.\demo_DemoDrawingClassifier\demo_drawing_classsifier.exe"
set "exe[3]=demo_drawing_classsifier.exe"
set "name[3]=Drawing Classifier"

set "app[4]=.\demo_filename_normalizer\filename_normalizer.exe"
set "exe[4]=filename_normalizer.exe"
set "name[4]=Filename Normalizer"

set "app[5]=.\demo_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
set "exe[5]=print_DWG_with_tkinter.exe"
set "name[5]=DWG Printer"

REM 실행 루프
for /l %%i in (1,1,5) do (
    echo [%%i/5] !name[%%i]! 실행 중...
    
    REM 앱 실행
    start "" "!app[%%i]!"
    
    REM 대기 시간 표시
    for /l %%j in (!display_time!,-1,1) do (
        <nul set /p "=   종료까지 %%j초... "
        timeout /t 1 /nobreak > nul
        <nul set /p "="
    )
    
    REM 프로세스 종료
    taskkill /IM "!exe[%%i]!" /F > nul 2>&1
    echo 종료됨
    echo.
)

echo ========================================
echo        모든 데모 시연 완료!
echo ========================================
echo.
pause