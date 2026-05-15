# WorksFree 결제 Workers 배포 스크립트
# 실행 전 wrangler 로그인 필요: npx wrangler login
#
# 사용법:
#   .\deploy-workers.ps1          # 둘 다 배포
#   .\deploy-workers.ps1 -toss    # Toss Worker만
#   .\deploy-workers.ps1 -stripe  # Stripe Worker만

param(
  [switch]$toss,
  [switch]$stripe
)

$doToss   = $toss   -or (-not $toss -and -not $stripe)
$doStripe = $stripe -or (-not $toss -and -not $stripe)

Set-Location $PSScriptRoot

if ($doToss) {
  Write-Host "`n▶ Toss Verify Worker 배포 중..." -ForegroundColor Cyan
  npx wrangler deploy --config wrangler-toss.toml
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ toss-verify.worksfree.workers.dev 배포 완료" -ForegroundColor Green
  } else {
    Write-Host "  ❌ Toss Worker 배포 실패" -ForegroundColor Red
  }
}

if ($doStripe) {
  Write-Host "`n▶ Stripe Session Worker 배포 중..." -ForegroundColor Cyan
  npx wrangler deploy --config wrangler-stripe.toml
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ stripe-session.worksfree.workers.dev 배포 완료" -ForegroundColor Green
  } else {
    Write-Host "  ❌ Stripe Worker 배포 실패" -ForegroundColor Red
  }
}

Write-Host "`n배포 완료. 시크릿 키 설정은 README.md 참조." -ForegroundColor Yellow
