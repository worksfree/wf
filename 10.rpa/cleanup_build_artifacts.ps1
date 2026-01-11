# Clean up build and distribution artifacts for RPA projects
[CmdletBinding(SupportsShouldProcess=$true)]
param(
    # 스크립트 위치의 절대 경로(단일 문자열)
    [string]$Root = (Get-Item -LiteralPath $PSScriptRoot).FullName
)

# Join-Path 입력용으로 단일 문자열만 사용
$RootPath = [string]($Root | Select-Object -First 1)

function Remove-PathSafe {
    param(
        [Parameter(Mandatory=$true)][string]$Path
    )
    if (Test-Path -LiteralPath $Path) {
        if ($PSCmdlet.ShouldProcess($Path, "Remove-Item")) {
            Write-Host ("Removing: {0}" -f $Path)
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Verbose ("Skip missing: {0}" -f $Path)
    }
}

# Top-level common folders to clean inside 10.rpa
$targets = @(
    (Join-Path -Path $RootPath -ChildPath '.build_templates')
    (Join-Path -Path $RootPath -ChildPath 'build')
    (Join-Path -Path $RootPath -ChildPath 'dist')
)

# App subfolders to clean for common patterns
$appRoots = @(
    (Join-Path -Path $RootPath -ChildPath '30.apps')
    (Join-Path -Path $RootPath -ChildPath '50.data')
    (Join-Path -Path $RootPath -ChildPath '70.webs')
    (Join-Path -Path $RootPath -ChildPath '90.tests')
)

foreach ($ar in $appRoots) {
    if (Test-Path -LiteralPath $ar) {
        Get-ChildItem -LiteralPath $ar -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $targets += (Join-Path $_.FullName 'build')
            $targets += (Join-Path $_.FullName 'dist')
            $targets += (Join-Path $_.FullName '.build_templates')
        }
    }
}

Write-Host "Cleaning build artifacts under: $Root" -ForegroundColor Cyan
foreach ($t in $targets | Sort-Object -Unique) {
    Remove-PathSafe -Path $t
}

Write-Host "Cleanup complete." -ForegroundColor Green
