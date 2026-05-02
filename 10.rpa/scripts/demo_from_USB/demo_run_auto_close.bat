@echo off
echo ========================================
echo     데모 앱 순차 실행 (자동 종료)
echo ========================================
echo.

REM 각 앱을 실행하고 3초 후 자동 종료
echo [1/5] b2e_new 실행 중...
start "" ".\demo_b2e_new\b2e_new.0.8.exe"
timeout /t 3 /nobreak > nul
taskkill /IM "b2e_new.0.8.exe" /F > nul 2>&1
echo      종료 완료

echo [2/5] conversion_verifier 실행 중...
start "" ".\demo_ConversionVerifier\conversion_verifier.exe"
timeout /t 3 /nobreak > nul
taskkill /IM "conversion_verifier.exe" /F > nul 2>&1
echo      종료 완료

echo [3/5] demo_drawing_classifier 실행 중...
start "" ".\demo_DemoDrawingClassifier\demo_drawing_classsifier.exe"
timeout /t 3 /nobreak > nul
taskkill /IM "demo_drawing_classsifier.exe" /F > nul 2>&1
echo      종료 완료

echo [4/5] filename_normalizer 실행 중...
start "" ".\demo_filename_normalizer\filename_normalizer.exe"
timeout /t 3 /nobreak > nul
taskkill /IM "filename_normalizer.exe" /F > nul 2>&1
echo      종료 완료

echo [5/5] print_DWG_with_tkinter 실행 중...
start "" ".\demo_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
timeout /t 3 /nobreak > nul
taskkill /IM "print_DWG_with_tkinter.exe" /F > nul 2>&1
echo      종료 완료

echo.
echo ========================================
echo     모든 데모 실행 완료!
echo ========================================
pause