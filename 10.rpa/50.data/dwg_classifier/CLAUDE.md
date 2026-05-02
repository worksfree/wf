# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**DWG Classifier (약어: dc)** — Excel 발주관리서(규칙 파일)를 기준으로 DWG 도면 파일을 가공분류별 폴더로 자동 분류·이동. 유일한 **2입력 앱** (폴더 + Excel 파일 다중 선택).

- 크레딧: 50 크레딧/작업
- 순수 Python (외부 GUI 앱 불필요)

## 실행

```powershell
python ui_main.py
```

## 빌드

```powershell
.\build_dwg_classifier.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. 여러 Excel 발주관리서 로드 → 데이터 통합
2. 중복 도번(도면 번호) 제거
3. 가공분류별 폴더 자동 생성 (밀링, 선반, 판금레이져 등)
4. 해당 도번의 DWG 파일 이동
5. 누락 파일 목록화 (Excel에는 있으나 파일 없음)
6. 매칭 안 된 파일 감지 (파일은 있으나 Excel에 없음)
7. 분류 취소/복원 기능

### 2입력 UI 특이사항

다른 앱과 달리 입력이 2개:
- Excel 파일 (Listbox, 다중 선택) — 발주관리서(가공분류 규칙)
- DWG 폴더 (폴더 선택)

UI 규모: ~2,600라인 (프로젝트 내 두 번째로 큰 UI)

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI (~2,600라인) |
| `automation.py` | DWG 분류 로직 |
| `app_setting_data.py` | 설정 로더 |
| `dwg_classifier.spec` | PyInstaller 빌드 설정 |

## Excel 규칙 파일 컬럼

발주관리서 Excel에서 필수 컬럼: 도번(도면 번호), 가공분류. 컬럼 구조 불일치 시 오류 메시지 표시 후 재선택.
