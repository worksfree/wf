# Changelog - 공통 모듈 (10.common)

공통 모듈의 주요 변경사항을 기록합니다.

## 형식 안내
- **Added**: 새로운 기능 추가
- **Changed**: 기존 기능 변경
- **Fixed**: 버그 수정
- **Removed**: 기능 제거

---

## [2025-11-30] - 단일 인스턴스 가드 통합

### Changed
- `wf_app_init_helpers.py` 모듈로 통합 (기존 `wf_single_instance.py` 통폐합)
- 모든 앱에서 동일한 단일 인스턴스 로직 공유
- 앱 초기화 관련 헬퍼 함수들을 한 모듈에 집약

### Removed
- `wf_single_instance.py` (wf_app_init_helpers.py로 이동)

---

## [2025-11-15~21] - 정책 시스템 개선

### Added
- **정책 우선순위 구조 확립**:
  1. Google Sheets 동기화 정책 (최우선)
  2. 사용자 로컬 설정
  3. 저장소 기본 정책
  4. 코드 내 기본값

### Changed
- `wf_googlesheets_manager.py`: 앱별 정책 시트 읽기 개선
  - `load_app_policy(app_name)` 메서드로 앱별 크레딧 정책 로드
  - 시트 형식 검증 강화
- `wf_credit_manager.py`: 정책 로드 순서 최적화
  - Google Sheets 정책이 우선 적용되도록 수정
  - 정책 누락 시 단계적 폴백 처리

### Fixed
- 정책 동기화 실패 시 무한 대기 문제 → 타임아웃 추가 (30초)
- 크레딧 정책 파일 누락 시 앱 실행 실패 → 기본 정책으로 폴백

---

## [2025-11-02] - 크레딧 시스템 로깅

### Added
- **크레딧 사용 이력 상세 로깅**:
  - `~/.wf_rpa/{app}/credit_history.json` 파일로 모든 거래 기록
  - 타임스탬프, 거래 유형 (사용/충전/환불), 금액, 잔액, 설명 저장
- `wf_credit_manager.py`: `record_usage()` 메서드 추가
  - 로컬 이력 파일에 JSON 라인 추가
  - 회전식 로그 (최대 10,000건 유지)

### Changed
- `use_credit()` 메서드: 모든 차감 작업 시 이력 자동 기록
- `add_credit()` 메서드: 충전 작업 시 이력 자동 기록

### Fixed
- 크레딧 파일 동시 접근 시 Race Condition → 파일 잠금 추가

---

## [2025-10-24~27] - Google Sheets 연동 강화

### Added
- `wf_googlesheets_manager.py`: OAuth 2.0 자동 갱신
  - Refresh token 자동 갱신 로직
  - 토큰 만료 시 자동 재인증 시도
- 크레딧 정책 시트 지원:
  - 앱별 시트에서 `credit_per_file`, `memory_limit_mb` 등 정책 읽기
  - 정책 변경 시 앱 재시작 없이 동기화

### Changed
- 인증 정보 위치: `~/.wf_rpa/` 디렉토리로 통일
  - 기존 루트 `installer_resources/` 제거
  - 앱별 서브폴더에서 credentials 관리

### Fixed
- Sheets API 할당량 초과 시 앱 멈춤 → Exponential backoff 재시도 추가 (최대 3회)

---

## [2025-10-18] - 개발/배포 환경 감지

### Added
- **자동 환경 감지 로직**:
  - `WF_RPA_DEV=1` 환경 변수 또는 `.git/` 디렉토리 존재 시 개발 모드
  - 개발 모드: 무제한 크레딧, `./config/` 디렉토리 사용
  - 배포 모드: 정책 기반 크레딧, `~/.wf_rpa/` 디렉토리 사용

### Changed
- `wf_credit_manager.py`: 환경별 크레딧 정책 적용
  - 개발: 크레딧 차감 없음 (로그만 기록)
  - 배포: 실제 크레딧 차감
- `wf_config.py`: 환경별 설정 파일 경로 동적 결정

### Fixed
- PyInstaller 빌드 시 환경 감지 실패 → `sys.frozen` 속성으로 배포 버전 감지

---

## 참고

- [Root CHANGELOG](../CHANGELOG.md): 인프라/빌드 시스템 변경사항
- [App CHANGELOGs](../30.apps/): 앱별 기능 변경사항
- [정책 시스템 문서](../docs/history/per_app_policy.md)
- [크레딧 로깅 문서](../docs/history/credit_logging.md)
