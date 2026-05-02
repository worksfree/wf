# WF-RPA 배포 검증 워크플로우

## 목표

**인증 툴킷(WF-ACT)을 통과하면 배포 패키지의 기본적인 라이프사이클에 문제가 없음을 보증**

---

## 검증 레벨

### Level 1: 빠른 검증 (2분)
```powershell
.\verify_exe_package.ps1 -ReleaseDir "D:\release\candidates"
```
- **검증 항목**: 119개 (7개 앱 × 17개 체크)
- **대상**: 파일 시스템만 (앱 실행 없음)
- **체크리스트**:
  - 패키지 구조 (portable 폴더, exe, _internal)
  - 크리덴셜 파일 포함 (worksfree-*.json, silver-argon-*.json)
  - 번들 설정 완전성 (settings.json, wf_rpa_config.json)
  - 버전 정보 정확성
  - NSIS 설치 파일 (BuildType=3인 경우)

### Level 2: 완전 인증 (10분)
```powershell
cd 90.tests\ui_lifecycle_test
python run_certification.py --app be dp ar dc cv kfn qr -l full
```
- **검증 항목**: 938개 (7개 앱 × 134개 테스트)
- **대상**: 앱 라이프사이클 전체

---

## 자동화 워크플로우

### 방법 1: 한 번에 실행 (권장)
```powershell
.\auto_build_and_certify.ps1
```

프로세스:
1. 빌드 완료 대기 (최대 15분)
2. 최신 빌드를 candidates로 복사
3. `verify_exe_package.ps1` 실행 (빠른 검증)
4. WF-ACT 인증 실행 (DEV 모드)
5. HTML 리포트 생성

결과 위치:
```
test_results/certification_YYYYMMDD_HHMMSS_auto/
├── index.html
├── bom_exporter_report.html
└── ... (앱별 리포트)
```

### 방법 2: 수동 단계별

```powershell
# Step 1: 빌드
.\build_all_parallel.ps1 -BuildType 2

# Step 2: candidates 복사
$apps = @('bom_exporter','dwg_batch_print','attribute_reset','dwg_classifier',
          'conversion_verifier','korean_filename_normalizer','qrcode_generator')
foreach ($app in $apps) {
    $latest = Get-ChildItem "D:\release" -Directory -Filter "${app}_v*" |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Copy-Item $latest.FullName -Destination "D:\release\candidates\" -Recurse -Force
}

# Step 3: 빠른 검증
.\verify_exe_package.ps1 -ReleaseDir "D:\release\candidates"

# Step 4: 완전 인증
cd 90.tests\ui_lifecycle_test
python run_certification.py --app be dp ar dc cv kfn qr -l full
```

---

## 결과 해석

### 성공 기준
- **verify_exe_package.ps1**: 성공률 90% 이상
  - 크리덴셜 파일 누락: 재빌드 필요
  - NSIS 설치 파일 없음: BuildType=2이므로 정상
- **WF-ACT 인증**: 100% 통과 (938개 테스트 전체 PASSED)

### DEV 모드 vs EXE 모드
- **현재**: DEV 모드만 134개 항목 전체 테스트 가능
- **EXE 모드**: TestServer 모듈 패키징 필요 (향후 개선 예정, [EXE_MODE_ISSUES.md](EXE_MODE_ISSUES.md) 참조)
- **권장**: DEV 모드로 100% 통과 후 배포 진행

---

## 배포 전 체크리스트

1. [ ] 빌드 성공 (7개 앱 모두)
2. [ ] `verify_exe_package.ps1` 통과 (성공률 90%+)
3. [ ] WF-ACT 인증 통과 (938/938 PASSED)
4. [ ] 크리덴셜 파일 포함 확인
   - `worksfree-b33a6b8f366b.json` (RELEASE)
   - `silver-argon-445712-a0-7092493258f3.json` (DEV)
5. [ ] 버전 정보 확인 (번들 settings.json의 `full_version`)

## 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-01-28 | PackageIntegritySuite 추가, auto_build_and_certify.ps1 생성, 7앱 × 17항목 검증 |
| 2026-01-27 | 934개 테스트 100% PASSED 달성 |
