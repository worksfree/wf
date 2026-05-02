@echo off
REM 빠른 실행 - 2초씩만 보여주고 종료

echo [DEMO] Quick Run - 2sec each
echo.

start "" ".\demo_b2e_new\b2e_new.0.8.exe"
timeout /t 2 > nul
taskkill /IM "b2e_new.0.8.exe" /F > nul 2>&1

start "" ".\demo_ConversionVerifier\conversion_verifier.exe"
timeout /t 2 > nul
taskkill /IM "conversion_verifier.exe" /F > nul 2>&1

start "" ".\demo_DemoDrawingClassifier\demo_drawing_classsifier.exe"
timeout /t 2 > nul
taskkill /IM "demo_drawing_classsifier.exe" /F > nul 2>&1

start "" ".\demo_filename_normalizer\filename_normalizer.exe"
timeout /t 2 > nul
taskkill /IM "filename_normalizer.exe" /F > nul 2>&1

start "" ".\demo_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
timeout /t 2 > nul
taskkill /IM "print_DWG_with_tkinter.exe" /F > nul 2>&1

echo Done!
pause