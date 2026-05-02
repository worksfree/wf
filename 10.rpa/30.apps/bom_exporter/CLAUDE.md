# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**BOM Exporter (약어: be)** — SolidWorks 어셈블리 도면(.SLDDRW)의 BOM을 pywinauto GUI 자동화로 추출하여 Excel로 저장. 가장 무거운 앱 (SolidWorks 연동).

- 크레딧: 100 크레딧/파일
- 요구사항: SolidWorks 2016 이상

## 실행

```powershell
# 개발 모드
python ui_main.py

# 데모 모드
$env:WF_RPA_MODE = "demo"; python ui_main.py
```

## 빌드

```powershell
.\build_bom_exporter.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. SolidWorks 실행/연결 (pywinauto UIA 백엔드)
2. `.SLDDRW` 파일 순차 열기
3. BOM 우클릭 → "Excel로 저장" 메뉴 실행
4. 크레딧 차감
5. 주기적으로 SolidWorks 재시작 (안정성)
6. 실패 파일 2차 재시도
7. 처리 결과 이메일 발송

### 성능 최적화 (목표: 로딩 1초 이하)

- `automation.py`는 버튼 클릭 시 Lazy import
- `_load_config_fast()` + `load_policies_async()` 비동기 정책 로드
- mtime 기반 파일 캐시

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI (~2,900라인), 앱 라이프사이클 |
| `automation.py` | SolidWorks BOM 추출 로직 |
| `app_setting_data.py` | 설정 로더 |
| `bom_exporter.spec` | PyInstaller 빌드 설정 |
| `capture_demo.py` | 데모 화면 캡처 유틸리티 |
| `memory_monitor.py` | 메모리 사용량 모니터링 |

## Non-UI 배치 모드

`ui_main.py`는 콘솔 명령어 인자로 배치 실행 지원 (폴더 경로 직접 전달).

## pywinauto 주의사항

- UIA 백엔드 사용 (`Application(backend="uia")`)
- SolidWorks 버전별 컨트롤 이름 다를 수 있음 → 재시도 로직 필수
- UI 포커스·해상도에 민감 → 화면 해상도 변경 시 컨트롤 탐색 실패 가능
