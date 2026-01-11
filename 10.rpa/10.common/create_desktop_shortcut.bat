@echo off
chcp 65001 >nul
REM ============================================================================
REM WorksFree 앱 바탕화면 바로가기 생성 스크립트
REM ============================================================================
REM 
REM 이 스크립트는 현재 폴더의 exe 파일을 찾아서 바탕화면 바로가기를 생성합니다.
REM 버전 정보는 .wf_rpa/<앱이름>/settings.json에서 자동으로 읽어옵니다.
REM
REM 모든 WorksFree 앱에서 공통으로 사용 가능합니다.
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo WorksFree 바탕화면 바로가기 생성
echo ========================================
echo.

REM 현재 스크립트가 실행되는 폴더 (portable 폴더)
set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"

REM EXE 파일 찾기 (첫 번째 .exe 파일 사용)
set "EXE_FILE="
for %%F in (*.exe) do (
    set "EXE_FILE=%%F"
    goto :found_exe
)

:found_exe
if not defined EXE_FILE (
    echo [오류] EXE 파일을 찾을 수 없습니다.
    echo 이 스크립트는 앱 실행 파일과 같은 폴더에 있어야 합니다.
    pause
    exit /b 1
)

echo [1/4] EXE 파일 발견: %EXE_FILE%

REM EXE 파일 전체 경로
set "EXE_PATH=%CURRENT_DIR%%EXE_FILE%"

REM 앱 이름 추출 (확장자 제거)
set "APP_NAME=%EXE_FILE:~0,-4%"

REM [2/5] policy.json에서 display_name 읽기
set "POLICY_JSON=%CURRENT_DIR%_internal\.wf_rpa\%APP_NAME%\policy.json"
if exist "%POLICY_JSON%" (
    echo [2/5] policy.json 발견
    for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "$json = Get-Content '%POLICY_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.identity.display_name"`) do set "APP_DISPLAY_NAME=%%D"
) else (
    echo [경고] policy.json을 찾을 수 없습니다: %POLICY_JSON%
)

REM display_name이 없으면 exe 파일명 사용
if not defined APP_DISPLAY_NAME (
    echo [경고] display_name을 읽을 수 없습니다. exe 파일명을 사용합니다.
    set "APP_DISPLAY_NAME=%APP_NAME%"
)

REM settings.json 경로 찾기 (_internal\.wf_rpa\<앱이름>\settings.json)
set "SETTINGS_JSON=%CURRENT_DIR%_internal\.wf_rpa\%APP_NAME%\settings.json"

if not exist "%SETTINGS_JSON%" (
    echo [경고] settings.json을 찾을 수 없습니다: %SETTINGS_JSON%
    echo 기본 정보로 바로가기를 생성합니다.
    set "VERSION=unknown"
    set "BUILD_TIME=unknown"
    goto :create_shortcut
)

echo [3/5] settings.json 발견

REM PowerShell로 JSON 파싱하여 버전 정보 추출
for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$json = Get-Content '%SETTINGS_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.runtime_config.full_version"`) do set "VERSION=%%V"
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "$json = Get-Content '%SETTINGS_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.runtime_config.build_count"`) do set "BUILD_TIME=%%T"

if not defined VERSION set "VERSION=unknown"
if not defined BUILD_TIME set "BUILD_TIME=unknown"
if not defined APP_DISPLAY_NAME set "APP_DISPLAY_NAME=%APP_NAME%"

echo [4/5] 버전 정보:
echo       앱 이름: %APP_DISPLAY_NAME%
echo       버전: %VERSION%
echo       빌드 시간: %BUILD_TIME%

:create_shortcut
REM PowerShell로 바로가기 생성
echo [5/5] 바탕화면 바로가기 생성 중...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$shortcutPath = Join-Path $desktop '%APP_DISPLAY_NAME%.lnk'; " ^
    "$WScriptShell = New-Object -ComObject WScript.Shell; " ^
    "$shortcut = $WScriptShell.CreateShortcut($shortcutPath); " ^
    "$shortcut.TargetPath = '%EXE_PATH%'; " ^
    "$shortcut.WorkingDirectory = '%CURRENT_DIR%'; " ^
    "$shortcut.IconLocation = '%EXE_PATH%'; " ^
    "$shortcut.Description = '%APP_DISPLAY_NAME% ^| %VERSION% ^| built %BUILD_TIME%'; " ^
    "$shortcut.Save(); " ^
    "Write-Host ''; " ^
    "Write-Host '========================================' -ForegroundColor Green; " ^
    "Write-Host '   바로가기 생성 완료!' -ForegroundColor Green; " ^
    "Write-Host '========================================' -ForegroundColor Green; " ^
    "Write-Host ''; " ^
    "Write-Host '위치: ' -NoNewline; Write-Host $shortcutPath -ForegroundColor Cyan; " ^
    "Write-Host '이름: ' -NoNewline; Write-Host '%APP_DISPLAY_NAME%' -ForegroundColor Yellow; " ^
    "Write-Host '버전: ' -NoNewline; Write-Host '%VERSION%' -ForegroundColor Yellow; " ^
    "Write-Host '빌드: ' -NoNewline; Write-Host '%BUILD_TIME%' -ForegroundColor Yellow; " ^
    "Write-Host ''; " ^
    "Write-Host '바로가기에 마우스를 올리면 상세 정보를 볼 수 있습니다.' -ForegroundColor Gray; " ^
    "Write-Host '';"

if %ERRORLEVEL% equ 0 (
    echo.
    echo 완료되었습니다!
) else (
    echo.
    echo [오류] 바로가기 생성 중 오류가 발생했습니다.
)

echo.
pause
