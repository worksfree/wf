# Changelog - DWG Classifier

DWG 파일 분류 도구의 주요 변경사항을 기록합니다.

## 형식 안내
- **Added**: 새로운 기능 추가
- **Changed**: 기존 기능 변경
- **Fixed**: 버그 수정
- **Removed**: 기능 제거

---

## [0.7.5.3] - 2025-11-30

### Fixed
- **빌드 스크립트 오류**: PowerShell 파라미터 구문 오류 수정
  - `$Clean` 파라미터 뒤 쉼표 누락 → 추가
  - `Split-Path -Parent -Parent` 구문 오류 → 중첩 호출로 수정
- **PostClean 실패**: 경로 계산 오류로 정리 실패 → 수정 완료

### Changed
- **빌드 시스템**: 앱 로컬 번들 구조 적용
  - `build/user_home_bundle/` 사용, 루트 의존성 제거

---

## [0.7.5.2] - 2025-11-20

### Added
- **메모리 정책**: 앱별 메모리 한계 설정
  - 정책 파일에서 `memory_limit_mb` 지정 가능
  - 한계 초과 시 조기 종료로 시스템 보호

### Changed
- **크레딧 로깅**: 파일 분류 작업 상세 기록
  - `~/.wf_rpa/dwg_classifier/credit_history.json`에 거래 이력 저장

### Fixed
- 대량 DWG 파일 처리 시 메모리 부족 → 메모리 모니터링 추가

---

## [0.7.5.1] - 2025-11-10

### Added
- **정책 동기화**: Google Sheets에서 크레딧 정책 자동 로드
  - 정책 우선순위: Sheets > 로컬 settings > 저장소 기본 > 코드 기본값

### Changed
- **UI 개선**: 관리자 모드 추가
  - Ctrl+Shift+A로 고급 설정 접근
  - 크레딧 이력 및 정책 상태 조회 가능

---

## [0.7.5.0] - 2025-11-02

### Added
- **DWG 버전 감지**: 파일 분류 시 AutoCAD 버전 자동 감지
  - 2000/2004/2007/2010/2013/2018 버전 구분
- **재시작 카운터**: UI에 앱 재시작 횟수 표시

### Changed
- **분류 알고리즘**: 파일명 기반 + 버전 기반 복합 분류
  - 프로젝트 코드, 도면 종류, CAD 버전별 폴더 생성

---

## [0.7.4.x] - 2025-10-18~27

### Added
- **크레딧 시스템**: 파일 분류당 크레딧 차감
  - 기본 정책: 파일당 10 크레딧
- **단일 인스턴스 가드**: 중복 실행 방지

### Changed
- **설정 파일 위치**: `~/.wf_rpa/dwg_classifier/` 로 이동

### Fixed
- 파일명 특수문자 처리 오류 → 유니코드 정규화 추가
- 경로 길이 초과 시 분류 실패 → 경로 단축 로직 추가

---

## 참고

- [Root CHANGELOG](../../CHANGELOG.md): 인프라 변경사항
- [Common CHANGELOG](../../10.common/CHANGELOG.md): 공통 모듈 변경사항
- [프로젝트 README](../../README.md): 프로젝트 개요
