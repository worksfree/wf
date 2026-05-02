# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**Conversion Verifier (약어: cv)** — SOLIDWORKS `.SLDDRW` → `.DWG` 변환 완료 여부를 자동 검증. 원본 폴더와 변환 결과 폴더를 비교하여 누락 파일을 식별.

- 크레딧: **무료 앱** (`trial_credits: -1`, 사용 로그는 Google Sheets에 계속 기록)
- 순수 Python (외부 GUI 앱 불필요)

## 실행

```powershell
python ui_main.py
```

## 빌드

```powershell
.\build_conversion_verifier.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. 원본 폴더(`.SLDDRW`) 스캔
2. 변환 결과 폴더(`.DWG`) 스캔
3. 파일명 기준 매칭 (확장자 제외)
4. 누락 파일 탐지 (SLDDRW는 있으나 DWG 없음)
5. 파일명·크기·수정시간 비교 테이블 생성
6. 결과 리포트 표시

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI |
| `automation.py` | 파일 비교 및 검증 로직 |
| `app_setting_data.py` | 설정 로더 (`app_setting_data.py` 표준 로더로 전환됨) |
| `conversion_verifier.spec` | PyInstaller 빌드 설정 |

## 특이사항

- 레거시 숨김 파일(`~/.wf_rpa` 루트의 숨김 파일)이 감지되면 표준 경로로 1회 자동 마이그레이션
- 무료 앱이므로 크레딧 차감 없이 작동하나, 사용 로그는 항상 Google Sheets에 동기화
