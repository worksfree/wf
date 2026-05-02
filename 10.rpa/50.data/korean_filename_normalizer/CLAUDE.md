# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**Korean Filename Normalizer (약어: kfn)** — Windows에서 발생하는 한글 파일명 자소 분리 현상(예: "한글"→"ㅎㅏㄴㄱㅡㄹ")을 감지하고 정상 파일명으로 복원.

- 크레딧: **무료 앱** (`trial_credits: -1`)
- 기본 경로: 사용자 Downloads 폴더 (Windows Known Folder API)
- 순수 Python (외부 GUI 앱 불필요)

## 실행

```powershell
python ui_main.py
```

## 빌드

```powershell
.\build_korean_filename_normalizer.ps1
```

## 아키텍처

### 자소 분리 감지 4가지 방법 (`automation.py`)

1. **NFD 정규화 비교**: `unicodedata.normalize("NFD", name) != name`
2. **연속 자모 패턴**: 정규식으로 연속된 자모 문자 탐지
3. **단독 자모**: 독립된 자음/모음 문자 탐지
4. **자모 확장 영역**: U+3130~U+318F 범위 문자 탐지

### 파일 복원 방식

- `unicodedata.normalize("NFC", name)` + 수동 자모 조합 알고리즘
- 변환 결과를 `result/` 하위 폴더에 저장 (원본 보존)
- 충돌(동일 파일명) 시 건너뛰기

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI (700×400, 관리자 모드 시 자동 크기 조정) |
| `automation.py` | 자소 분리 감지 및 파일명 복원 로직 |
| `app_setting_data.py` | 설정 로더 |
| `korean_filename_normalizer.spec` | PyInstaller 빌드 설정 |

## UI 특이사항

- "현재 폴더 스캔" 버튼 클릭 → 백그라운드 스레드로 `rglob('*')` 재귀 탐색
- 결과 팝업: `[번호 | 자소분리파일 | 복원파일]` 테이블
- "새폴더로 저장" 옵션은 설정 창에 있음 (메인 UI 아님)
