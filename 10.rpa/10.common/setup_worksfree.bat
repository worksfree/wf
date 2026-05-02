@echo off
chcp 65001 >nul
REM ============================================================================
REM WorksFree 앱 설정 및 바로가기 생성 스크립트
REM ============================================================================
REM
REM 사용법:
REM   setup_worksfree.bat          - 초기 설정 + 바로가기 생성
REM   setup_worksfree.bat /reset-app   - 현재 앱 설정만 초기화
REM   setup_worksfree.bat /reset-all   - .wf_rpa 전체 초기화
REM   setup_worksfree.bat /shortcut    - 바로가기만 생성
REM   setup_worksfree.bat /uninstall   - 앱 관련 파일 전체 제거
REM
REM 모든 WorksFree 앱에서 공통으로 사용 가능합니다.
REM ============================================================================

setlocal enabledelayedexpansion

REM 명령줄 인수 처리
set "MODE=setup"
if /i "%~1"=="/reset-app" set "MODE=reset-app"
if /i "%~1"=="/reset-all" set "MODE=reset-all"
if /i "%~1"=="/shortcut" set "MODE=shortcut"
if /i "%~1"=="/uninstall" set "MODE=uninstall"
if /i "%~1"=="/?" goto :show_help
if /i "%~1"=="/help" goto :show_help

REM 현재 스크립트가 실행되는 폴더 (portable 폴더)
set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"

REM 사용자 홈 .wf_rpa 경로
set "USER_WF_RPA=%USERPROFILE%\.wf_rpa"

REM EXE 파일 찾기
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

REM 앱 이름 추출 (확장자 제거)
set "APP_NAME=%EXE_FILE:~0,-4%"
set "EXE_PATH=%CURRENT_DIR%%EXE_FILE%"

REM 번들 설정 경로
set "BUNDLE_WF_RPA=%CURRENT_DIR%_internal\.wf_rpa"

REM policy.json에서 display_name 읽기
set "POLICY_JSON=%BUNDLE_WF_RPA%\%APP_NAME%\policy.json"
set "APP_DISPLAY_NAME=%APP_NAME%"
if exist "%POLICY_JSON%" (
    for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "$json = Get-Content '%POLICY_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.identity.display_name" 2^>nul`) do set "APP_DISPLAY_NAME=%%D"
)

REM 모드별 분기
if "%MODE%"=="reset-app" goto :reset_app
if "%MODE%"=="reset-all" goto :reset_all
if "%MODE%"=="shortcut" goto :create_shortcut_only
if "%MODE%"=="uninstall" goto :uninstall

REM ============================================================================
REM 기본 모드: 초기 설정 + 바로가기 생성
REM ============================================================================
:setup
echo.
echo ========================================
echo WorksFree %APP_DISPLAY_NAME% 설정
echo ========================================
echo.

REM [1] 사용자 홈 .wf_rpa 폴더 생성
echo [1/5] 설정 폴더 확인 중...
if not exist "%USER_WF_RPA%" (
    mkdir "%USER_WF_RPA%"
    echo       생성됨: %USER_WF_RPA%
) else (
    echo       존재함: %USER_WF_RPA%
)

REM [2] wf_rpa_config.json 복사
echo [2/5] 공통 설정 파일 복사 중...
set "SRC_CONFIG=%BUNDLE_WF_RPA%\wf_rpa_config.json"
set "DST_CONFIG=%USER_WF_RPA%\wf_rpa_config.json"
if exist "%SRC_CONFIG%" (
    if not exist "%DST_CONFIG%" (
        copy /y "%SRC_CONFIG%" "%DST_CONFIG%" >nul
        echo       복사됨: wf_rpa_config.json
    ) else (
        echo       존재함: wf_rpa_config.json (건너뜀)
    )
) else (
    echo       [경고] wf_rpa_config.json을 찾을 수 없습니다.
)

REM [3] credential 파일 복사 (silver-argon-xxx.json만, backup 제외)
echo [3/5] 인증 파일 복사 중...
set "CRED_COPIED=0"
for %%F in ("%BUNDLE_WF_RPA%\silver-argon-*.json") do (
    set "CRED_NAME=%%~nxF"
    REM backup 파일 제외
    echo !CRED_NAME! | findstr /i "backup" >nul
    if errorlevel 1 (
        set "DST_CRED=%USER_WF_RPA%\!CRED_NAME!"
        if not exist "!DST_CRED!" (
            copy /y "%%F" "!DST_CRED!" >nul
            echo       복사됨: !CRED_NAME!
            set "CRED_COPIED=1"
        ) else (
            echo       존재함: !CRED_NAME! (건너뜀)
            set "CRED_COPIED=1"
        )
    )
)
if "%CRED_COPIED%"=="0" (
    echo       [경고] 인증 파일을 찾을 수 없습니다.
)

REM [4] 앱별 설정 폴더 및 파일 복사
echo [4/5] 앱 설정 파일 복사 중...
set "SRC_APP_DIR=%BUNDLE_WF_RPA%\%APP_NAME%"
set "DST_APP_DIR=%USER_WF_RPA%\%APP_NAME%"

if not exist "%DST_APP_DIR%" (
    mkdir "%DST_APP_DIR%"
    echo       생성됨: %APP_NAME%\
)

REM settings.json 복사
if exist "%SRC_APP_DIR%\settings.json" (
    if not exist "%DST_APP_DIR%\settings.json" (
        copy /y "%SRC_APP_DIR%\settings.json" "%DST_APP_DIR%\settings.json" >nul
        echo       복사됨: %APP_NAME%\settings.json
    ) else (
        echo       존재함: %APP_NAME%\settings.json (건너뜀)
    )
)

REM policy.json 복사
if exist "%SRC_APP_DIR%\policy.json" (
    if not exist "%DST_APP_DIR%\policy.json" (
        copy /y "%SRC_APP_DIR%\policy.json" "%DST_APP_DIR%\policy.json" >nul
        echo       복사됨: %APP_NAME%\policy.json
    ) else (
        echo       존재함: %APP_NAME%\policy.json (건너뜀)
    )
)

REM [5] 바로가기 생성
echo [5/5] 바탕화면 바로가기 생성 중...
call :create_shortcut

echo.
echo ========================================
echo   설정 완료!
echo ========================================
echo.
echo 바탕화면의 '%APP_DISPLAY_NAME%' 바로가기로 앱을 실행하세요.
echo.
pause
exit /b 0

REM ============================================================================
REM /reset-app: 현재 앱 설정만 초기화
REM ============================================================================
:reset_app
echo.
echo ========================================
echo %APP_DISPLAY_NAME% 설정 초기화
echo ========================================
echo.
echo 이 작업은 %APP_NAME% 앱의 설정을 초기화합니다.
echo 크레딧 정보와 사용자 설정이 삭제됩니다.
echo.
set /p "CONFIRM=계속하시겠습니까? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 취소되었습니다.
    pause
    exit /b 0
)

set "DST_APP_DIR=%USER_WF_RPA%\%APP_NAME%"
if exist "%DST_APP_DIR%" (
    rmdir /s /q "%DST_APP_DIR%"
    echo [완료] %APP_NAME% 설정 폴더 삭제됨
)

echo.
echo 앱을 다시 실행하면 초기 설정이 적용됩니다.
echo 또는 'setup_worksfree.bat'를 실행하여 설정을 복원하세요.
echo.
pause
exit /b 0

REM ============================================================================
REM /reset-all: .wf_rpa 전체 초기화
REM ============================================================================
:reset_all
echo.
echo ========================================
echo WorksFree 전체 설정 초기화
echo ========================================
echo.
echo [경고] 이 작업은 모든 WorksFree 앱의 설정을 삭제합니다!
echo.
echo 삭제 대상: %USER_WF_RPA%
echo.
echo 포함 내용:
echo   - 모든 앱의 설정 파일
echo   - 크레딧 정보
echo   - 인증 파일
echo.
set /p "CONFIRM=정말 계속하시겠습니까? (YES 입력): "
if /i not "%CONFIRM%"=="YES" (
    echo 취소되었습니다.
    pause
    exit /b 0
)

if exist "%USER_WF_RPA%" (
    rmdir /s /q "%USER_WF_RPA%"
    echo.
    echo [완료] .wf_rpa 폴더 전체 삭제됨
)

echo.
echo 모든 WorksFree 앱 설정이 초기화되었습니다.
echo 앱을 다시 실행하거나 setup_worksfree.bat를 실행하세요.
echo.
pause
exit /b 0

REM ============================================================================
REM /shortcut: 바로가기만 생성
REM ============================================================================
:create_shortcut_only
echo.
echo ========================================
echo WorksFree 바로가기 생성
echo ========================================
echo.
call :create_shortcut
echo.
pause
exit /b 0

REM ============================================================================
REM /uninstall: 앱 관련 파일 전체 제거
REM ============================================================================
:uninstall
echo.
echo ========================================
echo %APP_DISPLAY_NAME% 제거
echo ========================================
echo.
echo 이 작업은 다음을 삭제합니다:
echo   - 바탕화면 바로가기
echo   - 앱 설정 폴더 (%USER_WF_RPA%\%APP_NAME%)
echo.
echo [참고] 앱 실행 파일은 수동으로 삭제해야 합니다.
echo.
set /p "CONFIRM=계속하시겠습니까? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo 취소되었습니다.
    pause
    exit /b 0
)

REM 바로가기 삭제
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\%APP_DISPLAY_NAME%.lnk"
if exist "%SHORTCUT_PATH%" (
    del /f "%SHORTCUT_PATH%"
    echo [완료] 바로가기 삭제됨
) else (
    echo [정보] 바로가기가 없습니다.
)

REM 앱 설정 폴더 삭제
set "DST_APP_DIR=%USER_WF_RPA%\%APP_NAME%"
if exist "%DST_APP_DIR%" (
    rmdir /s /q "%DST_APP_DIR%"
    echo [완료] 앱 설정 폴더 삭제됨
) else (
    echo [정보] 앱 설정 폴더가 없습니다.
)

echo.
echo %APP_DISPLAY_NAME% 관련 설정이 제거되었습니다.
echo.
pause
exit /b 0

REM ============================================================================
REM 바로가기 생성 서브루틴
REM ============================================================================
:create_shortcut
REM settings.json에서 버전 정보 읽기
set "SETTINGS_JSON=%BUNDLE_WF_RPA%\%APP_NAME%\settings.json"
set "VERSION=unknown"
set "BUILD_COUNT=unknown"

if exist "%SETTINGS_JSON%" (
    for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$json = Get-Content '%SETTINGS_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.runtime_config.full_version" 2^>nul`) do set "VERSION=%%V"
    for /f "usebackq delims=" %%B in (`powershell -NoProfile -Command "$json = Get-Content '%SETTINGS_JSON%' -Raw -Encoding UTF8 | ConvertFrom-Json; $json.runtime_config.build_count" 2^>nul`) do set "BUILD_COUNT=%%B"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
    "$shortcutPath = Join-Path $desktop '%APP_DISPLAY_NAME%.lnk'; " ^
    "$WScriptShell = New-Object -ComObject WScript.Shell; " ^
    "$shortcut = $WScriptShell.CreateShortcut($shortcutPath); " ^
    "$shortcut.TargetPath = '%EXE_PATH%'; " ^
    "$shortcut.WorkingDirectory = '%CURRENT_DIR%'; " ^
    "$shortcut.IconLocation = '%EXE_PATH%'; " ^
    "$shortcut.Description = '%APP_DISPLAY_NAME% %VERSION% (Build #%BUILD_COUNT%)'; " ^
    "$shortcut.Save(); " ^
    "Write-Host '       완료: %APP_DISPLAY_NAME%.lnk' -ForegroundColor Green;"

exit /b 0

REM ============================================================================
REM 도움말 표시
REM ============================================================================
:show_help
echo.
echo ========================================
echo WorksFree 설정 스크립트 사용법
echo ========================================
echo.
echo setup_worksfree.bat [옵션]
echo.
echo 옵션:
echo   (없음)        초기 설정 수행 + 바로가기 생성
echo   /shortcut     바로가기만 생성
echo   /reset-app    현재 앱 설정만 초기화
echo   /reset-all    모든 WorksFree 앱 설정 초기화
echo   /uninstall    앱 관련 파일 제거 (바로가기 + 설정)
echo   /?, /help     이 도움말 표시
echo.
echo 예시:
echo   setup_worksfree.bat              - 처음 설치 시
echo   setup_worksfree.bat /reset-app   - 앱 설정 문제 시
echo   setup_worksfree.bat /reset-all   - 전체 초기화
echo.
pause
exit /b 0
