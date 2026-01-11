# Korean Filename Normalizer UI 테스트 실행 스크립트
# PowerShell 스크립트

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Korean Filename Normalizer UI Tests" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Python 환경 확인
Write-Host "Python 환경 확인 중..." -ForegroundColor Yellow
python --version

# pytest 설치 확인
Write-Host "`npytest 설치 확인 중..." -ForegroundColor Yellow
$pytestCheck = python -m pip list | Select-String "pytest"
if (-not $pytestCheck) {
    Write-Host "pytest가 설치되어 있지 않습니다. 설치를 진행합니다..." -ForegroundColor Red
    python -m pip install pytest pytest-timeout
} else {
    Write-Host "pytest가 이미 설치되어 있습니다." -ForegroundColor Green
}

# 테스트 실행
Write-Host "`nUI 자동화 테스트 시작..." -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Cyan

# 테스트 실행 (상세 모드)
python -m pytest test_ui_automation.py -v -s --tb=short --color=yes

# 결과 확인
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n================================" -ForegroundColor Green
    Write-Host "모든 테스트가 성공했습니다! ✓" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
} else {
    Write-Host "`n================================" -ForegroundColor Red
    Write-Host "일부 테스트가 실패했습니다. ✗" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Red
}

Write-Host "`n테스트 완료. 아무 키나 눌러 종료..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
