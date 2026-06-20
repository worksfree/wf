# run-load-test.ps1 — WorksFree Hub Load Test Runner
#
# MODES
#   stress   Ramp up true concurrent connections → find NAS hardware limit
#   journey  Simulate real user browsing with think time (5 flows: A~E)
#   mixed    DART API queries (5 VUs) + page browsing simultaneously
#
# QUICK START
#   .\run-load-test.ps1 stress
#   .\run-load-test.ps1 journey
#   .\run-load-test.ps1 mixed

param(
    [Parameter(Position = 0)]
    [ValidateSet('stress', 'journey', 'mixed', '')]
    [string]$Mode = '',

    # Common ─────────────────────────────────────────────────────────────
    # Target environment preset (overridden by -Url)
    #   internal       http://192.168.100.38:8082  (NAS direct, www)
    #   internal-stg   http://192.168.100.38:8080  (NAS direct, staging)
    #   internal-test  http://192.168.100.38:8081  (NAS direct, test)
    #   cloudflare     https://portal.worksfree.kr
    #   cloudflare-stg https://staging.worksfree.kr
    [string]$Target   = 'internal',
    [string]$Url      = '',          # Direct URL (overrides -Target)
    [switch]$CacheBust,              # Bypass CDN cache with ?_=timestamp

    # stress / journey ───────────────────────────────────────────────────
    [int]$MaxVUs  = 0,   # Default: stress=1000, journey=300
    [int]$StepVUs = 0,   # Default: stress=100,  journey=30
    [int]$HoldSec = 60,  # Seconds to hold each VU step
    [int]$P95     = 3000,# Abort threshold (ms)
    [switch]$NoStress,   # journey/stress: keep sleep between requests

    # mixed ──────────────────────────────────────────────────────────────
    [int]$DartVUs    = 5,   # Concurrent DART query users
    [int]$DartMinS   = 30,  # Min think time after DART query (sec)
    [int]$DartMaxS   = 60,  # Max think time after DART query (sec)
    [int]$PageVUs    = 50,  # Max page browsing VUs
    [int]$Duration   = 10,  # Total test duration (minutes)
    [switch]$Verbose         # Log each DART request result
)

# ── Helpers ───────────────────────────────────────────────────────────────
function Show-Usage {
    $cyan  = 'Cyan'; $white = 'White'; $gray = 'Gray'; $yellow = 'Yellow'
    Write-Host ''
    Write-Host '  WorksFree Hub Load Test Runner' -ForegroundColor $cyan
    Write-Host '  =================================' -ForegroundColor $cyan
    Write-Host ''
    Write-Host '  USAGE' -ForegroundColor $yellow
    Write-Host '    .\run-load-test.ps1 <mode> [options]' -ForegroundColor $white
    Write-Host ''
    Write-Host '  MODES' -ForegroundColor $yellow
    Write-Host '    stress    Find NAS hardware limit (VU = real concurrent connections)' -ForegroundColor $white
    Write-Host '    journey   Real user browsing simulation with think time (Flows A~E)' -ForegroundColor $white
    Write-Host '    mixed     DART API queries + page browsing simultaneously' -ForegroundColor $white
    Write-Host ''
    Write-Host '  COMMON OPTIONS' -ForegroundColor $yellow
    Write-Host '    -Target   <env>   internal* | internal-stg | internal-test | cloudflare | cloudflare-stg' -ForegroundColor $gray
    Write-Host '    -Url      <url>   Direct URL (overrides -Target)' -ForegroundColor $gray
    Write-Host '    -CacheBust        Bypass CDN cache with ?_=timestamp' -ForegroundColor $gray
    Write-Host ''
    Write-Host '  STRESS / JOURNEY OPTIONS' -ForegroundColor $yellow
    Write-Host '    -MaxVUs   <n>     Max virtual users       stress:1000  journey:300' -ForegroundColor $gray
    Write-Host '    -StepVUs  <n>     VU increment per step   stress:100   journey:30' -ForegroundColor $gray
    Write-Host '    -HoldSec  <n>     Seconds per step        default:60' -ForegroundColor $gray
    Write-Host '    -P95      <ms>    Abort P95 threshold      default:3000' -ForegroundColor $gray
    Write-Host '    -NoStress         Keep sleep (stress mode becomes ramp-only test)' -ForegroundColor $gray
    Write-Host ''
    Write-Host '  MIXED OPTIONS' -ForegroundColor $yellow
    Write-Host '    -DartVUs  <n>     Concurrent DART users   default:5' -ForegroundColor $gray
    Write-Host '    -DartMinS <n>     Min think time (sec)    default:30' -ForegroundColor $gray
    Write-Host '    -DartMaxS <n>     Max think time (sec)    default:60' -ForegroundColor $gray
    Write-Host '    -PageVUs  <n>     Max page browsing VUs   default:50' -ForegroundColor $gray
    Write-Host '    -Duration <n>     Total minutes           default:10' -ForegroundColor $gray
    Write-Host '    -Verbose          Log each DART request result' -ForegroundColor $gray
    Write-Host ''
    Write-Host '  EXAMPLES' -ForegroundColor $yellow
    Write-Host '    .\run-load-test.ps1 stress' -ForegroundColor $white
    Write-Host '    .\run-load-test.ps1 stress  -MaxVUs 500 -StepVUs 50' -ForegroundColor $white
    Write-Host '    .\run-load-test.ps1 stress  -Target cloudflare -CacheBust' -ForegroundColor $white
    Write-Host '    .\run-load-test.ps1 journey -MaxVUs 300 -StepVUs 30' -ForegroundColor $white
    Write-Host '    .\run-load-test.ps1 mixed' -ForegroundColor $white
    Write-Host '    .\run-load-test.ps1 mixed   -DartVUs 5 -PageVUs 100 -Duration 15 -Verbose' -ForegroundColor $white
    Write-Host ''
    Write-Host '  NAS PORT MAP' -ForegroundColor $yellow
    Write-Host '    :8082 www (production)  :8080 staging  :8081 test' -ForegroundColor $gray
    Write-Host ''
}

function Find-K6 {
    $cmd = Get-Command k6 -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $fb = 'C:\tools\k6\k6.exe'
    if (Test-Path $fb) { return $fb }
    return $null
}

# ── Mode guard ────────────────────────────────────────────────────────────
if (-not $Mode) {
    Show-Usage
    exit 0
}

# ── Locate k6 ────────────────────────────────────────────────────────────
$K6 = Find-K6
if (-not $K6) {
    Write-Host 'ERROR: k6 not found.' -ForegroundColor Red
    Write-Host '  Install: https://github.com/grafana/k6/releases' -ForegroundColor Gray
    Write-Host '  Or place k6.exe at C:\tools\k6\k6.exe' -ForegroundColor Gray
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReportTs  = Get-Date -Format 'yyyyMMdd-HHmm'
$LogFile   = Join-Path $ScriptDir "report-$ReportTs.txt"

# ── Build k6 args ─────────────────────────────────────────────────────────
$k6Args = @('run')

if ($Mode -eq 'mixed') {
    # ── mixed mode ────────────────────────────────────────────────────────
    $Script = Join-Path $ScriptDir 'nas-mixed-test.js'
    $targetUrl = if ($Url) { $Url } else { '' }

    $k6Args += '--env', "DART_VUS=$DartVUs"
    $k6Args += '--env', "DART_MIN_SLEEP=$DartMinS"
    $k6Args += '--env', "DART_MAX_SLEEP=$DartMaxS"
    $k6Args += '--env', "PAGE_MAX_VUS=$PageVUs"
    $k6Args += '--env', "DURATION_MIN=$Duration"
    if ($targetUrl) { $k6Args += '--env', "TARGET_URL=$targetUrl" }
    else            { $k6Args += '--env', "TARGET_ENV=$Target"    }
    if ($Verbose)   { $k6Args += '--env', 'VERBOSE=true'          }

    Write-Host ''
    Write-Host "  [mixed]  DART ${DartVUs}VU (${DartMinS}~${DartMaxS}s) + page max ${PageVUs}VU  /  ${Duration}min" -ForegroundColor Cyan

} else {
    # ── stress / journey mode ─────────────────────────────────────────────
    $Script = Join-Path $ScriptDir 'nas-load-test.js'

    $defaultMax  = if ($Mode -eq 'stress') { 1000 } else { 300 }
    $defaultStep = if ($Mode -eq 'stress') { 100  } else { 30  }
    $actualMax   = if ($MaxVUs  -gt 0) { $MaxVUs  } else { $defaultMax  }
    $actualStep  = if ($StepVUs -gt 0) { $StepVUs } else { $defaultStep }
    $targetUrl   = if ($Url) { $Url } else { '' }

    if ($Mode -eq 'stress' -and -not $NoStress) {
        $k6Args += '--env', 'STRESS=true'
    }
    if ($Mode -eq 'journey') {
        $k6Args += '--env', 'TEST_MODE=journey'
    }
    $k6Args += '--env', "MAX_VUS=$actualMax"
    $k6Args += '--env', "STEP_VUS=$actualStep"
    $k6Args += '--env', "STEP_HOLD=$HoldSec"
    $k6Args += '--env', "P95_LIMIT=$P95"
    if ($targetUrl)  { $k6Args += '--env', "TARGET_URL=$targetUrl" }
    else             { $k6Args += '--env', "TARGET_ENV=$Target"    }
    if ($CacheBust)  { $k6Args += '--env', 'CACHE_BUST=true'       }

    $stressNote = if ($Mode -eq 'stress' -and -not $NoStress) { '  STRESS=true (no sleep)' } else { '' }
    Write-Host ''
    Write-Host ("  [{0}]  target={1}  max={2}VU  step={3}VU  hold={4}s  P95<{5}ms{6}" -f `
        $Mode, $(if ($targetUrl) { $targetUrl } else { $Target }), $actualMax, $actualStep, $HoldSec, $P95, $stressNote) -ForegroundColor Cyan
}

$k6Args += $Script

# ── Run ──────────────────────────────────────────────────────────────────
Write-Host "  Report : $LogFile" -ForegroundColor Gray
Write-Host "  k6     : $K6" -ForegroundColor Gray
Write-Host ''

"[START] $Mode  $(Get-Date)" | Out-File $LogFile -Encoding utf8

& $K6 @k6Args 2>&1 | Tee-Object -FilePath $LogFile -Append

# Move JSON report to timestamped file
$jsonSrc = Join-Path $ScriptDir (
    if ($Mode -eq 'mixed') { 'nas-mixed-test-report.json' } else { 'nas-load-test-report.json' }
)
$jsonDst = Join-Path $ScriptDir "report-$ReportTs.json"
if (Test-Path $jsonSrc) { Move-Item $jsonSrc $jsonDst -Force }

"[END]   $Mode  $(Get-Date)" | Out-File $LogFile -Append -Encoding utf8
Write-Host ''
Write-Host "  Done. Report: $LogFile" -ForegroundColor Green
if (Test-Path $jsonDst) {
    Write-Host "  JSON:  $jsonDst" -ForegroundColor Green
}
Write-Host ''
