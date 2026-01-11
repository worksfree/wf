# 앱 로딩 시간 측정 스크립트
# 사용법: .\test_loading_time.ps1

param(
    [int]$Iterations = 3
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "⏱️  WorksFree 앱 로딩 시간 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "테스트 반복 횟수: $Iterations 회`n" -ForegroundColor Yellow

# 최신 빌드 찾기 함수
function Find-LatestBuild {
    param([string]$Pattern, [string]$ExeName)
    
    $candidates = Get-ChildItem "D:\release\candidates" -Filter $Pattern -Directory | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 1
    
    if ($candidates) {
        $exePath = Get-ChildItem $candidates.FullName -Recurse -Filter $ExeName | 
            Select-Object -First 1
        return $exePath.FullName
    }
    return $null
}

# 테스트할 앱들 - 최신 빌드 자동 탐색
$apps = @(
    @{
        Name = "Bom Exporter"
        ExePath = Find-LatestBuild "bom2excel*" "bom2excel.exe"
    },
    @{
        Name = "Conversion Verifier"
        ExePath = Find-LatestBuild "conversion_verifier*" "conversion_verifier.exe"
    },
    @{
        Name = "DWG Classifier"
        ExePath = Find-LatestBuild "dwg_classifier*" "dwg_classifier.exe"
    },
    @{
        Name = "Korean Filename Normalizer"
        ExePath = Find-LatestBuild "korean_filename_normalizer*" "korean_filename_normalizer.exe"
    }
)

$results = @()

foreach ($app in $apps) {
    if (-not $app.ExePath -or -not (Test-Path $app.ExePath)) {
        Write-Host "⚠️  $($app.Name) 실행 파일을 찾을 수 없습니다: $($app.ExePath)" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "🔍 $($app.Name) 테스트" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "경로: $($app.ExePath)`n" -ForegroundColor Gray
    
    $times = @()
    
    for ($i = 1; $i -le $Iterations; $i++) {
        Write-Host "[$i/$Iterations] 시작..." -NoNewline
        
        # 프로세스 시작 시간 측정
        $startTime = Get-Date
        
        try {
            # 프로세스 시작 (UI 표시 대기)
            $process = Start-Process -FilePath $app.ExePath -PassThru -WindowStyle Minimized
            
            # UI가 응답할 때까지 대기 (최대 10초)
            $timeout = 10
            $elapsed = 0
            $checkInterval = 0.05
            
            while ($elapsed -lt $timeout) {
                Start-Sleep -Milliseconds ($checkInterval * 1000)
                $elapsed += $checkInterval
                
                # 프로세스가 종료되었으면 중단
                if ($process.HasExited) {
                    break
                }
                
                # MainWindowHandle이 생성되면 로딩 완료로 간주
                $process.Refresh()
                if ($process.MainWindowHandle -ne 0) {
                    break
                }
            }
            
            $endTime = Get-Date
            $loadTime = ($endTime - $startTime).TotalSeconds
            
            # 프로세스 종료
            if (-not $process.HasExited) {
                $process.Kill()
                $process.WaitForExit(2000)
            }
            
            $times += $loadTime
            
            # 색상 결정
            $color = if ($loadTime -le 1) { "Green" } 
                    elseif ($loadTime -le 2) { "Yellow" }
                    elseif ($loadTime -le 3) { "DarkYellow" }
                    else { "Red" }
            
            Write-Host " $([math]::Round($loadTime, 2))초" -ForegroundColor $color
            
            # 다음 테스트 전 대기
            if ($i -lt $Iterations) {
                Start-Sleep -Milliseconds 500
            }
            
        } catch {
            Write-Host " 실패: $_" -ForegroundColor Red
        }
    }
    
    if ($times.Count -gt 0) {
        $avgTime = ($times | Measure-Object -Average).Average
        $minTime = ($times | Measure-Object -Minimum).Minimum
        $maxTime = ($times | Measure-Object -Maximum).Maximum
        
        Write-Host "`n📊 통계:" -ForegroundColor Cyan
        Write-Host "  평균: $([math]::Round($avgTime, 2))초" -ForegroundColor $(
            if ($avgTime -le 1) { "Green" } 
            elseif ($avgTime -le 2) { "Yellow" }
            elseif ($avgTime -le 3) { "DarkYellow" }
            else { "Red" }
        )
        Write-Host "  최소: $([math]::Round($minTime, 2))초" -ForegroundColor Gray
        Write-Host "  최대: $([math]::Round($maxTime, 2))초" -ForegroundColor Gray
        
        $results += @{
            Name = $app.Name
            Average = $avgTime
            Min = $minTime
            Max = $maxTime
            Pass = $avgTime -le 3
        }
    }
}

# 최종 결과 요약
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "📊 최종 결과 요약" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$passCount = ($results | Where-Object { $_.Pass }).Count
$totalCount = $results.Count

foreach ($result in $results) {
    $status = if ($result.Pass) { "✅ PASS" } else { "❌ FAIL" }
    $statusColor = if ($result.Pass) { "Green" } else { "Red" }
    
    Write-Host "`n$($result.Name):" -ForegroundColor White
    Write-Host "  평균 로딩 시간: $([math]::Round($result.Average, 2))초" -ForegroundColor Cyan
    Write-Host "  목표(3초 이내): $status" -ForegroundColor $statusColor
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "전체 결과: $passCount / $totalCount 통과" -ForegroundColor $(
    if ($passCount -eq $totalCount) { "Green" } else { "Yellow" }
)
Write-Host "============================================================`n" -ForegroundColor Cyan
