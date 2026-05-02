@echo off
chcp 65001 > nul
echo.
echo ┌─────────────────────────────────────────────┐
echo │  Chrome 원격 디버깅 모드 재시작              │
echo │  세션(로그인 상태)은 그대로 유지됩니다       │
echo └─────────────────────────────────────────────┘
echo.

:: Chrome 프로세스 종료
echo [1/3] Chrome 종료 중...
taskkill /f /im chrome.exe 2>nul
taskkill /f /im msedge.exe 2>nul
timeout /t 2 /nobreak >nul

:: Chrome 실행 파일 경로 탐색
set CHROME=""
if exist "%PROGRAMFILES%\Google\Chrome\Application\chrome.exe" (
    set CHROME="%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"
) else if exist "%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe" (
    set CHROME="%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME%=="" (
    echo [오류] Chrome을 찾을 수 없습니다.
    pause
    exit /b 1
)

:: 원격 디버깅 포트(9222)로 Chrome 재시작
echo [2/3] Chrome 재시작 (디버깅 포트: 9222)...
start "" %CHROME% ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" ^
    --profile-directory=Default

timeout /t 3 /nobreak >nul

echo [3/3] 완료!
echo.
echo  이제 스크립트를 실행하세요:
echo  python download_materials.py --phase 1
echo.
pause
