# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

외부 데스크톱 애플리케이션(SolidWorks, AutoCAD 등)의 UI/COM/API를 직접 제어하는 자동화 앱 모음.

## 앱 목록

| 폴더 | 약어 | 기능 | 대상 앱 | 크레딧 |
|------|------|------|---------|--------|
| `bom_exporter/` | be | SolidWorks BOM → Excel 변환 | SolidWorks | 100/파일 |
| `batch_print/` | dp | DWG 파일 일괄 인쇄 | AutoCAD | 40/파일 |
| `attribute_reset/` | ar | SolidWorks 파일 속성 초기화 | SolidWorks | 200/작업 |
| `bom_api/` | — | SolidWorks COM API BOM 추출 (실험적) | SolidWorks | — |
| `ban_redirection/` | — | DNS 변경으로 네트워크 리다이렉션 차단 | 시스템 | — |

## 30.apps 개발 규칙

1. 자동화 로직은 `automation.py`, GUI는 `ui_main.py`로 분리
2. `automation.py`는 UI 이벤트(버튼 클릭) 시 Lazy import (`import automation`)
3. 외부 앱 연결·핸들 획득은 재시도(backoff) 로직 포함
4. 좌표 하드코딩 지양, pywinauto 컨트롤 탐색 우선
5. 대상 앱(SolidWorks/AutoCAD) 설치 및 라이선스 필수

## 각 앱 공통 파일 구조

```
{app}/
├── ui_main.py           # 메인 GUI + 라이프사이클
├── automation.py        # 자동화 로직 (Lazy import)
├── app_setting_data.py  # 설정 로더 (공통 구조)
├── ui_setting.py        # 설정 창 (Toplevel)
├── {app}.spec           # PyInstaller 빌드 설정
├── build_{app}.ps1      # 빌드 스크립트
├── {app}_installer.nsi  # NSIS 인스톨러 스크립트
├── res/                 # 아이콘 (*.ico)
└── logs/                # 실행 로그 (30일 자동 삭제)
```

## 빌드

각 앱 폴더에서:
```powershell
.\build_{app}.ps1
```
결과: `D:\release\candidates\{app}_{timestamp}\`
