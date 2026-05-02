# build_all_parallel.ps1 - parallel build helper (Windows PowerShell)
<#
.SYNOPSIS
    Parallel build for the six RPA apps.
.DESCRIPTION
    Launch each app build script in its own PowerShell process and wait for completion.
.PARAMETER BuildType
    Build mode to pass to each app script (1-5).
.PARAMETER PostClean
    Reserved for post-build cleanup (not used yet).
#>

param(
    [int]$BuildType = 2,
    [switch]$PostClean
)

$ErrorActionPreference = 'Stop'

# App metadata (absolute paths to avoid cwd issues)
$Apps = @(
    @{ 
        Name = 'Bom Exporter';
        ShortName = 'be';
        ExeName = 'bom_exporter.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\build_bom_exporter.ps1'
    },
    @{ 
        Name = 'Batch Print';
        ShortName = 'bp';
        ExeName = 'batch_print.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\batch_print\build_batch_print.ps1'
    },
    @{ 
        Name = 'Attribute Reset';
        ShortName = 'ar';
        ExeName = 'attribute_reset.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\attribute_reset\build_attribute_reset.ps1'
    },
    @{ 
        Name = 'DWG Classifier';
        ShortName = 'dc';
        ExeName = 'dwg_classifier.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier\build_dwg_classifier.ps1'
    },
    @{ 
        Name = 'Conversion Verifier';
        ShortName = 'cv';
        ExeName = 'conversion_verifier.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\conversion_verifier\build_conversion_verifier.ps1'
    },
    @{ 
        Name = 'Korean Filename Normalizer';
        ShortName = 'kfn';
        ExeName = 'korean_filename_normalizer.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer\build_korean_filename_normalizer.ps1'
    },
    @{ 
        Name = 'QRCode Generator';
        ShortName = 'qr';
        ExeName = 'qrcode_generator.exe';
        Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\qrcode_generator\build_qrcode_generator.ps1'
    }
)

function Create-DesktopShortcut {
    param(
        [string]$AppName,
        [string]$ExePath,
        [string]$ShortcutName,
        [string]$Description
    )

    $Desktop = [Environment]::GetFolderPath('Desktop')
    $ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"

    if (-not (Test-Path $ExePath)) { return $false }

    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force -ErrorAction SilentlyContinue
    }

    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = Split-Path $ExePath
    $Shortcut.Description = if ($Description) { $Description } else { $AppName }
    $Shortcut.Save()
    
    $DisplayText = if ($Description) { $Description } else { $ShortcutName }
    Write-Host "  OK shortcut c7eated: $DisplayText" -ForegroundColor Green
    return $true
}

$StartTime = Get-Date
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Parallel build for 6 apps (BuildType $BuildType)" -ForegroundColor Cyan
Write-Host "Start time: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$Jobs = @()
foreach ($App in $Apps) {
    Write-Host "[$($App.Name)] starting..." -ForegroundColor Yellow

    if (-not (Test-Path $App.Script)) {
        Write-Host "X build script not found: $($App.Script)" -ForegroundColor Red
        continue
    }

    $LogFile = Join-Path $env:TEMP "$($App.ShortName)_build_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    $ErrorLogFile = Join-Path $env:TEMP "$($App.ShortName)_error_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

    # Use PowerShell 7 (pwsh) or Windows PowerShell with bypass policy
    $psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { 'pwsh' } else { 'powershell.exe' }
    $argList = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $App.Script, '-BuildType', $BuildType)
    if ($PostClean.IsPresent) { $argList += '-PostClean' }
    $Process = Start-Process -FilePath $psExe `
        -ArgumentList $argList `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrorLogFile `
        -PassThru `
        -WindowStyle Minimized

    $Jobs += @{
        Name = $App.Name
        ShortName = $App.ShortName
        ExeName = $App.ExeName
        Process = $Process
        LogFile = $LogFile
        ErrorLogFile = $ErrorLogFile
        StartTime = Get-Date
    }
}

Write-Host "`nParallel build in progress... ($($Jobs.Count) jobs)" -ForegroundColor Cyan
Write-Host "Checking status every 5 seconds...`n" -ForegroundColor Gray

$Results = @()
$Completed = @{}

while ($Jobs.Count -gt $Completed.Count) {
    Start-Sleep -Seconds 5

    foreach ($JobInfo in $Jobs) {
        if ($Completed.ContainsKey($JobInfo.Name)) { continue }

        if ($JobInfo.Process.HasExited) {
            $Duration = (Get-Date) - $JobInfo.StartTime
            $ExitCode = $JobInfo.Process.ExitCode
            
            # Check if build was successful by looking for output files
            # Wait a moment for file system to update
            Start-Sleep -Milliseconds 500
            
            # Map ShortName to actual file name patterns
            $FilePatterns = @{
                'be'  = 'bom_exporter'
                'bp'  = 'batch_print'
                'ar'  = 'attribute_reset'
                'dc'  = 'dwg_classifier'
                'cv'  = 'conversion_verifier'
                'kfn' = 'korean_filename_normalizer'
                'qr'  = 'qrcode_generator'
            }
            $FilePattern = $FilePatterns[$JobInfo.ShortName]
            
            $RecentZips = @(Get-ChildItem "D:\release\candidates" -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { 
                    $_.Name -like "*${FilePattern}*portable.zip" -and
                    $_.LastWriteTime -ge $JobInfo.StartTime.AddSeconds(-5)
                } |
                Sort-Object LastWriteTime -Descending)
            
            $BuildSucceeded = ($RecentZips.Count -gt 0)

            if ($BuildSucceeded) {
                Write-Host "OK [$($JobInfo.Name)] build succeeded (duration: $($Duration.TotalMinutes.ToString('0.0')) min, output: $($RecentZips[0].Name))" -ForegroundColor Green
                $Results += @{ App = $JobInfo.Name; Status = 'success'; Duration = $Duration.TotalMinutes }
            } else {
                Write-Host "X [$($JobInfo.Name)] build failed (Exit Code: $ExitCode)" -ForegroundColor Red
                $Results += @{ App = $JobInfo.Name; Status = 'fail'; Duration = $Duration.TotalMinutes; Error = "Exit Code: $ExitCode" }
            }

            $Completed[$JobInfo.Name] = $true

            if (Test-Path $JobInfo.LogFile) {
                Remove-Item $JobInfo.LogFile -Force -ErrorAction SilentlyContinue
            }
            if (Test-Path $JobInfo.ErrorLogFile) {
                Remove-Item $JobInfo.ErrorLogFile -Force -ErrorAction SilentlyContinue
            }
        } else {
            $Elapsed = ((Get-Date) - $JobInfo.StartTime).TotalMinutes
            if ($Elapsed -gt 30) {
                Write-Host "X [$($JobInfo.Name)] timeout (>30 min) - killing" -ForegroundColor Red
                Stop-Process -Id $JobInfo.Process.Id -Force -ErrorAction SilentlyContinue

                $Results += @{ App = $JobInfo.Name; Status = 'fail'; Duration = 30.0; Error = 'timeout (30 min)' }
                $Completed[$JobInfo.Name] = $true

                if (Test-Path $JobInfo.LogFile) {
                    Remove-Item $JobInfo.LogFile -Force -ErrorAction SilentlyContinue
                }
                if (Test-Path $JobInfo.ErrorLogFile) {
                    Remove-Item $JobInfo.ErrorLogFile -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }

    $InProgress = $Jobs | Where-Object { -not $Completed.ContainsKey($_.Name) }
    if ($InProgress.Count -gt 0) {
        $Elapsed = ((Get-Date) - $StartTime).TotalMinutes
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] in progress: $($InProgress.Count) | elapsed: $([math]::Round($Elapsed,1)) min" -ForegroundColor Gray
    }
}

$EndTime = Get-Date
$TotalDuration = $EndTime - $StartTime

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Parallel build complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "End time: $($EndTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
Write-Host "Total duration: $($TotalDuration.TotalMinutes.ToString('0.0')) min" -ForegroundColor Gray
Write-Host ""

$SuccessCount = ($Results | Where-Object { $_.Status -eq 'success' }).Count
$FailCount = ($Results | Where-Object { $_.Status -eq 'fail' }).Count

foreach ($Result in $Results) {
    $StatusColor = if ($Result.Status -eq 'success') { 'Green' } else { 'Red' }
    $StatusIcon = if ($Result.Status -eq 'success') { 'OK' } else { 'X' }

    Write-Host "$StatusIcon $($Result.App): $($Result.Status) ($($Result.Duration.ToString('0.0')) min)" -ForegroundColor $StatusColor
    if ($Result.Error) {
        Write-Host "  Error: $($Result.Error)" -ForegroundColor Red
    }
}

Write-Host "`nSuccess: $SuccessCount / Fail: $FailCount / Total: $($Results.Count)" -ForegroundColor Cyan

Write-Host "`nPackages created:" -ForegroundColor Cyan
$RecentPackages = Get-ChildItem "D:\release\candidates\*_portable.zip" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $StartTime } |
    Sort-Object LastWriteTime -Descending

if ($RecentPackages.Count -gt 0) {
    $RecentPackages | ForEach-Object {
        $SizeMB = [math]::Round($_.Length / 1MB, 1)
        Write-Host "  - $($_.Name) ($SizeMB MB)" -ForegroundColor Green
    }
} else {
    Write-Host "  (No packages created)" -ForegroundColor Yellow
}

Write-Host "`nCreate desktop shortcuts:" -ForegroundColor Cyan
$Candidates = "D:\release\candidates"
foreach ($App in $Apps) {
    $AppFolderPattern = $App.Name.Replace(' ', '_').ToLower()
    $PortableDirs = Get-ChildItem $Candidates -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*$($AppFolderPattern)*portable" -and $_.Name -notlike "*_internal*" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($PortableDirs) {
        $ExePath = Join-Path $PortableDirs.FullName $App.ExeName
        $Version = 'unknown'
        if ($PortableDirs.Name -match 'v([0-9\.]+)') { $Version = "v$($Matches[1])" }
        $BuiltAt = Get-Date $PortableDirs.LastWriteTime -Format 'yyyy-MM-dd HH:mm'
        $ShortcutDescription = "$($App.Name) | $Version | built $BuiltAt"

        if (Test-Path $ExePath) {
            $null = Create-DesktopShortcut -AppName $App.Name -ExePath $ExePath -ShortcutName $App.Name -Description $ShortcutDescription
        } else {
            Write-Host "  X missing EXE: $($App.Name)" -ForegroundColor Red
        }
    } else {
        Write-Host "  X no portable folder: $($App.Name)" -ForegroundColor Yellow
    }
}

# Calculate parallel benefit
try {
    $DurationSum = 0
    foreach ($r in $Results) {
        if ($r.Duration -ne $null -and $r.Duration -is [System.ValueType]) {
            $DurationSum += $r.Duration
        }
    }
    
    if ($DurationSum -gt 0) {
        $EstimatedSequentialTime = $DurationSum
        $TimeSaved = $EstimatedSequentialTime - $TotalDuration.TotalMinutes
        $SavedPercent = if ($EstimatedSequentialTime -gt 0) { [math]::Round(($TimeSaved / $EstimatedSequentialTime) * 100, 1) } else { 0 }

        Write-Host "`nParallel benefit:" -ForegroundColor Cyan
        Write-Host "  Estimated sequential time: $([math]::Round($EstimatedSequentialTime, 1)) min" -ForegroundColor Gray
        Write-Host "  Actual parallel time: $($TotalDuration.TotalMinutes.ToString('0.0')) min" -ForegroundColor Gray
        Write-Host "  Time saved: $([math]::Round($TimeSaved, 1)) min ($SavedPercent%)" -ForegroundColor Green
    }
} catch {
    # Silently ignore calculation errors
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

exit ($(if ($FailCount -eq 0) { 0 } else { 1 }))
#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the six RPA apps in parallel.
.DESCRIPTION
    Launches each app's build script in its own PowerShell process and waits for completion.
.PARAMETER BuildType
    Build mode to pass through to each app script (1-5).
.PARAMETER PostClean
    Reserved for future post-build cleanup.
#>

param(
    [int]$BuildType = 2,
    [switch]$PostClean
)

$ErrorActionPreference = 'Stop'

# App metadata
$Apps = @(
    @{ Name = 'Bom Exporter'; ShortName = 'be'; ExeName = 'bom_exporter.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\build_bom_exporter.ps1' },
    @{ Name = 'DWG Batch Print'; ShortName = 'dp'; ExeName = 'batch_print.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\batch_print\build_batch_print.ps1' },
    @{ Name = 'Attribute Reset'; ShortName = 'ar'; ExeName = 'attribute_reset.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\30.apps\attribute_reset\build_attribute_reset.ps1' },
    @{ Name = 'DWG Classifier'; ShortName = 'dc'; ExeName = 'dwg_classifier.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\dwg_classifier\build_dwg_classifier.ps1' },
    @{ Name = 'Conversion Verifier'; ShortName = 'cv'; ExeName = 'conversion_verifier.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\conversion_verifier\build_conversion_verifier.ps1' },
    @{ Name = 'Korean Filename Normalizer'; ShortName = 'kfn'; ExeName = 'korean_filename_normalizer.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\korean_filename_normalizer\build_korean_filename_normalizer.ps1' },
    @{ Name = 'QRCode Generator'; ShortName = 'qr'; ExeName = 'qrcode_generator.exe'; Script = 'D:\drive_files\10.worksfree\10.rpa\50.data\qrcode_generator\build_qrcode_generator.ps1' }
)

function Create-DesktopShortcut {
    param(
        [string]$AppName,
        [string]$ExePath,
        [string]$ShortcutName,
        [string]$Description
    )

    $Desktop = [Environment]::GetFolderPath('Desktop')
    $ShortcutPath = Join-Path $Desktop "$ShortcutName.lnk"

    if (-not (Test-Path $ExePath)) { return $false }

    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force -ErrorAction SilentlyContinue
    }

    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = Split-Path $ExePath
    $Shortcut.Description = if ($Description) { $Description } else { $AppName }
    $Shortcut.Save()
    Write-Host "  OK 바탕화면 바로가기 생성: $ShortcutName" -ForegroundColor Green
    return $true
}

$StartTime = Get-Date
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "7개 RPA 앱 병렬 빌드 (BuildType $BuildType)" -ForegroundColor Cyan
Write-Host "시작 시간: $($StartTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$Jobs = @()
foreach ($App in $Apps) {
    Write-Host "[$($App.Name)] 병렬 빌드 시작..." -ForegroundColor Yellow

    if (-not (Test-Path $App.Script)) {
        Write-Host "X 빌드 스크립트를 찾을 수 없습니다: $($App.Script)" -ForegroundColor Red
        continue
    }

    $LogFile = Join-Path $env:TEMP "$($App.ShortName)_build_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

    $Process = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @('-NoLogo', '-NoProfile', '-File', $App.Script, '-BuildType', $BuildType) `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $LogFile `
        -PassThru `
        -WindowStyle Hidden

    $Jobs += @{
        Name = $App.Name
        ShortName = $App.ShortName
        ExeName = $App.ExeName
        Process = $Process
        LogFile = $LogFile
        StartTime = Get-Date
    }
}

Write-Host "`n병렬 빌드 진행 중... ($($Jobs.Count)개 작업)" -ForegroundColor Cyan
Write-Host "진행 상황을 5초마다 확인합니다...`n" -ForegroundColor Gray

$Results = @()
$Completed = @{}

while ($Jobs.Count -gt $Completed.Count) {
    Start-Sleep -Seconds 5

    foreach ($JobInfo in $Jobs) {
        if ($Completed.ContainsKey($JobInfo.Name)) { continue }

        if ($JobInfo.Process.HasExited) {
            $Duration = (Get-Date) - $JobInfo.StartTime
            $ExitCode = $JobInfo.Process.ExitCode

            if ($ExitCode -eq 0) {
                Write-Host "OK [$($JobInfo.Name)] 빌드 성공 (소요시간: $($Duration.TotalMinutes.ToString('0.0'))분)" -ForegroundColor Green
                $Results += @{ App = $JobInfo.Name; Status = '성공'; Duration = $Duration.TotalMinutes }
            } else {
                Write-Host "X [$($JobInfo.Name)] 빌드 실패 (Exit Code: $ExitCode)" -ForegroundColor Red
                $Results += @{ App = $JobInfo.Name; Status = '실패'; Duration = $Duration.TotalMinutes; Error = "Exit Code: $ExitCode" }
            }

            $Completed[$JobInfo.Name] = $true

            if (Test-Path $JobInfo.LogFile) {
                Remove-Item $JobInfo.LogFile -Force -ErrorAction SilentlyContinue
            }
        } else {
            $Elapsed = ((Get-Date) - $JobInfo.StartTime).TotalMinutes
            if ($Elapsed -gt 30) {
                Write-Host "X [$($JobInfo.Name)] 타임아웃 (30분 초과) - 강제 종료" -ForegroundColor Red
                Stop-Process -Id $JobInfo.Process.Id -Force -ErrorAction SilentlyContinue

                $Results += @{ App = $JobInfo.Name; Status = '실패'; Duration = 30.0; Error = '타임아웃 (30분)' }
                $Completed[$JobInfo.Name] = $true

                if (Test-Path $JobInfo.LogFile) {
                    Remove-Item $JobInfo.LogFile -Force -ErrorAction SilentlyContinue
                }                if (Test-Path $JobInfo.ErrorLogFile) {
                    Remove-Item $JobInfo.ErrorLogFile -Force -ErrorAction SilentlyContinue
                }            }
        }
    }

    $InProgress = $Jobs | Where-Object { -not $Completed.ContainsKey($_.Name) }
    if ($InProgress.Count -gt 0) {
        $Elapsed = ((Get-Date) - $StartTime).TotalMinutes
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 진행 중: $($InProgress.Count)개 | 경과: $([math]::Round($Elapsed,1))분" -ForegroundColor Gray
    }
}

$EndTime = Get-Date
$TotalDuration = $EndTime - $StartTime

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "병렬 빌드 완료 - 최종 결과" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "종료 시간: $($EndTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
Write-Host "총 소요시간: $($TotalDuration.TotalMinutes.ToString('0.0'))분 (병렬 처리)" -ForegroundColor Gray
Write-Host ""

$SuccessCount = ($Results | Where-Object { $_.Status -eq '성공' }).Count
$FailCount = ($Results | Where-Object { $_.Status -eq '실패' }).Count

foreach ($Result in $Results) {
    $StatusColor = if ($Result.Status -eq '성공') { 'Green' } else { 'Red' }
    $StatusIcon = if ($Result.Status -eq '성공') { 'OK' } else { 'X' }

    Write-Host "$StatusIcon $($Result.App): $($Result.Status) ($($Result.Duration.ToString('0.0'))분)" -ForegroundColor $StatusColor
    if ($Result.Error) {
        Write-Host "  오류: $($Result.Error)" -ForegroundColor Red
    }
}

Write-Host "`n성공: $SuccessCount / 실패: $FailCount / 전체: $($Results.Count)" -ForegroundColor Cyan

Write-Host "`n생성된 패키지:" -ForegroundColor Cyan
$RecentPackages = Get-ChildItem "D:\release\candidates\*_portable.zip" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $StartTime } |
    Sort-Object LastWriteTime -Descending

if ($RecentPackages.Count -gt 0) {
    $RecentPackages | ForEach-Object {
        $SizeMB = [math]::Round($_.Length / 1MB, 1)
        Write-Host "  - $($_.Name) ($SizeMB MB)" -ForegroundColor Green
    }
} else {
    Write-Host "  (패키지가 생성되지 않았습니다)" -ForegroundColor Yellow
}

Write-Host "`n바탕화면 바로가기 생성:" -ForegroundColor Cyan
$Candidates = "D:\release\candidates"
foreach ($App in $Apps) {
    $AppFolderPattern = $App.Name.Replace(' ', '_').ToLower()
    $PortableDirs = Get-ChildItem $Candidates -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*$($AppFolderPattern)*portable" -and $_.Name -notlike "*_internal*" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($PortableDirs) {
        $ExePath = Join-Path $PortableDirs.FullName $App.ExeName
        $Version = 'unknown'
        if ($PortableDirs.Name -match 'v([0-9\.]+)') { $Version = "v$($Matches[1])" }
        $BuiltAt = Get-Date $PortableDirs.LastWriteTime -Format 'yyyy-MM-dd HH:mm'
        $ShortcutDescription = "$($App.Name) | $Version | built $BuiltAt"

        if (Test-Path $ExePath) {
            Create-DesktopShortcut -AppName $App.Name -ExePath $ExePath -ShortcutName $App.Name -Description $ShortcutDescription | Out-Null
        } else {
            Write-Host "  X EXE 파일 없음: $($App.Name)" -ForegroundColor Red
        }
    } else {
        Write-Host "  X 포터블 폴더 없음: $($App.Name)" -ForegroundColor Yellow
    }
}

$EstimatedSequentialTime = ($Results | Measure-Object -Property Duration -Sum).Sum
$TimeSaved = $EstimatedSequentialTime - $TotalDuration.TotalMinutes
$SavedPercent = if ($EstimatedSequentialTime -gt 0) { [math]::Round(($TimeSaved / $EstimatedSequentialTime) * 100, 1) } else { 0 }

Write-Host "`n병렬 처리 효과:" -ForegroundColor Cyan
Write-Host "  순차 빌드 예상 시간: $([math]::Round($EstimatedSequentialTime, 1))분" -ForegroundColor Gray
Write-Host "  실제 병렬 빌드 시간: $($TotalDuration.TotalMinutes.ToString('0.0'))분" -ForegroundColor Gray
Write-Host "  시간 절감: $([math]::Round($TimeSaved, 1))분 ($SavedPercent%)" -ForegroundColor Green

Write-Host "`n========================================`n" -ForegroundColor Cyan

exit ($(if ($FailCount -eq 0) { 0 } else { 1 }))
