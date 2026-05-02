# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

WorksFree RPA 앱의 단위 테스트 및 WF-ACT 인증 툴킷.

## 폴더 구조

```
90.tests/
├── conftest.py                      # pytest 공통 fixture
├── 10.common/                       # 공통 모듈 단위 테스트
│   ├── test_wf_credit_manager_*.py
│   ├── test_wf_email_*.py
│   └── test_wf_scenario_complete.py
├── 30.apps/bom2excel/               # bom_exporter 통합 테스트
└── ui_lifecycle_test/               # WF-ACT 인증 툴킷
    ├── run_certification.py         # 동적 인증 실행기
    ├── run_static_certification.py  # 정적 인증 실행기
    └── test_results/                # 인증 결과 (HTML 리포트)
```

## 단위 테스트 실행

```powershell
cd D:\drive_files\10.worksfree\10.rpa
pytest 90.tests/ -v
pytest 90.tests/10.common/ -v -m unit
pytest 90.tests/10.common/ -v -m integration
```

pytest 마커: `unit`, `integration`, `google_sheets` (외부 연동)

## WF-ACT 인증 툴킷

앱 라이프사이클 전체를 자동 인증하는 통합 테스트 도구.

```powershell
cd 90.tests/ui_lifecycle_test

# 전체 앱 FULL 인증 (권장)
python run_certification.py --level full

# 특정 앱
python run_certification.py --app bom_exporter --level full
python run_certification.py --app be dc ar --level standard

# 정적 코드 검증만 (빠름)
python run_static_certification.py --app bom_exporter

# EXE 패키지 인증 (배포 전)
python run_certification.py --exe --level full

# 테스트 목록 확인
python run_certification.py --list
```

## 인증 레벨

| 레벨 | 테스트 수 | 내용 |
|------|----------|------|
| BASIC | ~40개 | 핵심 기능 |
| STANDARD | ~60개 | 일반 시나리오 |
| FULL | 166개+ | 32개 정적 + 134개 동적 |

## 8개 테스트 스위트

1. **ConfigSuite** — policy.json, settings.json, Google Sheets 연결
2. **CreditsSuite** — 크레딧 차감, 동기화, 무료앱 처리
3. **LifecycleSuite** — 시작, 종료, 상태 관리
4. **RegistrationSuite** — 이메일, HW 지문
5. **SettingsSuite** — geometry, topmost, 저장/로드
6. **UISuite** — 버튼, 단축키(Alt+G/Alt+C), 관리자 모드
7. **VersionSuite** — 버전 형식, 최소 요구사항
8. **StaticAnalysisSuite** — 코드 구조, 패턴 검증

## 인증 등급

- 🥇 FULL: 전체 통과
- 🥈 STANDARD: STANDARD까지 통과
- 🥉 BASIC: BASIC만 통과
- ❌ NONE: BASIC 미달

결과는 `test_results/certification_{timestamp}/index.html`에서 확인.
