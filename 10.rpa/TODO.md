# TODO: 출시 후 구조 개선 작업

> 작성일: 2025-12-01  
> 우선순위: 🔴 즉시 / 🟡 단계적 / 🟢 장기

---

## 🔴 즉시 수정 필요 (Critical Priority)

### 1. Bom_Exporter 앱명 통일
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
```python
# 30.apps/Bom_Exporter/ui_main.py
# Line 89: _load_version_info() 함수
settings_file = Path.home() / ".wf_rpa" / "bom2excel" / "settings.json"
→ settings_file = Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"

# Line 96: settings_file 개발 모드 경로
settings_file = Path(__file__).parent / "config" / "bom2excel" / "settings.json"
→ settings_file = Path(__file__).parent / "config" / "bom_exporter" / "settings.json"

# 모든 "bom2excel" 문자열 검색 후 "bom_exporter"로 변경
# 주의: 파일명, 폴더명은 유지 (빌드 스크립트 등)
```

**체크리스트**:
- [ ] ui_main.py의 모든 `bom2excel` → `bom_exporter` 변경
- [ ] automation.py 내 app_name 참조 확인
- [ ] config 폴더명 변경: `config/bom2excel` → `config/bom_exporter`
- [ ] 기존 사용자 마이그레이션 스크립트 작성 (선택)
- [ ] 빌드 후 테스트: 설정 로드, 크레딧 동기화 확인

---

### 2. BE/DC 관리자 모드 구현
**현재 상태**:
- ✅ **CV, KFN**: Progress Bar 클릭으로 관리자 모드 진입 가능
- ❌ **BE, DC**: 관리자 모드 변수는 있으나 진입 방법 없음

**추가 필요 기능**:
1. Progress Bar 클릭 이벤트 바인딩
2. 관리자 비밀번호 입력 다이얼로그
3. 관리자 모드 UI 확장 (로그 창, 테스트 버튼)
4. 테스트 데이터 생성/제거 기능

**구현 위치**:
```python
# 30.apps/bom_exporter/ui_main.py
# 50.data/dwg_classifier/ui_main.py

# init_ui() 또는 create_ui_elements() 내 추가
self.progress_bar_label.bind("<Button-1>", lambda e: self.toggle_admin_mode())

# toggle_admin_mode() 메서드 추가 (CV/KFN 참고)
def toggle_admin_mode(self):
    if not self.is_admin_mode:
        password = simpledialog.askstring("관리자 모드", "비밀번호를 입력하세요:", show="*")
        if password == self.admin_password:
            self._enter_admin_mode()
        else:
            messagebox.showerror("오류", "비밀번호가 틀렸습니다.")
    else:
        self._exit_admin_mode()

# _enter_admin_mode(), _exit_admin_mode() 메서드 추가
# _create_test_data(), _clear_test_data() 메서드 추가
```

**참고 파일**:
- `50.data/conversion_verifier/ui_main.py` (Lines 1009-1090)
- `50.data/korean_filename_normalizer/ui_main.py` (Lines 1770-1870)

**체크리스트**:
- [ ] BE에 관리자 모드 진입 메커니즘 추가
- [ ] DC에 관리자 모드 진입 메커니즘 추가
- [ ] 테스트 데이터 생성 기능 구현 (BE)
- [ ] 테스트 데이터 생성 기능 구현 (DC)
- [ ] 관리자 모드 UI 확장 테스트

---

## 🟡 단계적 개선 (High Priority)

### 3. 초기화 시퀀스 표준화
**현재 상황**:
| 앱 | WFM 초기화 | CreditManager 초기화 | 성능 |
|----|-----------|---------------------|------|
| CV | Blocking (즉시) | 헬퍼 사용 (즉시) | 중간 |
| BE | Lazy (백그라운드) | Lazy (백그라운드) | 빠름 ⚡ |
| DC | Early blocking | Lazy (백그라운드) | 중간 |
| KFN | Blocking (즉시) | 즉시 | 느림 |

**표준 패턴 (BE 방식 채택)**:
```python
def __init__(self, master):
    # 1. 필수 초기화만 (UI 표시 전)
    self.master = master
    self.logger = get_app_logger(...)
    self.config = get_config()
    self.ui = get_adaptive_ui_settings()
    
    # 2. Lazy 매니저 (백그라운드 초기화 예정)
    self.wf_manager = None
    self.credit_manager = None
    self._wfm_available = WFM_AVAILABLE
    
    # 3. UI 먼저 생성 (빠른 표시)
    self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
    self.init_ui()
    
    # 4. 백그라운드 초기화 스케줄
    self.master.after(100, self._lazy_init_managers)
    self.master.after(200, lambda: threading.Thread(
        target=self.create_user_directories, daemon=True
    ).start())

def _lazy_init_managers(self):
    """백그라운드에서 WFM/CreditManager 초기화"""
    def _worker():
        # Config 정책 로딩
        if self.config and hasattr(self.config, "load_policies_async"):
            self.config.load_policies_async()
        
        # WorksFree 매니저 초기화
        if self._wfm_available and WorksFreeManager:
            self.wf_manager = WorksFreeManager()
            self.is_registered_user = self.wf_manager.is_registered()
            self.master.after(0, self.update_registration_button)
        
        # CreditManager 초기화
        if CreditManager and self.wf_manager:
            self.credit_manager = init_credit_and_policy_managers(...)
            self.master.after(0, self.update_credit_display)
            self.master.after(300, self._async_refresh_policies)
    
    threading.Thread(target=_worker, daemon=True).start()
```

**이점**:
- UI가 300-500ms 더 빠르게 표시됨
- 네트워크 동기화가 UI 블로킹하지 않음
- 사용자가 즉시 앱 사용 가능

**체크리스트**:
- [ ] CV를 BE 패턴으로 리팩토링
- [ ] DC를 BE 패턴으로 리팩토링
- [ ] KFN을 BE 패턴으로 리팩토링
- [ ] 각 앱 startup time 측정 및 비교
- [ ] 크레딧 동기화 오류 처리 강화

---

### 4. 버전 파일 경로 표준화
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

**수정 범위**:
```python
# 30.apps/bom_exporter/ui_main.py (Line 89)
settings_file = Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"

# 50.data/dwg_classifier/ui_main.py (추가 확인 필요)
settings_file = Path.home() / ".wf_rpa" / "dwg_classifier" / "settings.json"
```

**기존 사용자 대응**:
- Option A: 마이그레이션 스크립트 (구 → 신 경로 자동 이동)
- Option B: 둘 다 체크 (구 경로 있으면 로드, 없으면 신 경로)

**체크리스트**:
- [ ] BE 경로 변경 (Task #1과 통합)
- [ ] DC 경로 변경
- [ ] 마이그레이션 로직 추가 (선택)
- [ ] 빌드 후 신규 설치 테스트
- [ ] 기존 사용자 업그레이드 테스트

---

## 🟢 장기 개선 (Medium Priority)

### 5. 테스트 데이터 기능 통일
**현재 상태**:
- ✅ CV, KFN: 완전한 테스트 데이터 생성/제거 구현
- ❌ BE, DC: 테스트 기능 없음

**용도**:
- 개발/QA 환경에서 빠른 테스트
- 크레딧 시스템 검증
- 데모/시연용 데이터 준비

**구현 방법**:
```python
# BE/DC에 추가
def _create_test_data(self):
    """테스트용 크레딧 데이터 생성"""
    try:
        if self.credit_manager:
            # 테스트 정책 설정
            test_policy = {
                "trial_credits": 10000,
                "credit_per_work": 50,
                "available_work": 200,
            }
            # 정책 업데이트 및 동기화
            # ...
        messagebox.showinfo("완료", "테스트 데이터가 생성되었습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"테스트 데이터 생성 실패: {e}")

def _clear_test_data(self):
    """테스트 데이터 제거 및 초기화"""
    try:
        if self.credit_manager:
            # 정책 리셋
            # 크레딧 초기화
            # 구글 시트 동기화
            # ...
        messagebox.showinfo("완료", "테스트 데이터가 제거되었습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"테스트 데이터 제거 실패: {e}")
```

**체크리스트**:
- [ ] BE에 테스트 데이터 기능 추가
- [ ] DC에 테스트 데이터 기능 추가
- [ ] 관리자 모드 UI에 버튼 추가
- [ ] 환경 변수 제어 추가 (`WF_TEST_MODE=1`)
- [ ] 테스트 시나리오 문서 작성

---

### 6. 로깅 레벨 설정 통일
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

**체크리스트**:
- [ ] 설정 창에 로깅 레벨 UI 추가
- [ ] 개발 모드 자동 DEBUG 활성화
- [ ] 환경 변수 지원 추가
- [ ] 로그 파일 로테이션 구현 (용량 제한)
- [ ] 성능 프로파일링 로그 정리

---

## 📝 추가 개선 아이디어

### 7. 다국어 지원 준비
- i18n 구조 설계
- 한국어/영어 전환 가능
- UI 문자열 외부화

### 8. 설정 백업/복원 기능
- 사용자 설정 내보내기/가져오기
- 앱 재설치 시 설정 복원
- 크레딧 정보는 제외

### 9. 업데이트 알림 시스템
- 새 버전 자동 체크
- Google Sheets 버전 정보 읽기
- 다운로드 링크 제공

### 10. 사용 통계 대시보드
- 앱별 사용 시간 추적
- 크레딧 사용 패턴 분석
- 구글 시트 집계 기능

---

## 🔍 테스트 체크리스트

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

### Task #3 (초기화 시퀀스) 테스트
- [ ] UI 표시 속도: Lazy init 적용 후 startup time 측정
- [ ] 크레딧 로딩: 백그라운드 초기화 후 UI에 정상 반영되는지 확인
- [ ] 에러 핸들링: 네트워크 오류 시 앱이 정상 동작하는지 확인
- [ ] 동기화 타이밍: 정책 sync가 적절한 시점에 호출되는지 확인

---

## 📅 일정 제안

### Phase 1: Critical (출시 후 1주 이내)
- Week 1: Task #1 (Bom_Exporter 앱명 통일)
- Week 1: Task #2 (BE/DC 관리자 모드 구현)

### Phase 2: High (출시 후 1개월 이내)
- Week 2-3: Task #3 (초기화 시퀀스 표준화)
- Week 3-4: Task #4 (버전 파일 경로 표준화)

### Phase 3: Medium (출시 후 2-3개월)
- Month 2: Task #5 (테스트 데이터 기능 통일)
- Month 2-3: Task #6 (로깅 레벨 설정 통일)
- Month 3: 추가 개선 아이디어 검토

---

## 📚 참고 자료

### 코드 참조
- 관리자 모드 구현: `50.data/conversion_verifier/ui_main.py` (Lines 1009-1090)
- Lazy 초기화: `30.apps/bom_exporter/ui_main.py` (Lines 430-470)
- 테스트 데이터: `50.data/korean_filename_normalizer/ui_main.py` (Lines 1870-1950)

### 관련 이슈
- Credit Policy 통합: 완료 (2025-11-27)
- 앱 명명 규칙 통일: 완료 (2025-11-28)
- UI 정리 (원숫자 제거): 완료 (2025-12-01)

### 연락처
- 개발팀: insung.lee@worksfree.co.kr
- 리포지토리: worksfree/rpa_pro (main branch)

---

**마지막 업데이트**: 2025-12-01  
**작성자**: GitHub Copilot (Claude Sonnet 4.5)  
**버전**: 1.0
