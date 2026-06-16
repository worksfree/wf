# WorksFree Hub — Playwright 테스트 실행 스크립트
# 사용법:
#   .\run-tests.ps1          → 전체 테스트 (headless)
#   .\run-tests.ps1 -Headed  → 브라우저 창 보이면서 실행
#   .\run-tests.ps1 -Smoke   → 스모크 테스트만
#   .\run-tests.ps1 -Report  → 마지막 결과 보고서 열기

param(
  [switch]$Headed,
  [switch]$Smoke,
  [switch]$Report,
  [switch]$Install,
  [string]$Filter = ''
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ① npm 패키지 설치 확인
if ($Install -or -not (Test-Path "node_modules")) {
  Write-Host "`n[1/2] npm 패키지 설치 중..." -ForegroundColor Cyan
  npm install
  if ($LASTEXITCODE -ne 0) { Write-Host "npm install 실패" -ForegroundColor Red; exit 1 }

  Write-Host "[2/2] Playwright 브라우저 설치 중..." -ForegroundColor Cyan
  npx playwright install chromium
  if ($LASTEXITCODE -ne 0) { Write-Host "브라우저 설치 실패" -ForegroundColor Red; exit 1 }
  Write-Host "설치 완료`n" -ForegroundColor Green
}

# ② 보고서만 열기
if ($Report) {
  npx playwright show-report
  exit 0
}

# ③ 테스트 명령 구성
$args = @()
if ($Headed) { $args += '--headed' }
if ($Smoke)  { $args += 'tests/smoke.spec.js' }
if ($Filter) { $args += "--grep=`"$Filter`"" }

# 실행
Write-Host "테스트 시작: $(if ($Smoke) {'smoke only'} else {'전체'})" -ForegroundColor Yellow
npx playwright test @args

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
  Write-Host "`n✅ 모든 테스트 통과" -ForegroundColor Green
} else {
  Write-Host "`n❌ 실패한 테스트가 있습니다. 보고서 확인:" -ForegroundColor Red
  Write-Host "   .\run-tests.ps1 -Report" -ForegroundColor Yellow
}
exit $exitCode
