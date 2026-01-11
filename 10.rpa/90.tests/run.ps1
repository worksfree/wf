# Unified test runner for WorksFree RPA
[CmdletBinding()]
param(
    [ValidateSet('all','unit','integration','staging','sanity','regression','interactive','static')]
    [string]$Scope = 'all',
    [switch]$Coverage,
    [switch]$Detail,
    [switch]$FailFast,
    [switch]$Last
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $root
Push-Location $root

function Run-StaticChecks {
    Write-Host "==> Static analysis (ruff, mypy)" -ForegroundColor Yellow
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        ruff check ..
    } else {
        Write-Host "ruff not found (pip install ruff)" -ForegroundColor DarkYellow
    }
    if (Get-Command mypy -ErrorAction SilentlyContinue) {
        mypy .. --ignore-missing-imports
    } else {
        Write-Host "mypy not found (pip install mypy)" -ForegroundColor DarkYellow
    }
}

if ($Scope -eq 'static') {
    Run-StaticChecks
    Pop-Location; exit 0
}

$pytestArgs = @()
$pytestArgs += '-v'
$pytestArgs += '--tb=short'
$pytestArgs += '-ra'

switch ($Scope) {
  'unit'        { $pytestArgs += @('-m','unit') }
  'integration' { $pytestArgs += @('-m','integration') }
  'staging'     { $pytestArgs += @('-m','staging') }
  'sanity'      { $pytestArgs += @('-m','sanity') }
  'regression'  { $pytestArgs += @('-m','regression') }
  'interactive' { $pytestArgs += @('-m','interactive') }
  default       { }
}

if ($Coverage) { $pytestArgs += @('--cov=10.common','--cov=30.apps','--cov-report=html','--cov-report=term-missing') }
if ($Detail)   { $pytestArgs += @('-vv','-s') }
if ($FailFast) { $pytestArgs += '-x' }
if ($Last)     { $pytestArgs += '--lf' }

$pytestArgs += '90.tests'

Write-Host "==> pytest @ $Scope" -ForegroundColor Yellow
pytest @pytestArgs
$code = $LASTEXITCODE
Pop-Location
exit $code
