# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

외부 GUI 앱을 제어하지 않고, 순수 Python으로 파일/데이터를 처리하는 앱 모음. 재현성과 이식성이 높고 자동 테스트에 적합.

## 앱 목록

| 폴더 | 약어 | 기능 | 크레딧 |
|------|------|------|--------|
| `dwg_classifier/` | dc | Excel 규칙 기반 DWG 파일 자동 분류·이동 | 50/작업 |
| `conversion_verifier/` | cv | PDF/DWG 변환 전후 파일 무결성 검증 | 무료(-1) |
| `korean_filename_normalizer/` | kfn | 자소 분리된 한글 파일명 감지·정규화 | 무료(-1) |
| `qrcode_generator/` | qr | QR 코드 일괄 생성 및 관리 | 무료(-1) |

## 50.data 개발 규칙

1. 외부 GUI/프로세스 제어 코드 포함 금지 (필요 시 `30.apps/`로 이관)
2. I/O 경계와 순수 변환 로직 분리
3. 크레딧 필요 시 `wf_credit_manager` 통합

## 각 앱 공통 파일 구조

```
{app}/
├── ui_main.py           # 메인 GUI
├── automation.py        # 데이터 처리 로직 (Lazy import)
├── app_setting_data.py  # 설정 로더
├── ui_setting.py        # 설정 창
├── {app}.spec           # PyInstaller 빌드 설정
├── build_{app}.ps1      # 빌드 스크립트
└── logs/                # 실행 로그
```

## 빌드

각 앱 폴더에서:
```powershell
.\build_{app}.ps1
```

## 특이사항

- `dwg_classifier`: 입력 2개 (폴더 + Excel 규칙 파일). 유일한 2입력 앱 (~2,600라인 UI).
- `korean_filename_normalizer`: 기본 경로가 사용자 Downloads 폴더 (Known Folder API).
- `conversion_verifier`: 원본/변환 폴더 비교 후 결과 리포트 생성.
