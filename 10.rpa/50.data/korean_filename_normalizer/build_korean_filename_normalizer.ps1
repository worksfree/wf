param(
    [object]$BuildType = 2,  # Option 1: onedir, Option 2: onedir+zip, Option 3: onedir+zip+installer
    [switch]$Clean,  # 빌드 후 build, dist, exe 파일 정리
    [switch]$PostClean # 빌드 성공 후 루트 정리 실행
)

# Workaround: coerce $BuildType array -> int if necessary
if ($BuildType -is [System.Object[]]) {
    try { $BuildType = [int]($BuildType -join '') } catch { }
}

$ErrorActionPreference = 'Stop'
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

$AppName = 'korean_filename_normalizer'
$AppDir = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer'
$SpecFile = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer\korean_filename_normalizer.spec'
$Python = 'python'
$PyInstallerArgs = @('-m','PyInstaller','--noconfirm','--log-level=ERROR', $SpecFile)
$Candidates = 'D:\release\candidates'
$script:VerifyScript = 'D:\drive_files\10.worksfree\10.rpa\scripts\verify_package_integrity.ps1'
$script:ReleasePath = $null

function Get-Timestamp { (Get-Date).ToString('yyyyMMdd_HHmmss') }
function Clean-Tree($p){ if(Test-Path $p){ Remove-Item -Recurse -Force -LiteralPath $p -ErrorAction SilentlyContinue } }
function Ensure-Dir($p){ if(!(Test-Path $p)){ New-Item -ItemType Directory -Path $p | Out-Null } }
function Read-Version($settingsJson){ if(!(Test-Path $settingsJson)){ return $null } try{ (Get-Content $settingsJson -Raw | ConvertFrom-Json).runtime_config.full_version } catch { $null } }
function Build-Onedir{ 
    Push-Location $AppDir
    try{ 
        $env:WF_EXTERNAL_PACKAGER='1'
        
        # dist/build 폴더 안전 정리
        $distPath = Join-Path $AppDir 'dist'
        $buildPath = Join-Path $AppDir 'build'
        if ((Test-Path $distPath) -or (Test-Path $buildPath)) {
            Get-Process | Where-Object {$_.Path -like "*$AppName*"} | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
            for ($i = 0; $i -lt 3; $i++) {
                Remove-Item $distPath -Recurse -Force -ErrorAction SilentlyContinue
                Remove-Item $buildPath -Recurse -Force -ErrorAction SilentlyContinue
                if (!(Test-Path $distPath) -and !(Test-Path $buildPath)) { break }
                Start-Sleep -Milliseconds 500
            }
            Start-Sleep -Seconds 1
        }
        
        Clean-Tree "$env:LOCALAPPDATA\pyinstaller"
        
        # PyInstaller 실행
        & $Python @PyInstallerArgs
        if($LASTEXITCODE -ne 0){ throw "PyInstaller failed ($LASTEXITCODE)" }
        if(!(Test-Path "$AppDir\dist\$AppName")){ throw 'dist missing' }
        
        # 🔄 빌드 후 크레딧 및 사용자 정보 초기화 (포터블 버전에서는 불필요하므로 주석 처리)
        # Write-Host "`n==> 배포용 초기 상태 설정 중..." -ForegroundColor Cyan
        
        # $distWfRpa = Join-Path "$AppDir\dist\$AppName" ".wf_rpa"
        # $distAppDir = Join-Path $distWfRpa $AppName
        
        # # .wf_rpa/app_name 폴더 생성
        # Ensure-Dir $distWfRpa
        # Ensure-Dir $distAppDir
        
        # # 템플릿 경로
        # $templateDir = Join-Path $AppDir ".build_templates"
        # $creditTemplate = Join-Path $templateDir "credit_history.template.json"
        # $configTemplate = Join-Path $templateDir "wf_rpa_config.template.json"
        # $settingsTemplate = Join-Path $templateDir "settings.template.json"
        
        # # credit_history.json 초기화 (앱별 디렉토리)
        # if(Test-Path $creditTemplate){
        #     $targetCredit = Join-Path $distAppDir "credit_history.json"
        #     Copy-Item -Force $creditTemplate -Destination $targetCredit
        #     Write-Host "   ✓ credit_history.json 초기화 완료" -ForegroundColor Green
        # } else {
        #     Write-Warning "   ⚠ credit_history 템플릿 없음: $creditTemplate"
        # }
        
        # # wf_rpa_config.json 초기화 (루트)
        # if(Test-Path $configTemplate){
        #     $targetConfig = Join-Path $distWfRpa "wf_rpa_config.json"
        #     Copy-Item -Force $configTemplate -Destination $targetConfig
        #     Write-Host "   ✓ wf_rpa_config.json 초기화 완료" -ForegroundColor Green
        # } else {
        #     Write-Warning "   ⚠ wf_rpa_config 템플릿 없음: $configTemplate"
        # }
        
        # # settings.json 초기화 (앱별 디렉토리)
        # if(Test-Path $settingsTemplate){
        #     $targetSettings = Join-Path $distAppDir "settings.json"
        #     Copy-Item -Force $settingsTemplate -Destination $targetSettings
        #     Write-Host "   ✓ settings.json 초기화 완료" -ForegroundColor Green
        # } else {
        #     Write-Warning "   ⚠ settings 템플릿 없음: $settingsTemplate"
        # }
        
        # # 런타임 생성 파일 및 레거시 파일 제거 (있으면)
        # $filesToRemove = @(
        #     (Join-Path $distAppDir "credit_policy.json"),
        #     (Join-Path $distAppDir "app_policy.json"),
        #     (Join-Path $distAppDir "admin_config.json"),
        #     (Join-Path $distAppDir "credit_purchase_log_sync_state.json"),
        #     (Join-Path $distAppDir "credit_usage_log.json"),
        #     (Join-Path $distAppDir "user_data.json")
        # )
        
        # foreach($file in $filesToRemove){
        #     if(Test-Path $file){
        #         Remove-Item -Force $file
        #         Write-Host "   ✓ 제거: $(Split-Path $file -Leaf)" -ForegroundColor Gray
        #     }
        # }
        
        Write-Host "   배포 초기화 완료!`n" -ForegroundColor Green
        
        "$AppDir\dist\$AppName"
    } finally { 
        Pop-Location 
    } 
}
function Copy-Portable($src,$targetRoot,$version){ $base=Join-Path $targetRoot "${AppName}_${version}"; $portable=Join-Path $base "${AppName}_${version}_portable"; Ensure-Dir $base; if(Test-Path $portable){ Remove-Item -Recurse -Force $portable }; Copy-Item -Recurse -Force -LiteralPath $src -Destination $portable; $commonDir = Join-Path $PSScriptRoot '..\..\10.common'; $batFiles = @('setup_worksfree.bat','바로가기_생성.bat','설정_초기화.bat','전체_초기화.bat','등록정보_동기화.bat','제거.bat'); foreach ($batFile in $batFiles) { $srcPath = Join-Path $commonDir $batFile; if (Test-Path $srcPath) { Copy-Item -Path $srcPath -Destination $portable -Force } }; Write-Host "✓ 설정 스크립트 포함: setup_worksfree.bat 외 $(($batFiles.Count - 1))개" -ForegroundColor Green; $manualPdf = Get-ChildItem -Path $AppDir -Filter "*USER_MANUAL.pdf" -File -ErrorAction SilentlyContinue | Select-Object -First 1; if ($manualPdf) { Copy-Item -Path $manualPdf.FullName -Destination $portable -Force; Write-Host "✓ 매뉴얼 포함: $($manualPdf.Name)" -ForegroundColor Green }; @{ Base=$base; Portable=$portable } }
function Make-Zip($portable){ $zip = Join-Path ([System.IO.Path]::GetDirectoryName($portable)) ("${AppName}_" + (Split-Path $portable -Leaf).Split('_')[-2] + '_portable.zip'); if(Test-Path $zip){ Remove-Item $zip -Force }; Compress-Archive -Path (Join-Path $portable '*') -DestinationPath $zip -Force; $zip }
function Create-DesktopShortcut { param([string]$ExePath,[string]$AppDisplayName,[string]$Version); try { $desktop = [Environment]::GetFolderPath("Desktop"); $shortcutPath = Join-Path $desktop "$AppDisplayName.lnk"; if (Test-Path $shortcutPath) { try { $existingShortcut = New-Object -ComObject WScript.Shell; $existing = $existingShortcut.CreateShortcut($shortcutPath); $oldDesc = $existing.Description; Write-Host "⚠️  기존 바로가기 발견: $shortcutPath" -ForegroundColor Yellow; if ($oldDesc) { Write-Host "   이전 정보: $oldDesc" -ForegroundColor Gray }; Write-Host "   → 새 버전으로 대체합니다 (v$Version)" -ForegroundColor Cyan } catch { Write-Host "⚠️  기존 바로가기 발견" -ForegroundColor Yellow } }; $WScriptShell = New-Object -ComObject WScript.Shell; $shortcut = $WScriptShell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $ExePath; $shortcut.WorkingDirectory = Split-Path $ExePath; $shortcut.IconLocation = $ExePath; $buildTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; $shortcut.Description = "$AppDisplayName v$Version (빌드: $buildTime)"; $shortcut.Save(); Write-Host "✅ 바탕화면 바로가기 생성 완료" -ForegroundColor Green; Write-Host "   위치: $shortcutPath" -ForegroundColor Gray; Write-Host "   버전: v$Version" -ForegroundColor Gray; Write-Host "   💡 바로가기에 마우스를 올리면 버전 정보가 표시됩니다" -ForegroundColor Cyan } catch { Write-Host "`n========================================" -ForegroundColor Red; Write-Host "🚨 경고: 바탕화면 바로가기 생성 실패" -ForegroundColor Red; Write-Host "========================================" -ForegroundColor Red; Write-Host "앱: $AppDisplayName v$Version" -ForegroundColor Yellow; Write-Host "오류: $_" -ForegroundColor Yellow; Write-Host "빌드는 정상 완료, 바로가기 미생성" -ForegroundColor Gray; Write-Host "테스트 시 수동 생성 필요" -ForegroundColor Cyan; Write-Host "========================================`n" -ForegroundColor Red; $buildBase = Split-Path $ExePath -Parent; $logPath = Join-Path (Split-Path $buildBase -Parent) "SHORTCUT_CREATION_FAILED.txt"; "바탕화면 바로가기 생성 실패`n앱: $AppDisplayName v$Version`n시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n오류: $_`nEXE: $ExePath`n`n빌드 정상, 바로가기 미생성. 수동 생성 필요." | Out-File -FilePath $logPath -Encoding UTF8 -Force; Write-Host "📄 실패 로그: $logPath" -ForegroundColor Magenta } }
function Make-Installer($portable){ $nsis='C:\Program Files (x86)\NSIS\makensis.exe'; if(!(Test-Path $nsis)){ Write-Warning 'NSIS not found; skip installer'; return $null }; $base=Split-Path $portable -Parent; $ver=(Split-Path $portable -Leaf).Replace("${AppName}_",'').Replace('_portable',''); $nsi=Join-Path $AppDir "${AppName}_installer.nsi"; $outFile="${AppName}_${ver}_installer.exe"; @"
!include "MUI2.nsh"
Name "Korean Filename Normalizer v$ver"
OutFile "$outFile"
InstallDir "`$PROGRAMFILES64\WorksFree\${AppName}"
RequestExecutionLevel admin
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Korean"
Section
  SetOutPath "`$INSTDIR"
  File /r "${portable}\*.*"
  WriteUninstaller "`$INSTDIR\uninstall.exe"
SectionEnd
Section "Uninstall"
  RMDir /r "`$INSTDIR"
SectionEnd
"@ | Out-File -FilePath $nsi -Encoding UTF8; Push-Location $AppDir; try{ $r=Start-Process -FilePath $nsis -ArgumentList "/V2", $nsi -Wait -PassThru -NoNewWindow; if($r.ExitCode -ne 0){ throw "NSIS failed ($($r.ExitCode))" }; $exe=Join-Path $AppDir $outFile; if(Test-Path $exe){ Move-Item -Force $exe -Destination $base; return (Join-Path $base $outFile) } $null } finally { Pop-Location } }

Ensure-Dir $Candidates
$dist = Build-Onedir

# 버전 읽기: PyInstaller 빌드 후 생성된 settings.json에서 읽음
$versionPaths = @(
    (Join-Path $AppDir "build\user_home_bundle\.wf_rpa\$AppName\settings.json"),
    (Join-Path $AppDir "dist\$AppName\_internal\.wf_rpa\$AppName\settings.json")
)
$ver = $null
foreach ($vp in $versionPaths) {
    if (Test-Path $vp) {
        $ver = Read-Version $vp
        if ($ver) {
            Write-Host "   버전 확인: $ver (from $vp)" -ForegroundColor Gray
            break
        }
    }
}
if(-not $ver){ $ver='0.0.0.0'; Write-Host "   버전 정보 없음, 기본값 사용: $ver" -ForegroundColor Yellow }

$paths = $null
switch($BuildType){
  1 { $paths = Copy-Portable -src $dist -targetRoot $Candidates -version $ver; $exePath = Join-Path $paths.Portable "$AppName.exe"; if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Korean Filename Normalizer" -Version $ver } }
  2 { $paths = Copy-Portable -src $dist -targetRoot $Candidates -version $ver; $null = Make-Zip $paths.Portable; $exePath = Join-Path $paths.Portable "$AppName.exe"; if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Korean Filename Normalizer" -Version $ver } }
  3 { $paths = Copy-Portable -src $dist -targetRoot $Candidates -version $ver; $null = Make-Zip $paths.Portable; $null = Make-Installer $paths.Portable; $exePath = Join-Path $paths.Portable "$AppName.exe"; if (Test-Path $exePath) { Create-DesktopShortcut -ExePath $exePath -AppDisplayName "Korean Filename Normalizer" -Version $ver } }
  4 { $tmp = Copy-Portable -src $dist -targetRoot $Candidates -version $ver; $paths = @{ Base=$tmp.Base; Portable=$null }; $zip = Make-Zip $tmp.Portable; Remove-Item -Recurse -Force $tmp.Portable }
  5 { $tmp = Copy-Portable -src $dist -targetRoot $Candidates -version $ver; $paths = @{ Base=$tmp.Base; Portable=$null }; $exe = Make-Installer $tmp.Portable; Remove-Item -Recurse -Force $tmp.Portable }
  default { $paths = Copy-Portable -src $dist -targetRoot $Candidates -version $ver }
}
Write-Host "완료: $($paths.Base)" -ForegroundColor Green

# 릴리스 경로 저장 (무결성 검증용)
$script:ReleasePath = $paths.Base

# 빌드 완료 후 dist/build 폴더 항상 정리 (소스트리 정리)
Write-Host "`n==> 소스트리 정리 (dist/build 폴더 삭제)..." -ForegroundColor Yellow
Clean-Tree "$AppDir\dist"
Clean-Tree "$AppDir\build"
Write-Host "   소스트리 정리 완료!" -ForegroundColor Green

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

# post-clean: on success, optionally run root cleanup script
if ($PostClean.IsPresent) {
    $cleanup = Join-Path (Split-Path $AppDir -Parent -Parent) 'cleanup_build_artifacts.ps1'
    if (Test-Path $cleanup) { & $cleanup }
}

# ============================================================
# 패키지 무결성 검증 (릴리스 모드만)
# ============================================================
if ($BuildType -eq 2 -and (Test-Path $script:VerifyScript)) {
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
} elseif ($BuildType -eq 2) {
    Write-Host "`n⚠️  무결성 검증 스크립트를 찾을 수 없습니다: $script:VerifyScript" -ForegroundColor Yellow
}

exit 0
