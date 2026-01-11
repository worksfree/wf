# 🧪 credit_changed 플래그 동기화 테스트 가이드

## 📋 준비사항

1. **앱을 최소 한 번 실행**해서 `credit_history.json` 파일 생성
2. **VSCode를 관리자 권한으로 실행** (선택사항, 편의를 위해)

---

## ✅ 시나리오 1: 앱 시작 시 동기화 (credit_changed=True)

### 목표
이전 세션에서 크레딧을 사용했지만 동기화 실패한 경우, 앱 재시작 시 자동 동기화 검증

### 테스트 순서

#### 1단계: credit_changed 플래그를 True로 설정

**방법 A - 수동 편집 (가장 간단)**
```
파일 열기: C:\Users\HP\.wf_rpa\bom2excel\credit_history.json

"credit_changed": false  →  "credit_changed": true  으로 변경
저장
```

**방법 B - 유틸리티 사용**
```powershell
cd d:\drive_files\10.worksfree\10.rpa\10.common
python manual_set_credit_changed.py

# 1. bom2excel 선택
# 2. "credit_changed = True 설정" 선택
```

#### 2단계: 앱 실행

```powershell
cd d:\drive_files\10.worksfree\10.rpa\30.apps\bom2excel
python ui_main.py
```

#### 3단계: 로그 확인

앱 시작 시 다음 로그가 출력되어야 함:

```
✅ 성공 케이스:
🔄 앱 시작: credit_changed=True 감지, 구글 시트 동기화 시도...
✅ 시작 시 동기화 성공: ...

⚠️ 실패 케이스 (동기화 조건 미충족):
🔄 앱 시작: credit_changed=True 감지, 구글 시트 동기화 시도...
⚠️ 시작 시 동기화 실패: ...

ℹ️ 생략 케이스 (변경사항 없음):
🔄 앱 시작: credit_changed=False, 동기화 생략
```

#### 4단계: 결과 확인

동기화 성공 시:
- `credit_changed`가 `false`로 변경됨
- `last_synced` 타임스탬프가 업데이트됨

```powershell
# 확인 명령
python manual_set_credit_changed.py
# 3. 현재 상태만 확인
```

---

## ✅ 시나리오 2: 크레딧 사용 후 종료 시 동기화

### 목표
정상 플로우에서 크레딧 사용 → 종료 시 자동 동기화 검증

### 테스트 순서

#### 1단계: 초기 상태 확인

```powershell
python manual_set_credit_changed.py
# 3. 현재 상태만 확인

# credit_changed: False 확인
```

#### 2단계: 앱 실행 및 크레딧 사용

```powershell
cd d:\drive_files\10.worksfree\10.rpa\30.apps\bom2excel
python ui_main.py

# GUI에서:
# 1. DWG 폴더 선택
# 2. 파일 처리 (크레딧 사용)
```

#### 3단계: 크레딧 사용 로그 확인

```
✅ 크레딧 사용 성공 시:
💰 크레딧 차감: 100 크레딧 사용 (잔액: 1900)
```

#### 4단계: 앱 종료

```
X 버튼 클릭 또는 종료 버튼 클릭
```

#### 5단계: 종료 로그 확인

```
✅ 동기화 성공 케이스:
🔄 앱 종료 시 크레딧 동기화 시도...
[SYNC-EXIT] {'success': True, 'synced': True, ...}

⚠️ 동기화 실패 케이스:
🔄 앱 종료 시 크레딧 동기화 시도...
[SYNC-EXIT] {'success': False, ...}
⚠️ 다음 앱 시작 시 재시도됩니다.
```

#### 6단계: 결과 확인

```powershell
python manual_set_credit_changed.py
# 3. 현재 상태만 확인

# 동기화 성공 시:
#   credit_changed: False
#   last_synced: [최신 타임스탬프]
```

---

## ✅ 시나리오 3: 크레딧 사용 없이 종료

### 목표
크레딧을 사용하지 않으면 동기화가 불필요함을 검증

### 테스트 순서

#### 1단계: 초기 상태 확인

```powershell
python manual_set_credit_changed.py
# 2. credit_changed = False 설정 (명시적 초기화)
```

#### 2단계: 앱 실행 (크레딧 사용 안 함)

```powershell
cd d:\drive_files\10.worksfree\10.rpa\30.apps\bom2excel
python ui_main.py

# GUI에서:
# - 아무 작업도 하지 않고 바로 종료
```

#### 3단계: 시작 로그 확인

```
🔄 앱 시작: credit_changed=False, 동기화 생략
```

#### 4단계: 종료 로그 확인

```
(동기화 관련 로그 없음)
→ credit_changed=False이므로 동기화 시도 안 함
```

---

## 🔍 디버깅 팁

### 로그 파일 위치

```
C:\Users\HP\.wf_rpa\bom2excel\.logs\app.log
```

### credit_history.json 위치

```
C:\Users\HP\.wf_rpa\bom2excel\credit_history.json
```

### 주요 확인 포인트

1. **credit_changed 플래그**
   - 크레딧 사용 성공 시: `true`로 변경
   - 동기화 성공 시: `false`로 리셋

2. **last_synced 타임스탬프**
   - 동기화 성공 시마다 업데이트

3. **session_usage_amount**
   - 크레딧 사용 시 누적
   - 동기화 성공 시 0으로 리셋

---

## 🚨 문제 해결

### PermissionError 발생 시

**증상**: `PermissionError: [Errno 13] Permission denied`

**원인**: 파일이 읽기 전용이거나 다른 프로세스가 사용 중

**해결방법**:
1. VSCode를 관리자 권한으로 재실행
2. 또는 수동으로 JSON 파일 편집

### 동기화가 안 될 때

**확인사항**:
1. 사용자 이메일이 등록되어 있는가?
2. Google Sheets 연결이 정상인가?
3. `applied_purchase_ids`에 해당 transaction_id가 이미 있는가?

**강제 동기화 시도**:
```python
# Python 콘솔에서
from wf_credit_manager import CreditManager
cm = CreditManager('bom2excel')
result = cm.check_and_sync_credits()
print(result)
```

---

## 📊 예상 결과 요약

| 시나리오 | 시작 시 동기화 | 종료 시 동기화 | credit_changed 최종값 |
|---------|-------------|-------------|---------------------|
| 이전 미동기화 건 | ✅ 시도 | - | False (성공 시) |
| 정상 사용 플로우 | ❌ 생략 | ✅ 시도 | False (성공 시) |
| 사용 안 함 | ❌ 생략 | ❌ 생략 | False (유지) |

---

## 🎯 검증 체크리스트

- [ ] 앱 시작 시 credit_changed=True면 동기화 시도
- [ ] 크레딧 사용 성공 시 credit_changed=True 설정
- [ ] 앱 종료 시 credit_changed=True면 동기화 시도
- [ ] 동기화 성공 시 credit_changed=False로 리셋
- [ ] 동기화 실패 시 credit_changed=True 유지 (다음 시작 시 재시도)
- [ ] 크레딧 사용 없으면 동기화 시도 안 함

---

**테스트 완료 후**: 각 시나리오별 로그 스크린샷을 저장하면 나중에 참고하기 좋습니다! 📸
