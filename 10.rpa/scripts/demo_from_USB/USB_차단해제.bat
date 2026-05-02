@echo off
:: 일괄 차단 해제 스크립트
cd /d "%~dp0"
color 0E

echo ========================================
echo    USB 파일 차단 해제 도구
echo ========================================
echo.
echo 이 도구는 현재 폴더와 하위 폴더의
echo 모든 .exe 파일의 보안 차단을 해제합니다.
echo.
echo [주의] 신뢰할 수 있는 파일에만 사용하세요!
echo ========================================
echo.

set /p confirm="계속하시겠습니까? (Y/N): "
if /i not "%confirm%"=="Y" goto :end

echo.
echo [1단계] PowerShell로 차단 해제 중...
powershell.exe -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse -Include *.exe | ForEach-Object { Unblock-File -Path $_.FullName -Confirm:$false; Write-Host ""차단 해제: $($_.Name)"" }"

echo.
echo [2단계] Zone.Identifier 스트림 제거 중...
for /r %%i in (*.exe) do (
    echo 처리 중: %%~nxi
    powershell.exe -Command "Remove-Item -Path '%%i' -Stream Zone.Identifier -ErrorAction SilentlyContinue" 2>nul
)

echo.
echo ========================================
echo    차단 해제 완료!
echo ========================================
echo.
echo 이제 batch 파일을 다시 실행해보세요.
echo.
pause

:end
exit