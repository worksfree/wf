# schedule-loadtest.ps1
# WorksFree Hub NAS Load Test Scheduler
#
# Usage:
#   .\schedule-loadtest.ps1                          # default 02:00, stress 200VU
#   .\schedule-loadtest.ps1 -RunAt 08:00
#   .\schedule-loadtest.ps1 -RunAt 03:00 -MaxVUs 1000 -StepVUs 100
#   .\schedule-loadtest.ps1 -Mode mixed -RunAt 23:00
#
# Run as Administrator

param(
    [string]$RunAt  = "02:00",
    [ValidateSet('stress', 'journey', 'mixed')]
    [string]$Mode   = 'stress',
    [int]$MaxVUs    = 200,    # stress/journey only
    [int]$StepVUs   = 10,     # stress/journey only
    [int]$HoldSec   = 60,
    [int]$P95       = 3000,
    [string]$Target = 'internal',  # internal | cloudflare | cloudflare-stg
    [int]$DartVUs   = 5,      # mixed only
    [int]$PageVUs   = 50,     # mixed only
    [int]$Duration  = 10      # mixed only (minutes)
)

$TaskName = "WF-NAS-LoadTest"

if ($RunAt -notmatch '^\d{2}:\d{2}$') {
    Write-Host "ERROR: -RunAt must be HH:mm format (e.g. 02:00, 14:30)" -ForegroundColor Red
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunScript = Join-Path $ScriptDir "run-load-test.ps1"

if (-not (Test-Path $RunScript)) {
    Write-Host "ERROR: run-load-test.ps1 not found at $RunScript" -ForegroundColor Red
    exit 1
}

# ── Build args for run-load-test.ps1 ─────────────────────────────────────
if ($Mode -eq 'mixed') {
    $runArgs = "$Mode -DartVUs $DartVUs -PageVUs $PageVUs -Duration $Duration -Target $Target"
} else {
    $runArgs = "$Mode -MaxVUs $MaxVUs -StepVUs $StepVUs -HoldSec $HoldSec -P95 $P95 -Target $Target"
}

$psArgs = "-NonInteractive -ExecutionPolicy Bypass -File `"$RunScript`" $runArgs"

# ── Schedule ──────────────────────────────────────────────────────────────
$today     = Get-Date
$runAtTime = [datetime]::ParseExact($today.ToString("yyyy-MM-dd") + " $RunAt", "yyyy-MM-dd HH:mm", $null)
if ($runAtTime -le $today) {
    $runAtTime = $runAtTime.AddDays(1)
    Write-Host "Time $RunAt already passed -> scheduled for tomorrow $RunAt" -ForegroundColor Yellow
}

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs -WorkingDirectory $ScriptDir
$trigger  = New-ScheduledTaskTrigger -Once -At $runAtTime
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 3) -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force -ErrorAction Stop | Out-Null

    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  Scheduled successfully" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  Time       : $($runAtTime.ToString('yyyy-MM-dd HH:mm'))" -ForegroundColor White
    Write-Host "  Mode       : $Mode" -ForegroundColor White
    Write-Host "  Target     : $Target" -ForegroundColor White
    if ($Mode -eq 'mixed') {
        Write-Host "  DART VUs   : $DartVUs  Page VUs: $PageVUs  Duration: ${Duration}min" -ForegroundColor White
    } else {
        Write-Host "  Max VU     : $MaxVUs (step $StepVUs, hold ${HoldSec}s)  P95<${P95}ms" -ForegroundColor White
    }
    Write-Host "  Task name  : $TaskName" -ForegroundColor White
    Write-Host "  Report dir : $ScriptDir\report-*.txt" -ForegroundColor White
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Cancel : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    Write-Host "  Run now: & '$RunScript' $Mode"
} catch {
    Write-Host "Failed to register task (requires Administrator)" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
}
