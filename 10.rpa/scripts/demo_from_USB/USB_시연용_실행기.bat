@echo off
REM ===================================================
REM USB 포터블 앱 실행기 - 5개 앱 간단 버전
REM ===================================================
REM 이 파일을 USB 루트 디렉토리에 놓고 실행하세요
REM ===================================================

cd /d "%~dp0"

echo.
echo ========================================
echo     기구설계 자동화 툴 실행기
echo ========================================
echo.

REM 앱 1 - DWG 프린터
if exist ".\시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe" (
    echo [1/5] DWG 프린터 실행 중...
    start "" ".\시연_print_DWG_with_tkinter\print_DWG_with_tkinter.exe"
) else (
    echo [1/5] DWG 프린터를 찾을 수 없습니다.
)
timeout /t 1 /nobreak > nul

REM 앱 2 - 다른 자동화 툴 (예시)
if exist ".\시연_batch_rename_tool\batch_rename_tool.exe" (
    echo [2/5] 일괄 이름변경 툴 실행 중...
    start "" ".\시연_batch_rename_tool\batch_rename_tool.exe"
) else (
    echo [2/5] 일괄 이름변경 툴을 찾을 수 없습니다.
)
timeout /t 1 /nobreak > nul

REM 앱 3 - 다른 자동화 툴 (예시)
if exist ".\시연_bom_generator\bom_generator.exe" (
    echo [3/5] BOM 생성기 실행 중...
    start "" ".\시연_bom_generator\bom_generator.exe"
) else (
    echo [3/5] BOM 생성기를 찾을 수 없습니다.
)
timeout /t 1 /nobreak > nul

REM 앱 4 - 다른 자동화 툴 (예시)
if exist ".\시연_drawing_checker\drawing_checker.exe" (
    echo [4/5] 도면 검사기 실행 중...
    start "" ".\시연_drawing_checker\drawing_checker.exe"
) else (
    echo [4/5] 도면 검사기를 찾을 수 없습니다.
)
timeout /t 1 /nobreak > nul

REM 앱 5 - 다른 자동화 툴 (예시)
if exist ".\시연_part_library\part_library.exe" (
    echo [5/5] 부품 라이브러리 실행 중...
    start "" ".\시연_part_library\part_library.exe"
) else (
    echo [5/5] 부품 라이브러리를 찾을 수 없습니다.
)

echo.
echo ========================================
echo     모든 앱 실행 완료!
echo ========================================
echo.
echo * USB 제거 전 모든 앱을 종료하세요
echo * 문제 발생 시 개별 폴더에서 직접 실행하세요
echo.
pause