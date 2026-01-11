# WorksFree RPA – Credit Continuation TODO

이 문서는 "크레딧 부족 시 작업 이어가기" 기능만을 위한 계획과 실행 목록을 다룹니다. 다른 영역(정적 테스트, 배포, 참조)은 여기에 기록하지 않습니다. 필요 시 새로운 하위 항목을 이 섹션 하단의 Next actions 또는 별도 Subtopics 아래에 추가하세요.

## 목표 (Goal)

크레딧이 부족해도 진행 중인 작업의 손실을 최소화하고 사용자 경험을 매끄럽게 유지하는 방안 제공.

### 실행 모드 (조합 가능)
- Grace 모드: 현재 배치만 마무리 후 부족분을 부채(debt)로 표시, 구매 후 청산.
- Deferred Queue: 남은 파일/작업을 큐에 저장하고 크레딧 보충 시 자동 실행.
- Checkpoint/Resume: 처리 중간 상태를 저장(checkpoint) 후 재개 가능.
- Split Runs: 남은 크레딧 한도 내로 배치 자동 축소 후 사용자 선택 유도.
- Admin Override: 정책 플래그 또는 ENV로 한시적 초과 허용.

### 최소 계약 (Contract)
- 입력: app_name, per_item_cost, remaining_credits, job_list(ids/files), user_email
- 출력: continuation_plan {mode, allowed_now, queued_count, debt?, checkpoint_id}
- 영속성: `~/.wf_rpa/{app}/continuation.json` (또는 dev 모드: `./config/continuation.json`)
- 오류 형태: no_credits, policy_disabled, invalid_jobs, corrupted_session

### UX 아이디어
- 비차단 토스트: “부분 실행 / 나머지 큐 / 취소” 선택.
- 상태 배지: 큐 대기 개수 + Resume 버튼.
- 구매 후 스낵바: “대기 중 N건 실행 가능 → [지금 실행]”.

### 데이터 모델 (초안)
`continuation.json`
- version: 1
- last_updated: ISO8601
- queued_jobs: [{id, path, size, created_at}]
- checkpoints: [{id, state, created_at, app_version}]
- debt: {amount, created_at} | null

### 엣지 케이스
- 부분 처리 후 앱 크래시 → checkpoint 원자적(write temp → rename)
- 큐 저장 후 파일 경로 변경/삭제
- 세션 중 정책 변경으로 per_item_cost 상승
- 사용자 PC 교체 (로컬 상태 미존재) → graceful fallback
- 무료/영구 라이선스 앱은 이 로직 건너뜀

### 로깅 & 지표
- 모드·큐 크기·처리 시간·checkpoint id 로깅
- 지표: queued_count, resumed_count, debt_cleared, split_runs_ratio

### 점진 배포 계획
- Feature flag: `WF_CONTINUATION_ENABLED=1` (prod 기본 off)
- 1차: bom2excel에 split + queue 기능만 도입
- 측정 후 다른 앱 확장 (classifier 등)
- backward compatible: 파일 없거나 파손 시 기존 동작 유지

### Open Questions
- Debt 만료/승인(수동 vs 자동)
- Queue 용량 및 삭제 정책 (LRU? 오래된 것부터?)
- 앱 간 공유 큐 필요 여부 (크레딧 풀링 시나리오?)

### Next Actions
- [ ] continuation.json 스키마 & 헬퍼 (load/save/atomic)
- [ ] `plan_continuation(job_count)` API 설계
- [ ] bom2excel: split-run + queue 구현 (happy path)
- [ ] 토스트 UI + Resume 엔트리 포인트 추가
- [ ] 테스트: 부분 실행, 구매 후 재개, 크래시 복구
- [ ] debt 기록/청산 흐름 정의
- [ ] 큐 항목 파일 변조 검증 로직 (존재/크기/해시)
- [ ] ENV flag 적용 지점(App 초기화)
- [ ] checkpoint 저장 구조 확정 (state 최소 필드 결정)


### Subtopics (추가 시 아래에 이어서 작성)
_예: Permanent 라이선스와 queue 상호작용, UI 세부 문구, 다국어 처리 등_

---

