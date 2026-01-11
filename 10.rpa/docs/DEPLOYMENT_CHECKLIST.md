# 배포 전 체크리스트

## 📋 빌드 전 확인사항

### 1. 버전 관리
- [ ] `runtime_config.full_version` 확인 (settings.json)
- [ ] `runtime_config.build_count` 확인 (settings.json)
- [ ] ❌ `app_config` 섹션이 없는지 확인 (MECE 위반)

### 2. 설정 파일 일관성
- [ ] 모든 앱이 `runtime_config` 사용 (app_config 사용 금지)
- [ ] 빌드 스크립트가 `runtime_config.full_version` 읽는지 확인
- [ ] spec 파일이 `runtime_config` 참조하는지 확인

### 3. 배치 파일 검증
- [ ] `create_desktop_shortcut.bat`가 `runtime_config` 읽는지 확인
- [ ] 앱 이름 매핑이 정확한지 확인:
  - `bom_exporter` → "Bom Exporter"
  - `dwg_batch_print` → "DWG Batch Print"
  - `dwg_classifier` → "DWG Classifier"
  - `conversion_verifier` → "Conversion Verifier"
  - `korean_filename_normalizer` → "Korean Filename Normalizer"

## 🧪 빌드 후 검증

### 1. 로컬 테스트 (빌드 직후)
```powershell
# 배포판 압축 해제 테스트
$testPath = "D:\release\candidates\bom_exporter_v0.9.1.7\bom_exporter_v0.9.1.7_portable"
cd $testPath

# 1. exe 실행 테스트
.\bom_exporter.exe

# 2. 버전 정보 확인
Write-Host "설정 파일 버전 확인:" -ForegroundColor Cyan
$settings = Get-Content ".\_internal\.wf_rpa\bom_exporter\settings.json" -Raw | ConvertFrom-Json
Write-Host "  버전: $($settings.runtime_config.full_version)" -ForegroundColor Yellow
Write-Host "  빌드: $($settings.runtime_config.build_count)" -ForegroundColor Yellow

# 3. 바로가기 생성 테스트
.\create_desktop_shortcut.bat
# → "Bom Exporter" 이름으로 생성되는지 확인
# → 바로가기 설명에 버전 정보가 표시되는지 확인
```

### 2. 타 PC 배포 테스트
- [ ] 압축 파일을 다른 PC로 복사
- [ ] 압축 해제 후 `create_desktop_shortcut.bat` 실행
- [ ] 바로가기 이름 확인: "Bom Exporter" (❌ bom_exporter)
- [ ] 바로가기 설명 확인: "Bom Exporter | v0.9.1.7 | built 217" (❌ unknown)
- [ ] 앱 실행 및 버전 표시 확인

### 3. 자동 검증 스크립트
```powershell
# verify_deployment.ps1
param([string]$AppPath)

$AppName = Split-Path $AppPath -Leaf
$ExePath = Get-ChildItem $AppPath -Filter "*.exe" | Select-Object -First 1

# 설정 파일 검증
$settingsPath = Join-Path $AppPath "_internal\.wf_rpa\$($ExePath.BaseName)\settings.json"
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    $version = $settings.runtime_config.full_version
    $build = $settings.runtime_config.build_count
    
    Write-Host "✅ 버전: $version (빌드: $build)" -ForegroundColor Green
    
    # app_config 섹션이 없는지 확인
    if ($settings.PSObject.Properties.Name -contains "app_config") {
        Write-Host "❌ 경고: app_config 섹션이 존재합니다 (MECE 위반)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ 오류: settings.json 없음" -ForegroundColor Red
    exit 1
}

# 바로가기 배치 파일 검증
$batPath = Join-Path $AppPath "create_desktop_shortcut.bat"
if (Test-Path $batPath) {
    $batContent = Get-Content $batPath -Raw
    if ($batContent -match "app_config\.full_version") {
        Write-Host "❌ 오류: 배치 파일이 app_config를 참조합니다" -ForegroundColor Red
        exit 1
    }
    if ($batContent -match "runtime_config\.full_version") {
        Write-Host "✅ 배치 파일 검증 통과" -ForegroundColor Green
    }
}

Write-Host "`n✅ 배포판 검증 완료" -ForegroundColor Green
```

## 🔄 반복 실수 방지 전략

### 1. 자동화
- **빌드 전 검증**: 빌드 스크립트에 자동 검사 추가
- **빌드 후 검증**: 배포판 자동 테스트 스크립트 실행
- **CI/CD**: GitHub Actions 또는 Azure Pipelines 통합

### 2. 문서화
- **체크리스트**: 이 문서를 배포 시 필수 확인
- **변경 로그**: CHANGELOG.md에 구조 변경사항 기록
- **주석**: 중요 파일에 "⚠️ 수정 시 다른 파일도 확인" 주석 추가

### 3. 코드 리뷰
- [ ] 빌드 스크립트 변경 시 5개 앱 모두 확인
- [ ] JSON 구조 변경 시 읽는 모든 곳 확인:
  - spec 파일 (5개)
  - 빌드 스크립트 (5개)
  - 배치 파일 (1개 공통)
  - UI 코드 (ui_main.py, ui_setting.py)

### 4. 테스트 자동화
```powershell
# 빌드 후 자동 실행
$apps = @(
    "bom_exporter",
    "dwg_batch_print",
    "dwg_classifier",
    "conversion_verifier",
    "korean_filename_normalizer"
)

foreach ($app in $apps) {
    $latest = Get-ChildItem "D:\release\candidates" -Directory | 
              Where-Object { $_.Name -like "${app}_v*" } | 
              Sort-Object LastWriteTime -Descending | 
              Select-Object -First 1
    
    if ($latest) {
        $portablePath = Get-ChildItem $latest.FullName -Directory | Select-Object -First 1
        .\verify_deployment.ps1 -AppPath $portablePath.FullName
    }
}
```

## 📝 수정 이력

### 2026-01-06: MECE 원칙 적용
**문제**: `app_config`와 `runtime_config`에 버전 정보 중복
**해결**: `runtime_config`로 단일화

**변경된 파일**:
1. ✅ `bom_exporter/settings.json` - app_config 제거
2. ✅ `bom_exporter/bom_exporter.spec` - runtime_config 사용
3. ✅ `bom_exporter/build_bom_exporter.ps1` - runtime_config.full_version 읽기
4. ✅ `create_desktop_shortcut.bat` - runtime_config 사용, 앱 이름 매핑 추가
5. ✅ 나머지 4개 앱 동일 수정

**검증 포인트**:
- [ ] 빌드 시 버전이 0.0.0.0이 아닌지
- [ ] 바로가기 이름이 "Bom Exporter"인지 (bom_exporter ❌)
- [ ] 바로가기 설명에 버전/빌드 번호가 표시되는지 (unknown ❌)

## 🎯 핵심 원칙

### MECE (Mutually Exclusive, Collectively Exhaustive)
- ✅ **단일 소스**: 버전 정보는 `runtime_config`에만 존재
- ❌ **중복 금지**: `app_config`에 동일 정보 저장 금지
- ✅ **일관성**: 모든 파일이 같은 위치 참조

### 변경 시 확인 필수 항목
| 변경 항목 | 확인 대상 | 파일 개수 |
|----------|---------|---------|
| JSON 구조 | spec, build script, bat, UI | 13개 |
| 빌드 스크립트 | 5개 앱 모두 | 5개 |
| 공통 배치 파일 | 즉시 재빌드 필요 | 5개 앱 |

---

**마지막 업데이트**: 2026-01-06  
**작성자**: GitHub Copilot  
**버전**: 1.0
