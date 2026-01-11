# 테스트 플랜 모음

본 문서는 테스트 설계 문서를 통합하여 관리합니다.

---

## 1) 크레딧 시스템 테스트 시나리오

# 크레딧 시스템 테스트 시나리오

## 테스트 앱 선정: Korean Filename Normalizer
- 빠른 실행 속도 (파일 처리 몇 초)
- 명확한 작업 단위 (파일 1개 = 1크레딧)
- 기존 GUI 구조 활용

## 테스트 시나리오

### 1. 초기 설치 및 등록
- [ ] 체험판 설치 (크레딧 5개)
- [ ] 사용자 등록 (이메일, 하드웨어 지문)
- [ ] 초기 크레딧 확인

### 2. 체험판 크레딧 사용
- [ ] 파일 3개 처리 (크레딧 3개 사용)
- [ ] 크레딧 표시 업데이트 확인
- [ ] 남은 크레딧 2개 확인

### 3. 크레딧 소진 전 구매
- [ ] 크레딧 1개 남은 상태에서 구매
- [ ] 구매 내역 반영 확인
- [ ] 크레딧 새로고침 기능 테스트

### 4. 크레딧 완전 소진 후 구매
- [ ] 모든 크레딧 소진
- [ ] 크레딧 없음 알림 확인
- [ ] 구매 후 즉시 사용 가능 여부

### 5. 작업 중 크레딧 소진
- [ ] 파일 10개 준비, 크레딧 3개 상태
- [ ] 작업 시작 후 중간에 크레딧 소진
- [ ] 부분 완료 처리 확인

### 6. 크레딧 동기화 테스트
- [ ] 다른 장치에서 구매
- [ ] 수동 동기화 버튼 클릭
- [ ] 자동 동기화 (앱 시작/종료 시)

### 7. 구매 내역 동기화
- [ ] 여러 번 구매 후 반영
- [ ] 중복 적용 방지 확인
- [ ] 구매 ID 기반 추적

## 테스트 데이터 준비

### 파일 생성 스크립트
```python
# test_files_creator.py
import os

def create_test_files(count=10):
    """자소 분리 테스트 파일 생성"""
    test_dir = "test_korean_files"
    os.makedirs(test_dir, exist_ok=True)
    
    for i in range(count):
        filename = f"테스트파일_{i:02d}.txt"
        import unicodedata
        nfd_name = unicodedata.normalize('NFD', filename)
        
        with open(os.path.join(test_dir, nfd_name), 'w', encoding='utf-8') as f:
            f.write(f"테스트 파일 내용 {i}")
    
    print(f"{count}개의 테스트 파일이 {test_dir}에 생성되었습니다.")

if __name__ == "__main__":
    create_test_files(15)
```

---

## 2) Multi‑App Lifecycle Test Scenarios

# WorksFree RPA — Multi‑App Lifecycle Test Scenarios

본 계획은 설치 → 체험판 → 크레딧 사용 → 구매 → 교차 앱 설치 → 단일 인스턴스 강제 → pending‑list 재개 흐름을 4개 앱 전반에 걸쳐 검증합니다.

### Pre‑Flight
- Apps: B2E, DWG, CV, KFN
- Must‑verify: 등록(5분 코드), 크레딧 차감/부족, pending list, 스캔 토글, 단일 인스턴스 등

### Test Data Guidance
- B2E: .slddrw, DWG: .dwg, CV: 매칭된 .slddrw/.dwg, KFN: 자소분리 파일 포함 폴더

### Environment Reset Between Cases
```pwsh
Remove-Item -Recurse -Force "$HOME\.wf_rpa"
```

### Scenarios 요약
- 시나리오 1: B2E → 부족 → 구매 → 재개 → DWG 단일 인스턴스 확인
- 시나리오 2: DWG → 부족 → 구매 → 재개 → CV 단일 인스턴스
- 시나리오 3: CV → 구매 → B2E 설치 → 스캔 토글 + 단일 인스턴스
- 시나리오 4: KFN (자소분리 집계) → DWG 설치
- 시나리오 5: B2E 영구 라이선스 전환 중
- 시나리오 6: 4앱 설치 후 단일 인스턴스 견고성
- 시나리오 7: B2E 크레딧 동기화 실패/복구
- 시나리오 8: CV → KFN 지속성 + 스캔 토글

### 공통 체크
- 등록 타이머/재전송, 크레딧 갱신, pending list 생성/제거, UI 토글/최근 경로, 단일 인스턴스

### 산출물
- 스크린샷/로그, `~/.wf_rpa/...` 설정과 크레딧 로그, `wf_pending_list.txt` 스냅샷
