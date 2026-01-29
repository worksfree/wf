# WorksFree RPA - TODO 목록

**마지막 업데이트**: 2026-01-29
**우선순위**: 🔴 즉시 / 🟡 단계적 / 🟢 장기

---

## ✅ 최근 완료 항목 (2026-01-29)

### 1. 번들링 일관성 100% 달성 ✅

**완료 내용**:
- 7개 spec 파일 `prepare_user_configs()` 순서 통일
- glob 패턴 표준화 (`'silver-argon*.json'`)
- set_hidden_attribute() 함수 호출 추가
- verify_bundle_structure.ps1 자동화 개선

**영향**:
- 모든 앱 배포 패키지 구조 일관성 확보
- 번들 검증 자동화로 품질 향상

### 2. 인증 테스트 완료 ✅

**결과**:
- **유료 앱 4개** (BE, DP, AR, DC): STANDARD 등급 (99.4% 통과)
- **무료 앱 3개** (CV, KFN, QR): 94.8% 통과 (크레딧 로직 개선 필요)

**테스트 커버리지**:
- Deployment Suite (25 tests)
- Package Integrity Suite (12 tests)
- Execution Environment Suite (8 tests)
- Config Suite (20 tests)
- Security Suite (6 tests)
- Registration Suite (15 tests)
- Credit Suite (22 tests, 무료 앱은 스킵)
- State Suite (14 tests)
- Recovery Suite (12 tests)
- UI Suite (22 tests)

**통합 리포트**: `90.tests/ui_lifecycle_test/test_results/certification_20260129_065258_exe/index.html`

---

## 🔴 즉시 수정 필요 (Critical Priority)

### 1. 무료 앱 크레딧 테스트 로직 개선 ⭐

**현재 문제**:
- CV, KFN, QR (무료 앱)이 크레딧 관련 테스트에서 실패
- `trial_credits: -1` (무제한) 정책으로 인한 테스트 케이스 불일치

**실패 테스트**:
1. `test_15_unregistered_limited_functionality`: 미등록 시 작업 차단
2. `test_03_negative_credits_handled`: 크레딧 음수 방지
3. `test_05_state_preserved_after_error`: 오류 후 크레딧 보존
4. `test_12_partial_work_recovery`: 부분 작업 후 크레딧 처리
5. `test_05_work_button_disabled_when_no_credits`: 버튼 비활성화
6. `test_07_credits_display_updated`: 크레딧 표시 업데이트

**해결 방안**:
1. **테스트 프레임워크 개선** (권장):
   - 무료 앱 감지 (`trial_credits == -1`)
   - 크레딧 관련 테스트 자동 스킵 또는 수정된 기대값 적용

2. **앱 로직 개선** (선택):
   - 무료 앱도 형식적 크레딧 시스템 적용 (큰 값으로 초기화)
   - UI에서 `trial_credits: -1` 처리 로직 보강

**우선순위**: 🔴 즉시 (STANDARD 등급 달성을 위해)

---

## 🔴 즉시 수정 필요 (기존 항목)

### 1. Bom_Exporter 앱명 통일 ⭐

**현재 문제**:
- 폴더명: `Bom_Exporter` (Title_Underscore)
- 코드 내 app_name: `bom2excel` (레거시 이름)
- 설정 파일 경로: `~/.wf_rpa/bom2excel/settings.json`
- 크레딧 정책 키: `Bom_Exporter` (최근 수정됨)

**영향**:
- 설정 파일 경로 혼동
- 크레딧 정책 매핑 오류 가능성
- 사용자 디렉토리 불일치

**수정 범위**:
- `ui_main.py`의 모든 `bom2excel` → `bom_exporter` 변경
- `automation.py` 내 app_name 참조 확인
- config 폴더명 변경: `config/bom2excel` → `config/bom_exporter`
- 기존 사용자 마이그레이션 스크립트 작성 (선택)
- 빌드 후 테스트: 설정 로드, 크레딧 동기화 확인

**참고 파일**:
- `d:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\ui_main.py` (Line 89, 96)

---

### 2. BE/DC 관리자 모드 구현 ⭐

**현재 상태**:
- ✅ **CV, KFN**: Progress Bar 클릭으로 관리자 모드 진입 가능
- ❌ **BE, DC**: 관리자 모드 변수는 있으나 진입 방법 없음

**추가 필요 기능**:
1. Progress Bar 클릭 이벤트 바인딩
2. 관리자 비밀번호 입력 다이얼로그
3. 관리자 모드 UI 확장 (로그 창, 테스트 버튼)
4. 테스트 데이터 생성/제거 기능

**구현 위치**:
- `30.apps/bom_exporter/ui_main.py`
- `50.data/dwg_classifier/ui_main.py`

**참고 파일**:
- `50.data/conversion_verifier/ui_main.py` (Lines 1009-1090)
- `50.data/korean_filename_normalizer/ui_main.py` (Lines 1770-1870)

---

### 3. 파일 덮어쓰기 취소 버그 (BE)

**증상**:
- 작업 결과 폴더에 기존 파일이 존재할 때 덮어쓰기 확인 다이얼로그에서 "아니오"를 클릭해도 작업이 계속 진행됨

**영향 범위**:
- BOM 추출 프로세스 시작 후 기존 파일 존재 시

**임시 해결방법**:
- "예"를 클릭하여 파일을 덮어쓰거나, 작업 시작 전에 결과 폴더를 비움

**계획**: 다음 버전에서 수정 예정

---

## 🟡 단계적 개선 (High Priority)

### 4. 초기화 시퀀스 표준화

**현재 상황**:
| 앱 | WFM 초기화 | CreditManager 초기화 | 성능 |
|----|-----------|---------------------|------|
| CV | Blocking (즉시) | 헬퍼 사용 (즉시) | 중간 |
| BE | Lazy (백그라운드) | Lazy (백그라운드) | 빠름 ⚡ |
| DC | Early blocking | Lazy (백그라운드) | 중간 |
| KFN | Blocking (즉시) | 즉시 | 느림 |

**목표**: BE의 Lazy 초기화 패턴을 모든 앱에 적용

**이점**:
- UI가 300-500ms 더 빠르게 표시됨
- 네트워크 동기화가 UI 블로킹하지 않음
- 사용자가 즉시 앱 사용 가능

**작업**:
- CV를 BE 패턴으로 리팩토링
- DC를 BE 패턴으로 리팩토링
- KFN을 BE 패턴으로 리팩토링
- 각 앱 startup time 측정 및 비교
- 크레딧 동기화 오류 처리 강화

---

### 5. 버전 파일 경로 표준화

**현재 상황**:
- CV: `~/.wf_rpa/conversion_verifier/settings.json` ✅
- BE: `~/.wf_rpa/bom2excel/settings.json` ❌ (레거시)
- DC: `~/.wf_rpa/DWG_Classifier/settings.json` ❌ (Title_Underscore)
- KFN: `~/.wf_rpa/korean_filename_normalizer/settings.json` ✅

**표준 규칙**:
```
사용자 디렉토리: ~/.wf_rpa/{lowercase_underscore}/
예시:
  - bom_exporter
  - dwg_classifier
  - conversion_verifier
  - korean_filename_normalizer
```

**작업**:
- BE 경로 변경 (Task #1과 통합)
- DC 경로 변경
- 마이그레이션 로직 추가 (선택)
- 빌드 후 신규 설치 테스트
- 기존 사용자 업그레이드 테스트

---

## 🟢 장기 개선 (Medium Priority)

### 6. 테스트 데이터 기능 통일

**현재 상태**:
- ✅ CV, KFN: 완전한 테스트 데이터 생성/제거 구현
- ❌ BE, DC: 테스트 기능 없음

**용도**:
- 개발/QA 환경에서 빠른 테스트
- 크레딧 시스템 검증
- 데모/시연용 데이터 준비

**작업**:
- BE에 테스트 데이터 기능 추가
- DC에 테스트 데이터 기능 추가
- 관리자 모드 UI에 버튼 추가
- 환경 변수 제어 추가 (`WF_TEST_MODE=1`)
- 테스트 시나리오 문서 작성

---

### 7. 로깅 레벨 설정 통일

**현재 상황**:
- 모든 앱이 `settings.json`의 `logging_config.log_level` 지원
- 기본값: `INFO`
- 지원 레벨: `DEBUG, INFO, WARNING, ERROR, CRITICAL`

**개선 사항**:
1. **UI 설정 창에 로깅 레벨 선택 추가**
   - 드롭다운 메뉴로 실시간 변경
   - 재시작 없이 적용

2. **개발 모드 자동 감지**
   ```python
   if not getattr(sys, "frozen", False):
       log_level = logging.DEBUG  # 개발 환경
   else:
       log_level = logging.INFO   # 릴리스 환경
   ```

3. **환경 변수 지원**
   ```python
   WF_LOG_LEVEL=DEBUG  # 환경 변수 우선
   ```

**작업**:
- 설정 창에 로깅 레벨 UI 추가
- 개발 모드 자동 DEBUG 활성화
- 환경 변수 지원 추가
- 로그 파일 로테이션 구현 (용량 제한)
- 성능 프로파일링 로그 정리

---

### 8. 다국어 지원 준비

**작업**:
- i18n 구조 설계
- 한국어/영어 전환 가능
- UI 문자열 외부화

---

### 9. 설정 백업/복원 기능

**작업**:
- 사용자 설정 내보내기/가져오기
- 앱 재설치 시 설정 복원
- 크레딧 정보는 제외

---

### 10. 업데이트 알림 시스템

**작업**:
- 새 버전 자동 체크
- Google Sheets 버전 정보 읽기
- 다운로드 링크 제공

---

### 11. 사용 통계 대시보드

**작업**:
- 앱별 사용 시간 추적
- 크레딧 사용 패턴 분석
- 구글 시트 집계 기능

---

## 완료된 작업 (Completed) ✅

### Phase 1: Critical (출시 준비)

- ✅ 버전 표시 및 경로 시스템 통합 (2025-12-02)
  - settings.json 경로 불일치 해결
  - frozen 모드 경로 통일
  - win32timezone 누락 문제 해결
- ✅ 빌드 시스템 표준화 (2025-11-30)
  - PostClean 옵션 추가
  - installer_resources 제거
  - 통합 테스트 구조 도입
- ✅ 크레딧 시스템 개선 (2025-11-02)
  - 정책 우선순위 설정
  - 체험판 크레딧 조정
- ✅ UI 및 성능 최적화 (2025-10-18~27)
  - "응답 없음" 현상 해결
  - 더미 창 깜빡임 제거
  - 단일 인스턴스 가드 추가

### Phase 2: 앱별 기능 구현

- ✅ Bom Exporter (BE)
  - 크레딧 시스템 통합
  - Google Sheets 동기화
  - 메모리 모니터링
  - 동적 타임아웃
  - 체험판 크레딧 10,000개 설정 파일 기반

- ✅ Conversion Verifier (CV)
  - 관리자 모드 구현
  - 검증 이력 로깅
  - 파일 무결성 검증 강화

- ✅ DWG Classifier (DC)
  - 메모리 정책 추가
  - DWG 버전 감지
  - 크레딧 로깅

- ✅ Korean Filename Normalizer (KFN)
  - 관리자 모드 구현
  - 정규화 옵션 추가
  - 미리보기 기능

- ✅ DWG Batch Print (DP)
  - 첫 릴리즈 (v1.0.0)

### Phase 3: 통합 및 배포

- ✅ v1.0.0 통합 릴리즈 (2025-12-29)
  - 5개 앱 통합 배포
  - 89개 테스트 모두 통과
  - 포터블 및 인스톨러 패키징

---

## 우선순위 변경 이력

- **2026-01-14**: 문서 통폐합 완료, Critical Task #1~#3 재확인
- **2025-12-29**: v1.0.0 릴리즈 완료, Critical 작업 제거
- **2025-12-02**: 경로 통일 완료로 상태 업데이트
- **2025-11-30**: 빌드 시스템 표준화 완료
- **2025-11-02**: 크레딧 시스템 개선 완료

---

## 테스트 체크리스트

### Task #1 (Bom_Exporter 앱명 통일) 테스트
- [ ] 신규 설치: 설정 파일이 `~/.wf_rpa/bom_exporter/`에 생성되는지 확인
- [ ] 버전 로딩: 앱 시작 시 올바른 버전 표시되는지 확인
- [ ] 크레딧 동기화: 정책이 정상적으로 로드되는지 확인
- [ ] 설정 저장: UI 설정 변경 후 저장/로드 정상 동작 확인
- [ ] 기존 사용자: (마이그레이션 구현 시) 구 설정이 신 경로로 이동되는지 확인

### Task #2 (관리자 모드) 테스트
- [ ] 진입: Progress Bar 클릭 후 비밀번호 입력으로 진입 확인
- [ ] UI 확장: 로그 창 및 관리자 버튼들이 표시되는지 확인
- [ ] 테스트 데이터: 생성/제거 기능이 정상 동작하는지 확인
- [ ] 자동 복귀: 30분 후 자동으로 일반 모드로 전환되는지 확인
- [ ] 종료 처리: 관리자 모드 중 앱 종료 시 정상 cleanup 확인

### Task #3 (파일 덮어쓰기) 테스트
- [ ] 덮어쓰기 확인 다이얼로그 표시
- [ ] "예" 선택 시 파일 덮어쓰기 정상 동작
- [ ] "아니오" 선택 시 작업 중단 확인
- [ ] 사용자 피드백 메시지 표시

---

## 일정 제안

### Phase 1: Critical (2주 이내)
- Week 1: Task #1 (Bom_Exporter 앱명 통일)
- Week 1: Task #2 (BE/DC 관리자 모드 구현)
- Week 2: Task #3 (파일 덮어쓰기 버그)

### Phase 2: High (1개월 이내)
- Week 2-3: Task #4 (초기화 시퀀스 표준화)
- Week 3-4: Task #5 (버전 파일 경로 표준화)

### Phase 3: Medium (2-3개월)
- Month 2: Task #6 (테스트 데이터 기능 통일)
- Month 2-3: Task #7 (로깅 레벨 설정 통일)
- Month 3: Task #8~#11 (추가 개선 아이디어 검토)

---

## 참고 자료

### 코드 참조
- 관리자 모드 구현: `50.data/conversion_verifier/ui_main.py` (Lines 1009-1090)
- Lazy 초기화: `30.apps/bom_exporter/ui_main.py` (Lines 430-470)
- 테스트 데이터: `50.data/korean_filename_normalizer/ui_main.py` (Lines 1870-1950)

### 관련 문서
- [DEVLOG.md](./DEVLOG.md) - 개발 일지
- [RELEASE_NOTES_v1.0.0.md](./RELEASE_NOTES_v1.0.0.md) - 릴리즈 노트
- [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) - 문제 해결
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - 배포 가이드

---

**마지막 업데이트**: 2026-01-14
**문서 버전**: 2.0
**정리**: 구현 완료 항목 제거, 실제 TODO만 남김
