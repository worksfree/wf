#!/usr/bin/env pwsh
<#
.SYNOPSIS
    배포 환경 폴더 구조 설정 및 숨김 속성 적용 스크립트

.DESCRIPTION
    사용자 홈폴더 ~/.wf_rpa 아래 배포 환경 구조를 생성하고
    모든 JSON 설정파일과 폴더에 Windows 숨김 속성을 적용합니다.

.EXAMPLE
    .\setup_deployment_structure.ps1
#>

param(
    [switch]$SkipHidden  # 숨김 속성 적용 건너뛰기 (테스트용)
)

$ErrorActionPreference = 'Stop'

# ==================== 배포 폴더 구조 정의 ====================
$DeploymentRoot = Join-Path $env:USERPROFILE '.wf_rpa'

$FolderStructure = @{
    # 전역 설정
    '' = @{
        Files = @('wf_global_settings.json')
        Hidden = $true
    }
    
    # BOM Exporter (be)
    'bom_exporter' = @{
        SubFolders = @('config', 'logs', 'res/fhd', 'res/qhd', 'res/uhd')
        Files = @('config/credits.json', 'config/settings.json', 'config/dev_credits.json', 'config/dev_settings.json', 'config/dev_wf_global_settings.json')
        Hidden = $true
    }
    
    # DWG Batch Print (dp)
    'dwg_batch_print' = @{
        SubFolders = @('config', 'logs', 'res/fhd', 'res/qhd', 'res/uhd')
        Files = @('config/credits.json', 'config/settings.json')
        Hidden = $true
    }
    
    # DWG Classifier (dc)
    'dwg_classifier' = @{
        SubFolders = @('config', 'logs', 'res/fhd', 'res/qhd', 'res/uhd')
        Files = @('config/credits.json', 'config/settings.json')
        Hidden = $true
    }
    
    # Conversion Verifier (cv)
    'conversion_verifier' = @{
        SubFolders = @('config', 'logs', 'res/fhd', 'res/qhd', 'res/uhd')
        Files = @('config/credits.json', 'config/settings.json')
        Hidden = $true
    }
    
    # Korean Filename Normalizer (kfn)
    'korean_filename_normalizer' = @{
        SubFolders = @('config', 'logs')
        Files = @('config/credits.json', 'config/settings.json')
        Hidden = $true
    }
}

# ==================== 유틸리티 함수 ====================

function Set-Hidden {
    param(
        [string]$Path,
        [bool]$IsHidden = $true
    )
    
    if (-not (Test-Path $Path)) {
        return
    }
    
    try {
        $Item = Get-Item $Path -Force
        if ($IsHidden) {
            $Item.Attributes = $Item.Attributes -bor [System.IO.FileAttributes]::Hidden
            Write-Host "  ✓ [$Path] 숨김 설정" -ForegroundColor Green
        } else {
            $Item.Attributes = $Item.Attributes -band -bnot [System.IO.FileAttributes]::Hidden
            Write-Host "  ✓ [$Path] 숨김 해제" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ✗ [$Path] 숨김 설정 실패: $_" -ForegroundColor Red
    }
}

function Create-DeploymentStructure {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "배포 환경 폴더 구조 생성" -ForegroundColor Cyan
    Write-Host "경로: $DeploymentRoot" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # 루트 폴더 생성
    if (-not (Test-Path $DeploymentRoot)) {
        New-Item -ItemType Directory -Path $DeploymentRoot -Force | Out-Null
        Write-Host "✓ 루트 폴더 생성: $DeploymentRoot" -ForegroundColor Green
    } else {
        Write-Host "✓ 루트 폴더 존재: $DeploymentRoot" -ForegroundColor Green
    }
    
    # 각 앱별 폴더 구조 생성
    foreach ($AppName in $FolderStructure.Keys) {
        $AppConfig = $FolderStructure[$AppName]
        
        if ($AppName) {
            Write-Host "`n[$AppName] 폴더 구조 생성:" -ForegroundColor Yellow
            $AppRoot = Join-Path $DeploymentRoot $AppName
        } else {
            Write-Host "`n[전역] 폴더 구조 생성:" -ForegroundColor Yellow
            $AppRoot = $DeploymentRoot
        }
        
        # 서브폴더 생성
        if ($AppConfig.SubFolders) {
            foreach ($SubFolder in $AppConfig.SubFolders) {
                $FolderPath = Join-Path $AppRoot $SubFolder
                if (-not (Test-Path $FolderPath)) {
                    New-Item -ItemType Directory -Path $FolderPath -Force | Out-Null
                    Write-Host "  ✓ 폴더: $SubFolder" -ForegroundColor Green
                } else {
                    Write-Host "  ✓ 폴더 존재: $SubFolder" -ForegroundColor Gray
                }
            }
        }
        
        # JSON 파일 생성 (기본 값)
        if ($AppConfig.Files) {
            foreach ($File in $AppConfig.Files) {
                $FilePath = Join-Path $AppRoot $File
                if (-not (Test-Path $FilePath)) {
                    # 파일 디렉토리 생성
                    $FileDir = Split-Path $FilePath -Parent
                    if (-not (Test-Path $FileDir)) {
                        New-Item -ItemType Directory -Path $FileDir -Force | Out-Null
                    }
                    
                    # 기본 JSON 파일 생성
                    $DefaultJson = @{}
                    switch -Wildcard ($File) {
                        '*credits.json' {
                            $DefaultJson = @{
                                'app_name' = if ($AppName) { $AppName } else { 'global' }
                                'total_credits' = 1000
                                'used_credits' = 0
                                'last_updated' = (Get-Date).ToString('o')
                                'history' = @()
                            }
                        }
                        '*settings.json' {
                            $DefaultJson = @{
                                'theme' = 'light'
                                'language' = 'ko'
                                'auto_update' = $true
                                'log_level' = 'info'
                            }
                        }
                        '*wf_global_settings.json' {
                            $DefaultJson = @{
                                'version' = '1.0.0'
                                'apps' = @()
                                'global_settings' = @{
                                    'check_update' = $true
                                    'auto_backup' = $true
                                }
                            }
                        }
                    }
                    
                    $DefaultJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $FilePath -Encoding UTF8
                    Write-Host "  ✓ 파일: $File" -ForegroundColor Green
                } else {
                    Write-Host "  ✓ 파일 존재: $File" -ForegroundColor Gray
                }
            }
        }
    }
}

function Apply-HiddenAttributes {
    if ($SkipHidden.IsPresent) {
        Write-Host "`n숨김 속성 적용 건너뜀 (테스트 모드)" -ForegroundColor Yellow
        return
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "숨김 속성 적용" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # 루트 폴더 숨김 설정
    Write-Host "[전역]" -ForegroundColor Yellow
    Set-Hidden -Path $DeploymentRoot -IsHidden $true
    
    # 각 앱별 숨김 속성 적용
    foreach ($AppName in $FolderStructure.Keys) {
        if (-not $AppName) { continue }
        
        Write-Host "`n[$AppName]" -ForegroundColor Yellow
        $AppRoot = Join-Path $DeploymentRoot $AppName
        
        if (-not (Test-Path $AppRoot)) { continue }
        
        # 앱 폴더 자체 숨김 설정
        Set-Hidden -Path $AppRoot -IsHidden $true
        
        # 서브폴더 숨김 설정
        $AppConfig = $FolderStructure[$AppName]
        if ($AppConfig.SubFolders) {
            foreach ($SubFolder in $AppConfig.SubFolders) {
                $FolderPath = Join-Path $AppRoot $SubFolder
                if (Test-Path $FolderPath) {
                    Set-Hidden -Path $FolderPath -IsHidden $true
                }
            }
        }
        
        # JSON 파일 숨김 설정
        if ($AppConfig.Files) {
            foreach ($File in $AppConfig.Files) {
                $FilePath = Join-Path $AppRoot $File
                if (Test-Path $FilePath) {
                    Set-Hidden -Path $FilePath -IsHidden $true
                }
            }
        }
    }
    
    # 전역 설정 파일 숨김 설정
    Write-Host "`n[전역 설정 파일]" -ForegroundColor Yellow
    $GlobalConfig = $FolderStructure['']
    if ($GlobalConfig.Files) {
        foreach ($File in $GlobalConfig.Files) {
            $FilePath = Join-Path $DeploymentRoot $File
            if (Test-Path $FilePath) {
                Set-Hidden -Path $FilePath -IsHidden $true
            }
        }
    }
}

function Verify-Structure {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "배포 환경 검증" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    $AllValid = $true
    
    foreach ($AppName in $FolderStructure.Keys) {
        $AppConfig = $FolderStructure[$AppName]
        $AppRoot = if ($AppName) { Join-Path $DeploymentRoot $AppName } else { $DeploymentRoot }
        
        $AppLabel = if ($AppName) { "[$AppName]" } else { "[전역]" }
        
        # 서브폴더 검증
        if ($AppConfig.SubFolders) {
            foreach ($SubFolder in $AppConfig.SubFolders) {
                $FolderPath = Join-Path $AppRoot $SubFolder
                if (Test-Path $FolderPath) {
                    Write-Host "  ✓ $AppLabel $SubFolder" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ $AppLabel $SubFolder (누락)" -ForegroundColor Red
                    $AllValid = $false
                }
            }
        }
        
        # 파일 검증
        if ($AppConfig.Files) {
            foreach ($File in $AppConfig.Files) {
                $FilePath = Join-Path $AppRoot $File
                if (Test-Path $FilePath) {
                    $FileSize = (Get-Item $FilePath).Length
                    Write-Host "  ✓ $AppLabel $File ($FileSize bytes)" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ $AppLabel $File (누락)" -ForegroundColor Red
                    $AllValid = $false
                }
            }
        }
    }
    
    if ($AllValid) {
        Write-Host "`n✓ 모든 배포 환경 구조가 올바르게 구성되었습니다" -ForegroundColor Green
    } else {
        Write-Host "`n✗ 누락된 항목이 있습니다" -ForegroundColor Red
    }
    
    return $AllValid
}

# ==================== 메인 실행 ====================
try {
    Create-DeploymentStructure
    Apply-HiddenAttributes
    $Valid = Verify-Structure
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "배포 환경 설정 완료" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    if ($Valid) {
        Write-Host "배포 환경: $DeploymentRoot" -ForegroundColor Green
        Write-Host "폴더 속성: 숨김 처리 완료" -ForegroundColor Green
        Write-Host "상태: 준비 완료" -ForegroundColor Green
    } else {
        exit 1
    }
} catch {
    Write-Host "`n✗ 오류 발생: $_" -ForegroundColor Red
    exit 1
}

exit 0
