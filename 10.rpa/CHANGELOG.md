# WorksFree v1.0.0 전체 릴리즈 노트

**릴리즈 날짜:** 2025-12-29  
**버전:** v1.0.0 (통합 배포)  
**플랫폼:** Windows 10/11  
**개발 기간:** 2025-10-18 ~ 2025-12-29

---

## 📋 새로운 기능 및 개선사항

### 🎯 주요 업데이트

#### 1. **5개 통합 RPA 애플리케이션**
- **Bom Exporter (BE)** v0.8.1 - BOM Excel 변환 및 검증
- **DWG Batch Print (DP)** v1.0.0 - CAD 도면 일괄 처리
- **DWG Classifier (DC)** v0.7.6 - DWG 파일 자동 분류
- **Conversion Verifier (CV)** v0.7.5 - 파일 변환 검증
- **Korean Filename Normalizer (KFN)** v0.7.5 - 한글 파일명 정규화

#### 2. **크레딧 시스템 (신규)**
- 통합 크레딧 관리 시스템
- 앱별 크레딧 사용량 추적
- 글로벌 및 앱별 정책 설정
- 자동 동기화 및 지속성 보장

#### 3. **배포 환경 개선**
- 사용자 홈 폴더 기반 설정 관리 (`~/.wf_rpa/`)
- 모든 설정 파일 숨김 처리 (개인정보 보호)
- 포터블 및 인스톨러 패키징 지원
- 자동 업데이트 인프라 구비

#### 4. **테스트 및 품질 보증**
- 통합 테스트 프레임워크 (pytest)
  - 단위 테스트: 13개
  - 통합 테스트: 20개
  - 회귀 테스트: 30개
  - 전체: **89개 테스트, 모두 통과 ✓**
- CI/CD 파이프라인 (GitHub Actions)
- 코드 품질 검사 (pylint, mypy)

#### 5. **성능 최적화**
- PyInstaller onedir 모드 (빠른 로딩)
- UPX 비활성화로 안정성 우선화
- 불필요한 라이브러리 제외
- 실행 파일 크기 최적화

---

## 🐛 버그 수정

### 배포 환경
- ✓ frozen 모드에서의 경로 불일치 수정
- ✓ 사용자 홈 폴더 설정 경로 통일
- ✓ 크로스 플랫폼 경로 호환성 개선

### 크레딧 시스템
- ✓ 정책 파일 로딩 오류 수정
- ✓ 등록 상태 인식 개선 (reg_time_local 폴백)
- ✓ 동시성 문제 해결

### UI/UX
- ✓ "응답 없음" 현상 개선 (conversion_verifier)
- ✓ 더미 창 깜빡임 제거
- ✓ 윈도우 크기 조정 안정성 향상

### 빌드 시스템
- ✓ spec 파일 경로 통일
- ✓ NSIS 인스톨러 생성 시간 초과 개선
- ✓ 병렬 빌드 타임아웃 처리

---

## 📦 배포 패키지

### 포함 항목
- **포터블 버전** (.zip)
  - 설치 없이 실행 가능
  - 모든 필수 라이브러리 포함
  - 약 70-150MB (앱마다 상이)

- **인스톨러** (.exe)
  - NSIS 기반 자동 설치
  - 시작 메뉴 바로가기 생성
  - 자동 업데이트 지원
  - 한글 설치 마법사

- **설정 파일** (JSON)
  - `wf_global_settings.json` - 전역 설정
  - `{app_name}/config/` - 앱별 설정
  - `{app_name}/logs/` - 실행 로그

### 배포 경로
```
~/.wf_rpa/                          # 사용자 홈 (숨김)
├── wf_global_settings.json         # 전역 설정
├── bom_exporter/
│   ├── config/
│   │   ├── credits.json            # 크레딧 정보
│   │   └── settings.json           # 앱 설정
│   ├── logs/                       # 실행 로그
│   └── res/                        # 리소스 (fhd/qhd/uhd)
├── dwg_batch_print/                # DP 앱
├── dwg_classifier/                 # DC 앱
├── conversion_verifier/            # CV 앱
└── korean_filename_normalizer/     # KFN 앱
```

---

## 🔄 마이그레이션 가이드 (기존 사용자)

이전 버전에서 업그레이드하는 경우:

1. **기존 애플리케이션 제거**
   ```powershell
   # 기존 설치 폴더 백업
   Copy-Item "C:\Program Files\WorksFree" -Destination "C:\Program Files\WorksFree_backup"
   # 제어판에서 제거
   ```

2. **새 버전 설치**
   - 다운로드한 인스톨러(.exe) 실행
   - 설치 마법사 따라 진행
   - 자동으로 설정 마이그레이션

3. **크레딧 확인**
   ```
   홈 폴더 > .wf_rpa > {앱명} > config > credits.json
   ```

4. **설정 수동 복구** (필요시)
   - 이전 `settings.json` 값들을 새로운 위치에 복사

---

## ✅ 시스템 요구사항

### 최소 요구사항
- **OS:** Windows 10 21H2 이상, Windows 11
- **메모리:** 2GB RAM 이상
- **디스크:** 300MB 여유 공간
- **디스플레이:** 1920x1080 이상 권장

### 지원 포맷
- **BOM:** Excel (.xlsx, .xls)
- **CAD:** DWG, DXF
- **파일명:** UTF-8 인코딩 지원

---

## 📝 앱별 상세 릴리즈 노트

각 애플리케이션의 상세 변경사항은 아래를 참고하세요:

- [Bom Exporter v0.8.1 릴리즈 노트](./bom_exporter/CHANGELOG.md)
- [DWG Batch Print v1.0.0 릴리즈 노트](./dwg_batch_print/CHANGELOG.md)
- [DWG Classifier v0.7.6 릴리즈 노트](./dwg_classifier/CHANGELOG.md)
- [Conversion Verifier v0.7.5 릴리즈 노트](./conversion_verifier/CHANGELOG.md)
- [Korean Filename Normalizer v0.7.5 릴리즈 노트](./korean_filename_normalizer/CHANGELOG.md)

---

## 🔗 관련 문서

- [설치 가이드](./docs/DEPLOYMENT.md)
- [문제 해결](./docs/TROUBLESHOOTING.md)
- [개발자 가이드](./docs/CODING_STANDARDS.md)
- [테스트 계획](./docs/TEST_PLANS.md)

---

## 💬 피드백 및 지원

- **문제 보고:** support@worksfree.co.kr
- **기능 요청:** features@worksfree.co.kr
- **웹사이트:** https://worksfree.co.kr

---

## 📊 통계

| 항목 | 수치 |
|------|------|
| 총 애플리케이션 | 5개 |
| 통합 모듈 | 11개 |
| 단위 테스트 | 13개 |
| 통합 테스트 | 20개 |
| 회귀 테스트 | 30개 |
| 테스트 통과율 | 100% ✓ |
| 코드 라인 수 | ~15,000줄 |
| 빌드 시간 (병렬) | ~60분 |
| 포터블 패키지 크기 | ~500MB (전체) |

---

**Happy coding! 🚀**
