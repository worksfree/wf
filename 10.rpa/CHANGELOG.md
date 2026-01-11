# Changelog - Infrastructure

공통 인프라(빌드 시스템, 테스트, 배포)의 변경 이력입니다.
앱별 변경사항은 각 앱 폴더의 CHANGELOG.md를 참고하세요.

---

## [2025-12-02] 버전 표시 및 경로 시스템 통합

### Fixed
- **settings.json 경로 불일치**: 4개 앱 모두 대문자 폴더명으로 통일 (config/Bom_Exporter/, config/Dwg_Classifier/, config/Conversion_Verifier/, config/Korean_Filename_Normalizer/)
- **frozen 모드 경로**: 모든 ui_main.py에서 `Path.home() / ".wf_rpa" / "{app_name}"` 사용하도록 수정 (기존 `_internal/` 경로 오류 수정)
- **win32timezone 누락**: 4개 앱 spec 파일 hiddenimports에 pywin32 모듈 추가

### Changed
- **spec 파일 경로**: app_specific 딕셔너리 키를 'bom2excel' → 'bom_exporter'로 통일
- **NSIS 설치 경로**: 모든 앱의 settings.json이 사용자 홈 `~/.wf_rpa/{app}/`에 설치되도록 수정
- **prepare_user_configs()**: Dwg_Classifier와 Conversion_Verifier spec에 함수 추가

### Verified
- 개발 모드: 4개 앱 모두 최신 버전 정상 로드 (BE: v0.8.1.5, DC: v0.7.6.7, CV: v0.7.5.5, KFN: v0.7.5.7)

---

## [2025-11-30] 빌드 시스템 표준화

### Added
- **PostClean 옵션**: 모든 빌드 스크립트에 `-PostClean` 플래그 추가
- **cleanup_build_artifacts.ps1**: 빌드 후 임시 파일 정리 스크립트 (`.build_templates`, `build/`, `dist/`)
- **통합 테스트 구조**: `90.tests/` 폴더에 pytest 기반 테스트 구조 도입
  - Markers: unit, integration, sanity, regression, interactive, static
  - 통합 runner: `90.tests/run.ps1`
  - CI: GitHub Actions 워크플로우 추가 (`.github/workflows/ci.yml`)

### Changed
- **installer_resources 제거**: 루트 레벨 `installer_resources/` 삭제
  - 각 앱의 spec 파일이 app-local `build/user_home_bundle/.wf_rpa/` 사용
  - CV, B2E, KFN spec 파일 패치 완료
- **config 구조 정리**: bom2excel dev 경로를 `config/bom2excel/`로 변경
  - 레거시 `config/settings.json` 제거
- **문서 재구성**: 
  - 레거시 리포트들을 `docs/history/`로 이동
  - `BUILD_TROUBLESHOOTING.md` → `docs/TROUBLESHOOTING.md`
  - `DEPLOYMENT_GUIDE.md` → `docs/DEPLOYMENT.md`

### Fixed
- **dwg_classifier 빌드 스크립트**: 파라미터 구문 오류 수정 (`$Clean,` 쉼표 추가)
- **dwg_classifier PostClean**: `Split-Path -Parent -Parent` 중첩 오류 수정

---

## [2025-11-15~21] 테스트 및 정책 시스템

### Added
- **Policy sync 테스트**: Google Sheets 정책 동기화 통합 테스트
- **Fixtures**: `90.tests/fixtures/policy_sync/` 추가

### Changed
- **Test markers**: pytest.ini에 확장 마커 추가
- **Requirements**: `requirements-dev.txt` 생성 (ruff, mypy, pytest)

### Removed
- 레거시 테스트 스크립트: `test_policy_sync.py`, `scripts/` 폴더 삭제

---

## [2025-11-02] 크레딧 시스템 개선

### Changed
- **정책 우선순위**: 사용자 정책 > 저장소 정책 > 기본값
- **체험판 크레딧**: 
  - 유료 앱(B2E, DWG, CV): 2000
  - 무료 앱(KFN): -1 (무제한)

---

## [2025-10-18~27] UI 및 성능 최적화

### Fixed
- **conversion_verifier UI**: "응답 없음" 현상 (batched filtering with `after()`)
- **더미 창 깜빡임**: 일관된 `withdraw()` 타이밍

### Added
- **단일 인스턴스 가드**: `wf_app_init_helpers.py`에 통합
- **동적 타임아웃**: 작업량 기반 타임아웃 계산

---

## 문서 아카이브

상세한 개발 로그는 `docs/history/`에서 확인할 수 있습니다:
- `2025-10-18_dev_log.md`
- `2025-10-24_dev_log.md`
- `2025-11-02_dev_log.md`
- `2025-11-15_dev_log.md`
- `console_flash_fix.md`
- `bom2excel_build.md`
- 기타 기술 리포트들
