# Changelog - Korean Filename Normalizer

파일명 한글 정규화 도구의 주요 변경사항을 기록합니다.

## 형식 안내
- **Added**: 새로운 기능 추가
- **Changed**: 기존 기능 변경
- **Fixed**: 버그 수정
- **Removed**: 기능 제거

---

## [0.7.4.7] - 2025-11-30

### Changed
- **빌드 시스템**: 앱 로컬 번들 구조 적용
  - `build/user_home_bundle/` 사용, 루트 의존성 제거
  - NSIS 인스톨러: 와일드카드 패턴으로 credentials 파일 복사

### Fixed
- 빌드 경로 참조 오류 해결

---

## [0.7.4.6] - 2025-11-20

### Added
- **크레딧 로깅**: 파일명 변경 작업 상세 기록
  - `~/.wf_rpa/korean_filename_normalizer/credit_history.json`에 거래 이력 저장

### Changed
- **정책 동기화**: Google Sheets에서 크레딧 정책 자동 로드
  - 정책 우선순위: Sheets > 로컬 settings > 저장소 기본 > 코드 기본값

---

## [0.7.4.5] - 2025-11-10

### Added
- **정규화 옵션**: 파일명 정규화 모드 선택
  - NFC (Canonical Composition): 조합형 한글
  - NFD (Canonical Decomposition): 분해형 한글
  - NFKC/NFKD: 호환성 정규화

### Changed
- **UI 개선**: 정규화 전후 미리보기
  - 변경될 파일명 사전 확인
  - 중복 파일명 충돌 자동 감지

---

## [0.7.4.4] - 2025-11-02

### Added
- **관리자 모드**: 고급 설정 및 변경 이력 조회
  - Ctrl+Shift+A로 진입
  - 크레딧 이력, 파일명 변경 기록 조회

### Changed
- **정규화 알고리즘**: Unicode NFC 기본값으로 변경
  - Windows/macOS 간 호환성 개선

---

## [0.7.4.3] - 2025-10-27

### Added
- **크레딧 시스템**: 파일명 변경당 크레딧 차감
  - 기본 정책: 파일당 5 크레딧
- **단일 인스턴스 가드**: 중복 실행 방지

### Changed
- **설정 파일 위치**: `~/.wf_rpa/korean_filename_normalizer/` 로 이동

---

## [0.7.4.x] - 2025-10-18~24

### Added
- **일괄 정규화**: 폴더 내 모든 파일 자동 처리
- **재귀 옵션**: 하위 폴더 포함 정규화

### Fixed
- macOS에서 생성된 파일명 Windows에서 깨짐 → NFD → NFC 변환으로 해결
- 특수문자 포함 파일명 처리 오류 → 예외 처리 추가

---

## 참고

- [Root CHANGELOG](../../CHANGELOG.md): 인프라 변경사항
- [Common CHANGELOG](../../10.common/CHANGELOG.md): 공통 모듈 변경사항
- [프로젝트 README](../../README.md): 프로젝트 개요
