# WF-ACT (WF-RPA App Certification Toolkit)

WF-RPA 앱 라이프사이클 인증 툴킷입니다. Java의 TCK(Technology Compatibility Kit)와 유사하게, 앱이 정의된 라이프사이클 요구사항을 충족하는지 검증합니다.

## 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                    WF-ACT Certification                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Registration│  │   Credit    │  │    State    │            │
│  │    Suite    │  │    Suite    │  │    Suite    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Config    │  │  Recovery   │  │     UI      │            │
│  │    Suite    │  │    Suite    │  │    Suite    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  결과: 🥇 FULL CERTIFIED | 76/76 passed | Report Generated     │
└─────────────────────────────────────────────────────────────────┘
```

## 인증 레벨

| 레벨 | 배지 | 설명 | 테스트 수 |
|------|------|------|----------|
| **FULL** | 🥇 | 모든 테스트 통과 (엣지 케이스 포함) | 76+ |
| **STANDARD** | 🥈 | 일반 시나리오 통과 | 60 |
| **BASIC** | 🥉 | 핵심 기능 통과 | 40 |
| **NONE** | ❌ | 인증 실패 | - |

## 테스트 스위트

### 1. Deployment Suite (배포 파일)
- BAT 파일 존재 확인 (setup, shortcuts, uninstall 등)
- wf_rpa_config.json 구조 검증
- DEV/RELEASE 환경 분리 확인

### 2. Package Integrity Suite (패키지 무결성) 🆕
- **EXE 모드 전용**: 패키징된 실행 파일의 내부 구조 검증
- _internal 디렉토리 구조
- RELEASE/DEV 크리덴셜 파일 포함 여부
- 번들 settings.json 버전 정확성
- Google Sheets 설정 일관성
- NSIS 설치 파일 존재 (BuildType=3)

### 3. Config Suite (설정 관리)
- policy.json 로드 및 검증
- settings.json 검증
- 설정 일관성 확인

### 4. Security Suite (보안 규칙)
- 크리덴셜 파일 암호화 확인
- 민감 정보 노출 방지
- 안전한 파일 권한 설정

### 5. Registration Suite (등록 라이프사이클)
- 미등록 상태 감지
- 이메일 등록
- 중복 등록 방지
- 등록 정보 동기화

### 6. Credit Suite (크레딧 시스템) ⭐
- 크레딧 조회/설정
- 작업당 크레딧 차감 (BE: 100, DC: 50, DP: 40)
- 크레딧 부족 시 작업 차단
- **작업 중 크레딧 소진 → 중단**
- **크레딧 구매 후 작업 재개**
- 연속 작업 시퀀스

### 7. State Suite (상태 관리)
- 상태 유지
- 설정 저장/로드
- 세션 관리

### 8. Recovery Suite (오류 복구)
- 잘못된 입력 처리
- 연속 오류 후 복구
- 부분 작업 실패 복구

### 9. UI Suite (UI 응답성)
- 버튼 상태 반영
- 응답 시간 확인
- 블로킹 없음 확인

## 사용법

### 기본 실행
```batch
run_certification.bat
```

### 명령줄 옵션
```bash
# 모든 앱, FULL 레벨 인증 (DEV 모드 - 소스코드)
python run_certification.py

# EXE 모드 - 패키징된 실행 파일 테스트
python run_certification.py --exe
python run_certification.py --app be dp ar --exe -l full

# 특정 앱만 인증
python run_certification.py --app bom_exporter
python run_certification.py --app be dc  # 단축명 사용

# 특정 레벨까지만 테스트
python run_certification.py --level basic
python run_certification.py --level standard

# 테스트 목록 확인
python run_certification.py --list

# 결과 저장 위치 지정
python run_certification.py --output ./my_results

# EXE 후보 디렉토리 지정 (기본: D:/release/candidates)
python run_certification.py --exe --candidates-dir D:/my_builds
```

### 앱 단축명
| 단축명 | 앱 이름 |
|--------|---------|
| be | bom_exporter |
| dc | dwg_classifier |
| dp, dbp | dwg_batch_print |
| cv | conversion_verifier |
| kfn | korean_filename_normalizer |
| ar | attribute_reset |
| qr | qrcode_generator |

## 실행 모드

### DEV 모드 (기본)
- **대상**: Python 소스 코드
- **용도**: 개발 중 빠른 검증, 코드 수정 후 즉시 테스트
- **실행**: `python run_certification.py`
- **특징**: 
  - TestServer 모듈 직접 임포트
  - 앱 수정 후 재빌드 불필요
  - 134개 항목 전체 테스트 가능

### EXE 모드
- **대상**: 패키징된 실행 파일 (.exe)
- **용도**: 배포 전 최종 검증, 실제 사용 환경 테스트
- **실행**: `python run_certification.py --exe`
- **특징**:
  - D:/release/candidates/ 폴더의 exe 테스트
  - PackageIntegritySuite 추가 실행 (파일 구조, 크리덴셜 검증)
  - 실제 배포 패키지 완전성 확인

**권장 워크플로우**:
1. 코드 수정 → DEV 모드 인증 (빠름)
2. 빌드 완료 → EXE 모드 인증 (최종 검증)
3. 100% 통과 → 배포

## 자동화된 빌드 & 인증

빌드와 인증을 한 번에 실행:

```powershell
# 루트 디렉토리에서 실행
.\auto_build_and_certify.ps1

# 프로세스:
# 1. 7개 앱 병렬 빌드 (10분)
# 2. 빌드 결과를 D:/release/candidates로 복사
# 3. verify_exe_package.ps1 실행 (빠른 검증)
# 4. WF-ACT 인증 실행 (DEV 모드, 938개 테스트)
# 5. HTML 리포트 생성
```
| dp | dwg_batch_print |
| cv | conversion_verifier |
| kfn | korean_filename_normalizer |

## 앱에 테스트 모드 추가하기

앱이 WF-ACT 인증을 받으려면 `--test-mode` 플래그를 지원해야 합니다.

### 1. TestServer 임포트
```python
# ui_main.py
import sys
sys.path.insert(0, 'D:/drive_files/10.worksfree/10.rpa/90.tests/ui_lifecycle_test')

from core import TestServer
```

### 2. 테스트 서버 초기화
```python
class App:
    def __init__(self):
        # ... 기존 초기화 코드 ...

        if '--test-mode' in sys.argv:
            self.init_test_server()

    def init_test_server(self):
        self.test_server = TestServer(app_name='bom_exporter')

        # 핸들러 등록
        self.test_server.register_handlers({
            'get_credits': self.get_credits,
            'set_credits': self.set_credits,
            'add_credits': self.add_credits,
            'get_registration_status': self.get_registration_status,
            'register': self.register,
            'clear_registration': self.clear_registration,
            'simulate_work': self.simulate_work,
            'get_state': self.get_state,
            'get_policy': self.get_policy,
            'get_settings': self.get_settings,
            # ... 기타 핸들러 ...
        })

        self.test_server.start()
```

### 3. 필수 핸들러 구현
```python
def get_credits(self) -> int:
    """현재 크레딧 반환"""
    return self.credit_manager.get_credits()

def set_credits(self, amount: int) -> bool:
    """크레딧 설정"""
    self.credit_manager.set_credits(amount)
    return True

def add_credits(self, amount: int) -> bool:
    """크레딧 추가 (구매 시뮬레이션)"""
    current = self.credit_manager.get_credits()
    self.credit_manager.set_credits(current + amount)
    return True

def simulate_work(self, file_count: int = 1) -> dict:
    """작업 시뮬레이션 (테스트용)"""
    cost = self.policy['credit_per_work']
    current = self.get_credits()

    processed = 0
    for i in range(file_count):
        if current < cost:
            return {
                'success': False,
                'blocked': True,
                'processed_count': processed,
                'interrupted': processed > 0,
                'exhausted': True
            }
        current -= cost
        processed += 1

    self.set_credits(current)
    return {
        'success': True,
        'processed_count': processed,
        'blocked': False
    }

def get_registration_status(self) -> dict:
    """등록 상태 반환"""
    return {
        'is_registered': self.registration_manager.is_registered(),
        'email': self.registration_manager.get_email(),
        'registered_at': self.registration_manager.get_registration_date()
    }
```

## 결과 출력

인증 완료 후 결과는 `test_results/certification_YYYYMMDD_HHMMSS/`에 저장됩니다:

```
test_results/certification_20260126_101530/
├── bom_exporter_report.html    # 웹 리포트 (브라우저로 열기)
├── bom_exporter_result.json    # JSON 결과
├── dwg_classifier_report.html
├── dwg_classifier_result.json
└── ...
```

### HTML 리포트 예시
- 인증 배지 (🥇/🥈/🥉/❌)
- 전체 통계 (총 테스트, 통과, 실패, 소요 시간)
- 스위트별 상세 결과
- 실패한 테스트 메시지

## 디렉토리 구조

```
90.tests/ui_lifecycle_test/
├── __init__.py
├── README.md
├── run_certification.py      # 메인 실행 스크립트
├── run_certification.bat     # Windows 배치 파일
├── setup_test_data.py        # 테스트 데이터 설정
│
├── core/                     # 코어 프레임워크
│   ├── __init__.py
│   ├── test_server.py        # IPC 서버 (앱에서 import)
│   ├── test_client.py        # IPC 클라이언트
│   ├── certification.py      # 인증 엔진
│   └── report.py             # 리포트 생성기
│
├── suites/                   # 테스트 스위트
│   ├── __init__.py
│   ├── base.py               # 기본 스위트 클래스
│   ├── cert_config.py        # 설정 테스트
│   ├── cert_registration.py  # 등록 테스트
│   ├── cert_credits.py       # 크레딧 테스트
│   ├── cert_state.py         # 상태 테스트
│   ├── cert_recovery.py      # 복구 테스트
│   └── cert_ui.py            # UI 테스트
│
└── test_results/             # 결과 저장
    └── certification_YYYYMMDD_HHMMSS/
```

## 크레딧 정책 (참고)

| 앱 | 작업당 크레딧 | 체험판 크레딧 |
|---|---|---|
| bom_exporter | 100 | 10,000 |
| dwg_classifier | 50 | 5,000 |
| dwg_batch_print | 40 | 4,000 |
| conversion_verifier | 30 | 3,000 |
| korean_filename_normalizer | 20 | 2,000 |

## 라이선스

WorksFree Internal Use Only
