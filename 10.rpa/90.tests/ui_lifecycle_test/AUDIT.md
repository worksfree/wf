# WF-ACT 인증 툴킷 감사 보고서

**감사 일자:** 2026-04-20  
**감사 범위:** `90.tests/ui_lifecycle_test/` 전체 (core/, suites/, 앱별 TestServer 구현)  
**수정 여부:** 이 문서는 분석 보고서이며 코드 수정 없음

---

## UI 실제 구동 테스트 가능 여부

**가능 (Windows 데스크탑 환경 기준)**

`python run_certification.py --app bom_exporter --level basic` 실행 시 실제 Tkinter UI가 열리고 IPC(TCP 소켓)로 테스트가 진행된다. 단, 열린 창의 시각적 내용(텍스트, 레이아웃)은 자동으로 확인할 수 없으며 사용자가 직접 확인해야 한다.

---

## 발견된 문제점

### [HIGH] 1. `test_12_continuous_work_sequence` 이중 simulate_work 호출

**파일**: `suites/cert_credits.py`

```python
for i in range(10):
    credits_before = self.get_credits()
    if credits_before < cost:
        result = self.simulate_work(file_count=1)  # 1번 호출
        if result.get('blocked'):
            interrupted_at = i
            break
    # break 없이 여기까지 오면 simulate_work 재호출
    result = self.simulate_work(file_count=1)      # 2번 호출 (버그)
    if result.get('success') and not result.get('blocked'):
        total_processed += 1
```

크레딧이 부족할 때 `simulate_work`가 예기치 않게 success를 반환하면 한 iteration에 2번 호출되어 크레딧 이중 차감 및 `total_processed` 오계산 발생.

---

### [HIGH] 2. `_test_simulate_work`가 실제 크레딧 차감 경로를 우회

**파일**: `30.apps/bom_exporter/ui_main.py`, `50.data/*/ui_main.py`

```python
# 현재 구현: 직접 JSON 조작
data = self._load_credit_data()
data["remaining_trial"] -= cost
self._save_credit_data(data)

# 실제 운영 코드 경로 (미호출)
# wf_credit_manager.deduct_credits(...)
```

테스트가 `wf_credit_manager.deduct_credits()`를 호출하지 않으므로, 실제 운영 크레딧 차감 로직(정책 검증, 예외 처리, Google Sheets 동기화 트리거)이 전혀 테스트되지 않음.

**영향**: "크레딧이 실제로 차감되는지 확인"이라는 목적을 달성하지 못함.

---

### [HIGH] 3. KFN `_test_simulate_work`에서 `interrupted` 필드 누락

**파일**: `50.data/korean_filename_normalizer/ui_main.py` (lines ~1751-1781)

bom_exporter는 크레딧 부족 시 `{"blocked": True, "interrupted": processed > 0, ...}` 반환.  
KFN은 `{"blocked": True, "remaining": remaining}` 반환 — `interrupted` 필드 없음.

`test_09_mid_work_exhaustion`이 `result.get('interrupted')`를 검사하는데 KFN에서 항상 `None` → 테스트가 의도한 검증을 수행하지 못함.

---

### [MEDIUM] 4. UI 오류 메시지 텍스트 검증 없음

크레딧 부족 시 사용자에게 표시되는 Tkinter 오류 메시지가 올바른지 테스트가 확인하지 않음. 현재 모든 크레딧 관련 테스트는 IPC 응답값(`result.get('blocked')`)만 검사.

"크레딧 부족 상황에서 제대로 된 오류 메시지를 내는지" 검증하려면 `get_ui_state()`로 메시지 텍스트를 읽고 기댓값과 비교하는 assertion 추가 필요.

---

### [MEDIUM] 5. `_test_set_credits(0)` 시 `usage_history` 오염

**파일**: `30.apps/bom_exporter/ui_main.py`

```python
# 크레딧을 0으로 설정할 때 삽입되는 더미 엔트리
data["usage_history"].append({
    "timestamp": "2000-01-01T00:00:00",
    "credits_used": 0,
    "operation": "wf_act_test_marker",
    "details": "Credits set to 0 for testing"
})
```

`test_20_credit_usage_log_after_work`가 `initial_count = len(usage_history)`를 기준으로 새 로그 생성 여부를 검사하는데, 이 더미 엔트리가 `initial_count`를 올려 카운트 오류 유발 가능.

---

### [MEDIUM] 6. UI 표시 업데이트 레이스 컨디션 (`test_07`)

`_test_set_credits()` 내부에서 `self.master.after(0, self.update_credit_display)`로 UI 업데이트를 큐잉한 뒤 IPC 응답을 즉시 반환. 직후 `get_ui_state()`로 `credits_display`를 읽으면 Tkinter 이벤트 루프가 아직 `after(0)` 콜백을 처리하기 전일 수 있어 간헐적 실패 가능.

---

### [LOW] 7. `test_01_get_credits` 크레딧 매니저 초기화 검증 미흡

`_ensure_credit_manager` 타임아웃 시 `remaining = 0` 반환 → `isinstance(0, int)` 통과로 테스트 PASS. 크레딧 매니저가 실제로 초기화됐는지 확인하지 않음.

---

### [LOW] 8. `terminate_app(wait_time=0.5)` 뮤텍스 해제 타이밍

단일 인스턴스 뮤텍스가 0.5초 안에 해제되지 않으면 다음 테스트 앱 실행 시 "이미 실행 중" 오류 발생 가능. 느린 환경(I/O 부하, 백신 스캔)에서 간헐적 실패 원인.

---

## 요약

| # | 문제 | 심각도 | 영향 앱 |
|---|------|--------|---------|
| 1 | `test_12` 이중 simulate_work 호출 | HIGH | 전체 |
| 2 | simulate_work가 실제 deduct_credits 우회 | HIGH | 전체 |
| 3 | KFN `interrupted` 필드 누락 | HIGH | kfn |
| 4 | UI 오류 메시지 텍스트 미검증 | MEDIUM | 전체 |
| 5 | set_credits(0)가 usage_history 오염 | MEDIUM | 전체 |
| 6 | UI 표시 레이스 컨디션 (test_07) | MEDIUM | 전체 |
| 7 | get_credits 초기화 검증 미흡 | LOW | 전체 |
| 8 | 뮤텍스 해제 타이밍 불안정 | LOW | 전체 |

**핵심 결론**: 문제 2가 가장 중요. 현재 WF-ACT는 크레딧 차감의 _결과_(JSON 값 변화)는 검증하지만 실제 운영 코드 경로(`deduct_credits`)는 테스트하지 않음. 진정한 크레딧 차감 검증을 위해 `_test_simulate_work`가 `wf_credit_manager.deduct_credits()`를 직접 호출하도록 수정 필요.
