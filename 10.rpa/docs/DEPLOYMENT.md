# WorksFree 형상 관리 및 배포 가이드

## 개요

WorksFree 프로젝트의 Google Service Account 키 파일 및 앱 배포 구조 표준화 가이드입니다.

## 📁 디렉토리 구조

### 개발 환경
```
10.worksfree/10.rpa/
├── 10.common/
│   ├── credentials/
│   │   ├── README.md
│   │   ├── google-service-account.json     # 실제 키 파일 (gitignore)
│   │   └── google-service-account.json.template
│   ├── templates/
│   │   └── standard_app.spec.template      # 표준 .spec 템플릿
│   ├── wf_credentials_manager.py           # 새로운 자격증명 관리자
│   └── (기타 공통 모듈들...)
├── 30.apps/                               # 외부 앱 자동화
│   └── bom2excel/
│       ├── ui_main.py
│       ├── automation.py
│       └── bom2excel.spec
├── 50.data/                               # 데이터 처리 앱
│   └── dwg_classifier/
│       ├── ui_main.py
│       ├── automation.py
│       └── dwg_classifier.spec
├── build_apps.py                          # 통합 빌드 스크립트
└── .gitignore                             # 보안 파일 제외 설정
```

### 사용자 환경
```
%USERPROFILE%/.wf_rpa/
├── credentials/
│   └── google-service-account.json        # 자동 복사된 키
├── wf_rpa_config.json                    # 사용자 설정
└── .wf_app_policies.json                  # 앱 정책
```

### 배포 환경
```
release/
├── bom2excel/
│   ├── bom2excel.exe
│   └── _internal/
│       ├── credentials/
│       │   └── google-service-account.json # 번들된 키
│       └── (기타 리소스...)
└── dwg_classifier/
    ├── dwg_classifier.exe
    └── _internal/...
```

## 🔧 설정 방법

### 1. 개발 환경 설정

1. **Google Service Account 키 설정**:
   ```bash
   # Google Cloud Console에서 서비스 계정 키 다운로드
   # 파일을 다음 위치에 저장:
   10.common/credentials/google-service-account.json
   ```

2. **Git 설정 확인**:
   ```bash
   # .gitignore에 보안 파일 제외 설정 확인
   cat .gitignore | grep credentials
   ```

### 2. 빌드 환경 설정

1. **전제조건 확인**:
   ```bash
   cd 10.rpa
   python build_apps.py check
   ```

2. **개별 앱 빌드**:
   ```bash
   # DWG Classifier 빌드
   python build_apps.py build --app dwg_classifier --clean
   
   # BOM2Excel 빌드  
   python build_apps.py build --app bom2excel --clean
   ```

3. **전체 빌드**:
   ```bash
   # 모든 앱 일괄 빌드
   python build_apps.py build-all --clean
   
   # 릴리즈 패키지 생성
   python build_apps.py release --version 1.0.0
   ```

## 🔐 보안 관리

### 자격증명 파일 보안
- **개발 환경**: Git에 절대 커밋하지 않음 (.gitignore로 보호)
- **배포 환경**: PyInstaller로 안전하게 번들링
- **사용자 환경**: 홈 디렉토리의 숨겨진 폴더에 보관

### 파일 권한
- Unix 계열: 600 (소유자만 읽기/쓰기)
- Windows: 사용자 폴더 기본 권한

## 🚀 자동화된 워크플로우

### 앱 실행 시 자동 처리
1. **자격증명 확인**: 사용자 홈 디렉토리 확인
2. **자동 복사**: 번들된 키를 홈 디렉토리로 복사
3. **유효성 검증**: JSON 구조 및 필수 필드 확인
4. **권한 설정**: 적절한 파일 권한 적용

### 빌드 시 자동 처리
1. **리소스 수집**: credentials, 공통 모듈, 앱별 리소스
2. **의존성 해결**: 히든 임포트 자동 포함
3. **최적화**: 불필요한 모듈 제외
4. **패키징**: 단일 실행파일 생성

## 📋 체크리스트

### 개발자용
- [ ] Google Service Account 키를 올바른 위치에 배치
- [ ] .gitignore 설정 확인
- [ ] 새로운 앱 추가 시 APPS_CONFIG에 등록
- [ ] .spec 파일 템플릿 활용

### 배포자용  
- [ ] 빌드 전제조건 확인 (`python build_apps.py check`)
- [ ] 테스트 빌드 수행
- [ ] 실행파일 동작 검증
- [ ] Google Sheets 연동 테스트

### 사용자용
- [ ] 앱 첫 실행 시 자격증명 자동 설정 확인
- [ ] 홈 디렉토리 `.wf_rpa` 폴더 생성 확인
- [ ] 앱 간 설정 공유 동작 확인

## 🔄 마이그레이션 가이드

기존 앱을 새로운 구조로 마이그레이션:

1. **credentials 정리**:
   ```bash
   # 기존 위치의 키 파일 제거
   find . -name "*service-account*.json" -not -path "./10.common/credentials/*"
   ```

2. **코드 업데이트**:
   ```python
   # 기존 코드
   from google.oauth2.service_account import Credentials
   creds_file = Path.home() / '.wf_rpa' / 'some-key.json'
   
   # 새로운 코드  
   from wf_credentials_manager import get_google_credentials_path
   creds_file = get_google_credentials_path()
   ```

3. **.spec 파일 업데이트**:
   - 표준 템플릿 사용
   - 리소스 수집 자동화
   - 히든 임포트 표준화

## ⚠️ 주의사항

1. **보안**: 절대 키 파일을 Git에 커밋하지 마세요
2. **경로**: 하드코딩된 경로 대신 credentials manager 사용
3. **테스트**: 배포 전 반드시 실행파일 단독 테스트
4. **버전**: 각 앱의 버전 정보 관리
5. **로깅**: 자격증명 관련 민감한 정보 로깅 금지

## 📞 문의

문제 발생 시:
1. 빌드 전제조건 재확인
2. 로그 파일 확인
3. 개발팀 문의

---

## 개발 모드 vs 배포 모드

# 개발 모드 vs 배포 모드 설명

## 환경 구분 방식

### 개발 모드 (Development Mode)
- 감지 방법: `WF_RPA_HOME` 또는 `WF_RPA_DIR` 환경변수가 설정되어 있는 경우
- 폴더 위치: 환경변수로 지정된 경로
- 숨김 처리: 없음 - 모든 폴더/파일이 보임
- 용도: 개발 중 디버깅, 테스트 실행, 파일 구조 확인

```powershell
$env:WF_RPA_HOME = "D:\dev\test_home"
python ui_main.py

# 생성되는 구조 (모두 보임)
D:\dev\test_home\
├── wf_rpa_config.json
├── [app]/credit_policy.json
└── bom2excel\
   └── .bom2excel_credits.json
```

### 배포 모드 (Release Mode)
- 감지 방법: `WF_RPA_HOME` 환경변수가 설정되지 않은 경우
- 폴더 위치: 사용자 홈 디렉토리 (`%USERPROFILE%\.wf_rpa`)
- 숨김 처리: 모든 폴더/파일 숨김
- 용도: 최종 사용자 배포, 프로덕션 환경, 숨김 폴더로 UI 깔끔하게 유지

```powershell
python ui_main.py

# 생성되는 구조 (모두 숨김)
C:\Users\Username\.wf_rpa\
├── wf_rpa_config.json
├── [app]/credit_policy.json
└── bom2excel\
   └── .bom2excel_credits.json
```

### 숨김 처리 구현

- Windows: `ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)`
- Linux/macOS: 파일명이 `.` 으로 시작하면 숨김

### 숨김 처리되는 항목
- `.wf_rpa` 폴더, `wf_rpa_config.json`, 앱별 폴더, `.[app]_credits.json`, `credit_policy.json`

### 개발 시 주의사항
```powershell
$env:WF_RPA_HOME = "D:\temp\test_wf_rpa"
python test_unlimited_credits.py
Remove-Item Env:\WF_RPA_HOME
```

### 배포 전 체크리스트
```powershell
$env:WF_RPA_HOME   # 비어있어야 함
$env:WF_RPA_DIR    # 비어있어야 함
```

---

## 통합 빌드/인스톨러 가이드

### .spec 중심 빌드 시스템
- 모든 빌드 로직을 `.spec` 에 통합 → PyInstaller 한 번으로 배포 산출물 생성

```powershell
cd 50.data\dwg_classifier
pyinstaller dwg_classifier.spec
```

자동화 단계:
- 리소스 자동 수집, Google Credentials 포함, 사용자 홈 설정 준비
- NSIS 인스톨러 스크립트 자동 생성, 포터블/인스톨러/ZIP 생성, 임시 정리

### 스마트 NSIS 인스톨러
- 첫 앱 설치 시 전역 설정 생성, 이후 앱은 공통 인프라 건너뜀

### Zero-Configuration 배포 산출물 예시
```
release/installers/
├── dwg_classifier_1.0.0_YYYYMMDD.exe
├── dwg_classifier_1.0.0_portable.zip
└── bom2excel_1.0.0_YYYYMMDD.exe
```

### 템플릿 기반 구조
```
enhanced_app.spec.template  # 모든 빌드 로직 통합
generate_specs.py           # 단순 템플릿 치환기
```

### 고급 기능 예시
- 앱별 히든 임포트 테이블, 동적 리소스 수집, 날짜 기반 버전 태깅 등

### 성능 최적화 포인트
- 필요한 모듈만 포함, UPX 압축, 중복 설치 감지로 인스톨 속도 향상

요약: 기존 다수의 빌드 스크립트 대신 각 앱의 `.spec` 한 개로 빌드/포장/인스톨러까지 일원화합니다.