# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 앱 개요

**ban_redirection (약어: br)** — DNS를 Google Public DNS로 변경하여 네트워크 리다이렉션(DNS 하이재킹) 차단. 모든 활성 인터페이스(유선/무선/VPN)에 적용.

- 크레딧: **무료 앱** (`trial_credits: -1`)
- 요구사항: Windows 관리자 권한 (미충족 시 UAC 재실행)

## 실행

```powershell
python ui_main.py
```

관리자 권한이 없으면 UAC 프롬프트 → 승인 후 자동 재실행.

## 빌드

```powershell
.\build_ban_redirection.ps1
```

## 아키텍처

### 자동화 흐름 (`automation.py`)

1. `is_admin()` — 관리자 권한 확인
2. `get_active_adapters()` — PowerShell `Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}`로 활성 인터페이스 목록
3. 각 인터페이스에 `set_dns(adapter, [primary, secondary])` 적용
4. `flush_dns_cache()` — `ipconfig /flushdns`

### 주요 파일

| 파일 | 역할 |
|------|------|
| `ui_main.py` | 메인 GUI (WF 표준 패턴, ~380라인) |
| `automation.py` | DNS 변경 로직 (stateless) |
| `app_setting_data.py` | 설정 로더 |

### 일반 앱과 다른 점

- 입력 없음: DNS 주소 2개 (Primary/Secondary) — 실행마다 settings.json에 저장
- 로그 영역 항상 표시 (관리자 모드와 무관)
- 크레딧 없음: `simulate_work` 항상 success 반환
- 관리자 권한 필수: main() 진입 시 UAC 재실행 로직 포함

## 설정 (`settings.json` 주요 항목)

```json
{
  "runtime_config": { "run_mode": "dev", "full_version": "v0.7.0.0" },
  "app_config": { "primary_dns": "8.8.8.8", "secondary_dns": "8.8.4.4" },
  "ui_config": { "window_height": 280, "topmost": true }
}
```
