# Release Notes - BOM2Excel v0.8.0.5

**Release Date**: 2026-01-08  
**Version**: 0.8.0.5

---

## 개요

이번 릴리스는 Google Sheets 동기화 안정성 향상과 개발 환경에서의 크레딧 시스템 신뢰성 개선에 초점을 맞췄습니다.

---

## 주요 변경사항

### 🔧 Fixed - 버그 수정

#### Google Sheets 동기화 실패 문제 해결
- **문제**: 개발 환경에서 Python 스크립트 직접 실행 시 Google Sheets 크레딧 동기화가 실패하던 문제
- **원인**: `sys.argv[0]`가 `-c`, `Untitled`, 또는 유효하지 않은 경로를 반환하여 서비스 계정 인증 파일(`.silver-argon-*.json`)을 찾지 못함
- **해결방법**: 
  - `wf_googlesheets_manager.py`의 `_get_dev_credentials_dir()` 메서드 개선
  - Call stack 검사를 통한 Fallback 로직 추가
  - 실제 앱 실행 경로(`30.apps`, `50.data` 디렉토리)를 자동으로 탐지하여 인증 파일 위치 확인
- **영향**: 개발 환경에서의 크레딧 동기화가 안정적으로 작동

#### 상세 오류 로깅 추가
- **추가 위치**:
  - `sync_credit_data()`: Google Sheets 연결 실패 시 상세한 오류 메시지 출력
  - `_append_credit_usage_log()`: 크레딧 사용 로그 기록 실패 시 원인별 상세 메시지 제공
- **효과**: 동기화 문제 발생 시 즉각적인 원인 파악 가능

---

## Known Issues

### UI - 파일 덮어쓰기 취소 미작동
- **증상**: 작업 결과 폴더에 기존 파일이 존재할 때 덮어쓰기 확인 다이얼로그에서 "아니오"를 클릭해도 작업이 계속 진행됨
- **영향 범위**: BOM 추출 프로세스 시작 후 기존 파일 존재 시
- **임시 해결방법**: "예"를 클릭하여 파일을 덮어쓰거나, 작업 시작 전에 결과 폴더를 비움
- **계획**: 다음 버전에서 수정 예정

---

## 기술 세부사항

### 파일 변경 내역

#### `10.common/wf_googlesheets_manager.py`
- **_get_dev_credentials_dir() 메서드 (59-102줄)**
  - `import inspect` 추가
  - Call stack 기반 앱 경로 탐지 로직 추가
  - `sys.argv[0]` 실패 시 자동 Fallback 동작

```python
# Fallback: Call stack에서 실제 앱 파일 경로 찾기
for frame_info in inspect.stack():
    frame_path = Path(frame_info.filename).resolve()
    if "30.apps" in frame_path.parts or "50.data" in frame_path.parts:
        potential_config = frame_path.parent / "config"
        if potential_config.exists():
            silver_files = list(potential_config.glob(".silver-argon-*.json"))
            if silver_files:
                return potential_config
```

- **sync_credit_data() 메서드 (907-927줄)**
  - 동기화 실패 시 상세 로깅 추가
  - `self.gc` 및 `ACTIVE_SHEET_MODE` 상태 출력

- **_append_credit_usage_log() 메서드 (1062-1078줄)**
  - 오류 원인별 구체적인 메시지 출력
  - `self.gc` 및 `self.usage_worksheet` 개별 검증

---

## 테스트 결과

### 성공 케이스
✅ Google Sheets 클라이언트 연결 성공  
✅ `usage_worksheet` 초기화 완료 (`credit_usage_log`)  
✅ 서비스 계정 인증 파일 자동 탐지 확인  
✅ 크레딧 동기화 정상 작동

### 테스트 환경
- Python 3.14
- Windows 11
- Google Sheets API v4
- 개발 모드 (PyInstaller 번들링 전)

---

## 업그레이드 가이드

### 필수 작업
특별한 업그레이드 작업이 필요하지 않습니다. 기존 설정 및 데이터가 그대로 유지됩니다.

### 주의사항
- 서비스 계정 인증 파일(`.silver-argon-*.json`)이 `config/` 폴더에 존재하는지 확인
- Google Sheets API 활성화 및 권한 설정 유지 확인

---

## 다음 버전 계획 (v0.8.0.6)

- [ ] 파일 덮어쓰기 취소 기능 수정
- [ ] UI 응답성 개선
- [ ] 추가 오류 처리 강화

---

## 지원

문제가 발생하거나 질문이 있으신 경우:
- 로그 파일 확인: `logs/YYYYMMDD.txt`
- 디버그 로그: `debug_log.txt`

---

**Developed by**: WorksFree RPA Team  
**Build Date**: 2026-01-08
