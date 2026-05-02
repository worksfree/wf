param(
    [object]$BuildType = 2,  # 1=onedir, 2=onedir+zip, 3=onedir+zip+installer, 4=zip only, 5=installer only
    [switch]$Clean,
    [switch]$PostClean
)

if ($BuildType -is [System.Object[]]) {
    try { $BuildType = [int]($BuildType -join '') } catch { }
}

$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "[BUILD] Working directory: $ScriptDir" -ForegroundColor Cyan

$AppName    = 'ban_redirection'
$AppDir     = $ScriptDir
$SpecFile   = Join-Path $AppDir 'ban_redirection.spec'
$Candidates = 'D:\release\candidates'

$_pi = Get-Command pyinstaller -ErrorAction SilentlyContinue
$PyInstaller     = if ($_pi) { $_pi.Source } else { 'pyinstaller' }
$PyInstallerArgs = @('--noconfirm', '--log-level=WARN', $SpecFile)

function Clean-Tree($p) {
    if (Test-Path $p) { Remove-Item -Recurse -Force -LiteralPath $p -ErrorAction SilentlyContinue }
}
function Ensure-Dir($p) {
    if (!(Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}
function Read-Version($settingsJson) {
    if (!(Test-Path $settingsJson)) { return $null }
    try { (Get-Content $settingsJson -Raw | ConvertFrom-Json).runtime_config.full_version } catch { $null }
}

function Ensure-Utf8Bom($path) {
    if (!(Test-Path $path)) { return }

    $bytes = [System.IO.File]::ReadAllBytes($path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        return
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false, $true)
    $utf8Bom   = New-Object System.Text.UTF8Encoding($true)
    $text      = $utf8NoBom.GetString($bytes)
    [System.IO.File]::WriteAllText($path, $text, $utf8Bom)
    Write-Host "Normalized encoding (UTF-8 BOM): $path" -ForegroundColor DarkGray
}

function Build-Onedir {
    Write-Host "==> PyInstaller onedir build" -ForegroundColor Yellow
    $env:WF_EXTERNAL_PACKAGER = '1'

    $distPath  = Join-Path $AppDir 'dist'
    $buildPath = Join-Path $AppDir 'build'
    if ((Test-Path $distPath) -or (Test-Path $buildPath)) {
        Write-Host "   Cleaning dist/build..." -ForegroundColor Gray
        Get-Process | Where-Object { $_.Path -like "*$AppName*" } |
            Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        for ($i = 0; $i -lt 3; $i++) {
            Remove-Item $distPath  -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item $buildPath -Recurse -Force -ErrorAction SilentlyContinue
            if (!(Test-Path $distPath) -and !(Test-Path $buildPath)) { break }
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Seconds 1
    }

    Clean-Tree "$env:LOCALAPPDATA\pyinstaller"

    # Out-Host: prevents PyInstaller stdout from polluting the function return value
    & $PyInstaller @PyInstallerArgs | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
    if (!(Test-Path "$AppDir\dist\$AppName")) { throw 'dist output missing' }
    return "$AppDir\dist\$AppName"
}

function Copy-Portable($src, $targetRoot, $version) {
    $base     = Join-Path $targetRoot "${AppName}_${version}"
    $portable = Join-Path $base "${AppName}_${version}_portable"
    Ensure-Dir $base
    if (Test-Path $portable) { Remove-Item -Recurse -Force $portable }
    Copy-Item -Recurse -Force -LiteralPath $src -Destination $portable

    $commonDir = Join-Path $PSScriptRoot '..\..\10.common'
    foreach ($bat in @('setup_worksfree.bat')) {
        $s = Join-Path $commonDir $bat
        if (Test-Path $s) { Copy-Item -Path $s -Destination $portable -Force }
    }
    return @{ Base = $base; Portable = $portable }
}

function Make-Zip($portablePath) {
    $zip = Join-Path ([System.IO.Path]::GetDirectoryName($portablePath)) `
        ("${AppName}_" + (Split-Path $portablePath -Leaf).Split('_')[-2] + '_portable.zip')
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $portablePath '*') -DestinationPath $zip -Force
    Write-Host "ZIP: $zip" -ForegroundColor Green
    return $zip
}

function Create-DesktopShortcut($exePath, $version) {
    try {
        $lnk      = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ban Redirection.lnk'
        $wsh      = New-Object -ComObject WScript.Shell
        $sc       = $wsh.CreateShortcut($lnk)
        $sc.TargetPath       = $exePath
        $sc.WorkingDirectory = Split-Path $exePath
        $sc.IconLocation     = $exePath
        $sc.Description      = "Ban Redirection v$version"
        $sc.Save()
        Write-Host "Shortcut: $lnk" -ForegroundColor Green
    } catch {
        Write-Warning "Shortcut creation failed: $_"
    }
}

function Make-Installer($portablePath) {
    $nsis = 'C:\Program Files (x86)\NSIS\makensis.exe'
    if (!(Test-Path $nsis)) { Write-Warning 'NSIS not found; skipping installer'; return $null }

    $verFull = (Split-Path $portablePath -Leaf).Replace("${AppName}_", '').Replace('_portable', '')
    $verNum  = $verFull.TrimStart('v')
    $base    = Split-Path $portablePath -Parent
    $nsiFile = Join-Path $AppDir 'ban_redirection_installer.nsi'
    $outFile = "${AppName}_${verNum}_installer.exe"

    if (!(Test-Path $nsiFile)) { Write-Warning "NSI not found: $nsiFile"; return $null }
    Ensure-Utf8Bom $nsiFile

    Push-Location $AppDir
    try {
        $r = Start-Process -FilePath $nsis `
            -ArgumentList ("/V2", "/DVERSION=$verNum", $nsiFile) `
            -PassThru -Wait -NoNewWindow
        if ($r.ExitCode -ne 0) { throw "NSIS failed ($($r.ExitCode))" }
        $exe = Join-Path $AppDir $outFile
        if (Test-Path $exe) {
            Move-Item -Force $exe -Destination $base
            Write-Host "Installer: $(Join-Path $base $outFile)" -ForegroundColor Green
            return Join-Path $base $outFile
        }
        return $null
    } finally { Pop-Location }
}

# ==================== Main ====================
Write-Host "==== $AppName build (BuildType=$BuildType) ====" -ForegroundColor Cyan
Ensure-Dir $Candidates

switch ($BuildType) { 1 {} 2 {} 3 {} 4 {} 5 {} default { $BuildType = 2 } }

$distPath = Build-Onedir

$settingsFile = Join-Path $AppDir "..\..\10.common\config\$AppName\settings.json"
$version = Read-Version $settingsFile
if (-not $version) { $version = '0.0.0.0'; Write-Warning 'Version not found, using default' }
Write-Host "Version: $version" -ForegroundColor Cyan

$paths = $null
switch ($BuildType) {
    1 {
        $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
        Create-DesktopShortcut (Join-Path $paths.Portable "$AppName.exe") $version
    }
    2 {
        $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
        $null  = Make-Zip $paths.Portable
        Create-DesktopShortcut (Join-Path $paths.Portable "$AppName.exe") $version
    }
    3 {
        $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
        $null  = Make-Zip $paths.Portable
        $null  = Make-Installer $paths.Portable
        Create-DesktopShortcut (Join-Path $paths.Portable "$AppName.exe") $version
    }
    4 {
        $tmp   = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
        $paths = @{ Base = $tmp.Base; Portable = $null }
        $null  = Make-Zip $tmp.Portable
        Remove-Item -Recurse -Force $tmp.Portable
    }
    5 {
        $tmp   = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
        $paths = @{ Base = $tmp.Base; Portable = $null }
        $null  = Make-Installer $tmp.Portable
        if ($tmp.Portable -and (Test-Path $tmp.Portable)) { Remove-Item -Recurse -Force $tmp.Portable }
    }
}

Write-Host "Done: $($paths.Base)" -ForegroundColor Green

Write-Host "Cleaning source tree..." -ForegroundColor Yellow
Clean-Tree "$AppDir\dist"
Clean-Tree "$AppDir\build"
Write-Host "Clean complete" -ForegroundColor Green

if ($Clean) {
    Get-ChildItem -Path $AppDir -Recurse -Directory -Filter '__pycache__' |
        ForEach-Object { Clean-Tree $_.FullName }
    Get-ChildItem -Path $AppDir -Filter '*.log' -File |
        ForEach-Object { Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue }
}

exit 0
