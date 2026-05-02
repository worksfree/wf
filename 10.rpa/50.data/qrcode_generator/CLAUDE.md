# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**QR Code Generator (약어: qr)** — 텍스트/URL을 QR 코드 이미지로 변환. 단일 생성 및 Excel/CSV 기반 대량 일괄 생성 지원.

- 크레딧: **무료 앱** (`trial_credits: -1`)
- 순수 Python (외부 GUI 앱 불필요)

## 실행

```powershell
python ui_main.py
```

## 빌드

```powershell
.\build_qrcode_generator.ps1
```

## 아키텍처

### 주요 기능 (`automation.py`)

- 텍스트/URL → QR 코드 이미지 생성
- 출력 형식: PNG, JPEG, SVG
- 크기 커스터마이징
- 로고 삽입 옵션
- 색상 커스터마이징
- Excel/CSV 입력으로 대량 일괄 생성

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI |
| `automation.py` | QR 코드 생성 로직 |
| `app_setting_data.py` | 설정 로더 |
| `sample.py` | QR 생성 샘플/테스트 스크립트 |
| `test_server.py` | 로컬 HTTP 서버 테스트 유틸리티 |
| `qrcode_generator.spec` | PyInstaller 빌드 설정 |

## 의존 라이브러리

`qrcode`, `Pillow` (PIL). spec 파일의 `hiddenimports`에 포함 필요.
