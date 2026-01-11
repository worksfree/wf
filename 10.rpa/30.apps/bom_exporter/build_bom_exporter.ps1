param(
    [object]$Option = 1,  # Option 1: onedir, Option 2: onedir+zip, Option 3: onedir+zip+installer
    [switch]$Clean,  # 빌드 후 build, dist, exe 파일 정리
    [switch]$PostClean # 빌드 성공 후 루트 정리 실행
)

$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

# ===== 경로 문제 원천 차단: 스크립트 위치 기준으로 모든 경로 설정 =====
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "[BUILD] Working directory: $ScriptDir" -ForegroundColor Cyan

$AppName = 'bom_exporter'
$AppDir = $ScriptDir
$SpecFile = Join-Path $AppDir 'bom_exporter.spec'
$Python = 'C:/Users/USER/AppData/Local/Python/pythoncore-3.14-64/python.exe'
$PyInstallerArgs = @('-m','PyInstaller','--noconfirm','--log-level=ERROR', $SpecFile)
$Candidates = 'D:\release\candidates'
$script:VerifyScript = Join-Path $AppDir '..\..\scripts\verify_package_integrity.ps1'
$script:ReleasePath = $null  # 릴리스 패키지 경로 (빌드 후 설정)

function Get-Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }
function Clean-Tree($p){ if(Test-Path $p){ Remove-Item -Recurse -Force -LiteralPath $p -ErrorAction SilentlyContinue } }
function Ensure-Dir($p){ if(!(Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }
function Read-Version($settingsJson){
    if(!(Test-Path $settingsJson)){ return $null }
    try{ (Get-Content $settingsJson -Raw | ConvertFrom-Json).runtime_config.full_version } catch { $null }
}
function Build-Onedir{
    Write-Host "==> PyInstaller onedir 빌드" -ForegroundColor Yellow
    
    # 외부 패키저 사용 플래그로 spec 내부 post 처리 차단
    $env:WF_EXTERNAL_PACKAGER = '1'
    
    # dist/build 폴더 안전 정리
    $distPath = Join-Path $AppDir 'dist'
    $buildPath = Join-Path $AppDir 'build'
    if ((Test-Path $distPath) -or (Test-Path $buildPath)) {
        Write-Host "   dist/build 폴더 정리 중..." -ForegroundColor Gray
        # 관련 프로세스 종료
        Get-Process | Where-Object {$_.Path -like "*$AppName*"} | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        # 삭제 시도
        for ($i = 0; $i -lt 3; $i++) {
            Remove-Item $distPath -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item $buildPath -Recurse -Force -ErrorAction SilentlyContinue
            if (!(Test-Path $distPath) -and !(Test-Path $buildPath)) { break }
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Seconds 1
    }
    
    # PyInstaller 캐시 정리
    Clean-Tree "$env:LOCALAPPDATA\pyinstaller"
    $p = Start-Process -FilePath $Python -ArgumentList $PyInstallerArgs -Wait -PassThru -NoNewWindow
    if($p.ExitCode -ne 0){ throw "PyInstaller failed ($($p.ExitCode))" }
    if(!(Test-Path "$AppDir\dist\$AppName")){ throw 'dist output missing' }
    return "$AppDir\dist\$AppName"
}
function Copy-Portable($src,$targetRoot,$version){
    $base = Join-Path $targetRoot "${AppName}_${version}"
    $portable = Join-Path $base "${AppName}_${version}_portable"
    Ensure-Dir $base
    if(Test-Path $portable){ Remove-Item -Recurse -Force $portable }
    Copy-Item -Recurse -Force -LiteralPath $src -Destination $portable
    
    # 공용 바탕화면 바로가기 생성 스크립트 복사
    $commonScriptSrc = Join-Path $PSScriptRoot '..\..\10.common\create_desktop_shortcut.bat'
    if (Test-Path $commonScriptSrc) {
        $scriptDest = Join-Path $portable 'create_desktop_shortcut.bat'
        Copy-Item -Path $commonScriptSrc -Destination $scriptDest -Force
        Write-Host "✓ 바로가기 생성 스크립트 포함: create_desktop_shortcut.bat" -ForegroundColor Green
    } else {
        Write-Host "⚠️  공용 스크립트 없음: $commonScriptSrc" -ForegroundColor Yellow
    }
    
    return @{ Base=$base; Portable=$portable }
}
function Make-Zip($portablePath){
    $zip = Join-Path ([System.IO.Path]::GetDirectoryName($portablePath)) ("${AppName}_" + (Split-Path $portablePath -Leaf).Split('_')[-2] + '_portable.zip')
    if(Test-Path $zip){ Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $portablePath '*') -DestinationPath $zip -Force
    return $zip
}
function Create-DesktopShortcut {
    param(
        [string]$ExePath,
        [string]$AppDisplayName,
        [string]$Version
    )
    
    try {
        $desktop = [Environment]::GetFolderPath("Desktop")
        $shortcutPath = Join-Path $desktop "$AppDisplayName.lnk"
        
        # 기존 바로가기 확인 및 알림
        if (Test-Path $shortcutPath) {
            try {
                $existingShortcut = New-Object -ComObject WScript.Shell
                $existing = $existingShortcut.CreateShortcut($shortcutPath)
                $oldDesc = $existing.Description
                
                Write-Host "⚠️  기존 바로가기 발견: $shortcutPath" -ForegroundColor Yellow
                if ($oldDesc) {
                    Write-Host "   이전 정보: $oldDesc" -ForegroundColor Gray
                }
                Write-Host "   → 새 버전으로 대체합니다 (v$Version)" -ForegroundColor Cyan
            } catch {
                Write-Host "⚠️  기존 바로가기 발견 (정보 읽기 실패)" -ForegroundColor Yellow
            }
        }
        
        # 새 바로가기 생성
        $WScriptShell = New-Object -ComObject WScript.Shell
        $shortcut = $WScriptShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $ExePath
        $shortcut.WorkingDirectory = Split-Path $ExePath
        $shortcut.IconLocation = $ExePath
        
        # 빌드 정보를 Description에 저장 (마우스 오버 시 표시)
        $buildTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $shortcut.Description = "$AppDisplayName v$Version (빌드: $buildTime)"
        
        $shortcut.Save()
        
        Write-Host "✅ 바탕화면 바로가기 생성 완료" -ForegroundColor Green
        Write-Host "   위치: $shortcutPath" -ForegroundColor Gray
        Write-Host "   버전: v$Version" -ForegroundColor Gray
        Write-Host "   💡 바로가기에 마우스를 올리면 버전 정보가 표시됩니다" -ForegroundColor Cyan
    }
    catch {
        Write-Host "`n========================================" -ForegroundColor Red
        Write-Host "🚨 경고: 바탕화면 바로가기 생성 실패" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "앱: $AppDisplayName v$Version" -ForegroundColor Yellow
        Write-Host "오류: $_" -ForegroundColor Yellow
        Write-Host "빌드는 정상 완료, 바로가기 미생성" -ForegroundColor Gray
        Write-Host "테스트 시 수동 생성 필요" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Red
        $buildBase = Split-Path $ExePath -Parent
        $logPath = Join-Path (Split-Path $buildBase -Parent) "SHORTCUT_CREATION_FAILED.txt"
        "바탕화면 바로가기 생성 실패`n앱: $AppDisplayName v$Version`n시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n오류: $_`nEXE: $ExePath`n`n빌드 정상, 바로가기 미생성. 수동 생성 필요." | Out-File -FilePath $logPath -Encoding UTF8 -Force
        Write-Host "📄 실패 로그: $logPath" -ForegroundColor Magenta
    }
}

function Make-Installer($portablePath){
    $nsis = 'C:\Program Files (x86)\NSIS\makensis.exe'
    if(!(Test-Path $nsis)){ Write-Warning 'NSIS not found; skip installer'; return $null }
    $base = Split-Path $portablePath -Parent
    $ver = ($portablePath | Split-Path -Leaf).Replace("${AppName}_",'').Replace('_portable','')
    $nsiPath = Join-Path $AppDir "${AppName}_installer.nsi"
    $outFile = "${AppName}_${ver}_installer.exe"
    $script = @"
!include "MUI2.nsh"
Name "BOM2Excel v$ver"
OutFile "$outFile"
InstallDir "`$PROGRAMFILES64\WorksFree\${AppName}"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "`$INSTDIR"
  File /r "${portablePath}\*.*"
  WriteUninstaller "`$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "`$INSTDIR"
SectionEnd
"@
    $script | Out-File -FilePath $nsiPath -Encoding UTF8
    Push-Location $AppDir
    try{
        $r = Start-Process -FilePath $nsis -ArgumentList ("/V2", $nsiPath) -PassThru -Wait -NoNewWindow
        if($r.ExitCode -ne 0){ throw "NSIS failed ($($r.ExitCode))" }
        $exe = Join-Path $AppDir $outFile
        if(Test-Path $exe){ Move-Item -Force $exe -Destination $base; return (Join-Path $base $outFile) }
        return $null
    } finally { Pop-Location }
}

# post-clean: on success, optionally run root cleanup script
if ($PostClean.IsPresent) {
  $cleanup = Join-Path (Split-Path (Split-Path $AppDir -Parent) -Parent) 'cleanup_build_artifacts.ps1'
  if (Test-Path $cleanup) { & $cleanup }
}

Write-Host "==== ${AppName} 패키징(Build Option=$Option) 시작 ====" -ForegroundColor Cyan
Ensure-Dir $Candidates

# 1) 빌드 (onedir 필요 여부)
$needOnedir = $true
switch($Option){ 1 { } 2 { } 3 { } 4 { } 5 { } default { $Option = 1 } }

$distPath = Build-Onedir
$version = Read-Version (Join-Path $AppDir 'config\bom_exporter\settings.json')
if(-not $version){ $version = '0.0.0.0' }

# 2) 결과 복사/압축/인스톨러
$paths = $null
switch($Option){
  1 { 
    $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
    $exePath = Join-Path $paths.Portable "$AppName.exe"
    if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Bom Exporter" -Version $version }
  }
  2 { 
    $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
    $null = Make-Zip $paths.Portable
    $exePath = Join-Path $paths.Portable "$AppName.exe"
    if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Bom Exporter" -Version $version }
  }
  3 { 
    $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version
    $null = Make-Zip $paths.Portable
    $null = Make-Installer $paths.Portable
    $exePath = Join-Path $paths.Portable "$AppName.exe"
    if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Bom Exporter" -Version $version }
  }
  4 { $tmp = Copy-Portable -src $distPath -targetRoot $Candidates -version $version; $paths = @{ Base=$tmp.Base; Portable=$null }; $zip = Make-Zip $tmp.Portable; Remove-Item -Recurse -Force $tmp.Portable }
  5 { $tmp = Copy-Portable -src $distPath -targetRoot $Candidates -version $version; $paths = @{ Base=$tmp.Base; Portable=$null }; $exe = Make-Installer $tmp.Portable; if($tmp.Portable -and (Test-Path $tmp.Portable)){ Remove-Item -Recurse -Force $tmp.Portable } }
  default { $paths = Copy-Portable -src $distPath -targetRoot $Candidates -version $version }
}

Write-Host "완료: $($paths.Base)" -ForegroundColor Green

# 릴리스 경로 저장 (무결성 검증용)
$script:ReleasePath = $paths.Base

# 3) Clean 모드: 빌드 산출물 정리
if($Clean){
    Write-Host "`n==> 빌드 산출물 정리 중..." -ForegroundColor Yellow
    
    # build, dist 폴더 삭제
    Clean-Tree "$AppDir\build"
    Clean-Tree "$AppDir\dist"
    
    # exe 파일 삭제 (루트의 실행 파일)
    $exeFiles = Get-ChildItem -Path $AppDir -Filter "*.exe" -File
    foreach($exe in $exeFiles){
        Remove-Item -Force $exe.FullName -ErrorAction SilentlyContinue
        Write-Host "   삭제: $($exe.Name)" -ForegroundColor Gray
    }
    
    # 임시 빌드 폴더
    Clean-Tree "$AppDir\build\user_home_bundle"
    
    # __pycache__ 폴더
    Get-ChildItem -Path $AppDir -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
        Clean-Tree $_.FullName
    }
    
    # .log 파일
    Get-ChildItem -Path $AppDir -Filter "*.log" -File | ForEach-Object {
        Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue
    }
    
    # .spec.backup 파일
    Get-ChildItem -Path $AppDir -Filter "*.spec.backup*" -File | ForEach-Object {
        Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue
    }
    
    Write-Host "   정리 완료!" -ForegroundColor Green
}

# ============================================================
# 패키지 무결성 검증 (릴리스 모드만)
# ============================================================
if ($Mode -eq 2 -and (Test-Path $script:VerifyScript)) {
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "   패키지 무결성 검증 실행" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    try {
        & $script:VerifyScript -PackagePath $script:ReleasePath
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ 무결성 검증 통과" -ForegroundColor Green
        } else {
            Write-Host "`n❌ 무결성 검증 실패 (종료 코드: $LASTEXITCODE)" -ForegroundColor Red
            Write-Host "배포를 중단하고 문제를 해결하세요." -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "`n⚠️  무결성 검증 스크립트 실행 중 오류: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "검증을 건너뛰고 계속합니다..." -ForegroundColor Gray
    }
} elseif ($Option -eq 2) {
    Write-Host "`n⚠️  무결성 검증 스크립트를 찾을 수 없습니다: $script:VerifyScript" -ForegroundColor Yellow
}

exit 0
