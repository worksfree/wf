# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**DWG Batch Print (약어: dp)** — 폴더 내 AutoCAD DWG 파일을 지정된 프린터(또는 PDF)로 일괄 출력. pywinauto로 AutoCAD GUI 제어.

- 크레딧: 40 크레딧/파일
- 요구사항: AutoCAD 2018 이상
- 체험판: 4,000 크레딧 (약 100파일 처리)

## 실행

```powershell
# 개발 모드
python ui_main.py
```

## 빌드

```powershell
.\build_batch_print.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. AutoCAD 실행/연결 (pywinauto UIA 백엔드)
2. DWG 파일 순차 열기
3. 설정된 프린터/용지/레이아웃으로 출력
4. 크레딧 차감 후 다음 파일 처리

### 출력 설정

- 용지: A0~A4 지원
- 레이아웃: Model 공간 또는 Layout(배치) 공간
- PDF 출력: "Microsoft Print to PDF" 선택

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI |
| `automation.py` | AutoCAD DWG 출력 로직 |
| `app_setting_data.py` | 설정 로더 |

### 주의사항

- AutoCAD 경로 자동 감지. 여러 버전 설치 시 설정에서 경로 수동 지정 필요
- AutoCAD UI 포커스에 민감 → 작업 중 다른 창 클릭 금지
- PDF 저장 경로에 쓰기 권한 필요
