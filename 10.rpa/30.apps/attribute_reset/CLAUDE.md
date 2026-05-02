# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**Attribute Reset (약어: ar)** — SOLIDWORKS 파트(.sldprt) 및 어셈블리(.sldasm) 파일의 사용자 정의 속성(Custom Properties)을 일괄 초기화. 경량 앱 (~380라인 UI).

- 크레딧: 200 크레딧/작업
- 요구사항: SOLIDWORKS 2016 이상

## 실행

```powershell
# 개발 모드
python ui_main.py
```

## 빌드

```powershell
.\build_attribute_reset.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. SOLIDWORKS 실행/연결
2. 폴더 내 `.sldprt`/`.sldasm` 파일 순차 처리
3. 선택된 속성 초기화 (전체/선택적/제외)
4. 백업 옵션 활성화 시 `.bak` 파일 생성
5. 파일 저장 후 닫기

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI (경량: ~380라인) |
| `automation.py` | SOLIDWORKS 속성 초기화 로직 |
| `app_setting_data.py` | 설정 로더 |
| `attribute_reset.spec` | PyInstaller 빌드 설정 |

### 경량 앱 특이사항

다른 앱과 달리:
- Startup Profiling 없음 (구조가 단순하여 불필요)
- 초기화 대상 속성은 설정에서 세밀하게 구성 가능 (전체/선택/제외)
- 백업 파일은 원본과 같은 폴더에 `.bak` 확장자로 저장

## 설정 (`settings.json` 주요 항목)

```json
{
  "app_config": {
    "solidworks_path": "자동감지",
    "backup_enabled": true,
    "backup_location": "same_folder"
  }
}
```
