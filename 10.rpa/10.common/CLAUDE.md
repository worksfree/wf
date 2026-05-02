# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 역할

모든 WorksFree RPA 앱이 공유하는 공통 모듈 모음. 앱은 이 폴더를 Python path에 추가하여 사용.

## 모듈 목록

| 파일 | 역할 |
|------|------|
| `wf_log.py` | 싱글톤 로거. `get_app_logger("app_name")` 으로 사용. 30일 자동 정리 |
| `wf_credit_manager.py` | 크레딧 차감/동기화. Google Sheets 연동. 로컬 캐시 + 변경 플래그 방식 |
| `wf_register.py` | 사용자 이메일 등록, 이메일 인증코드 발송, HW 지문 검증 |
| `wf_googlesheets_manager.py` | Google Sheets 읽기/쓰기. 6개 시트 관리 |
| `wf_hwinfo.py` | CPU ID + 메인보드 UUID 조합 HW 지문 생성 |
| `wf_email.py` | SMTP 이메일 발송 (admin_config 시트에서 설정 로드) |
| `wf_app_init_helpers.py` | 앱 초기화 공통 헬퍼 (JSON 숨김속성 설정 등) |
| `wf_settings_common.py` | JSON 설정 파일 로드/저장 공통 유틸리티 |
| `wf_license.py` | 라이선스 검증 |

## 개발용 설정 파일 (`config/`)

dev/demo 모드에서 모든 앱이 공유하는 설정 파일 위치:
```
10.common/config/
  wf_rpa_config.json              # 전역 사용자 정보
  credentials/
    google-service-account.json   # Google 서비스 계정 키 (gitignore 대상)
  {app_name}/
    policy.json                   # 크레딧 정책
    settings.json                 # UI 설정
    credit_history.json           # 크레딧 이력
```

**주의**: `config/` 폴더는 개발 환경 전용. 배포(release)는 `~/.wf_rpa/`를 사용.

## 각 모듈 독립 테스트

각 모듈은 `__main__` 블록에 `quick_test()` 함수를 포함하며, 명령행 옵션으로 실행:

```powershell
python wf_credit_manager.py test          # 테스트 실행
python wf_credit_manager.py clean         # 생성된 테스트 데이터 삭제
python wf_credit_manager.py test-and-clean
```

임시 데이터는 `~/.temp/` 폴더에 저장. Google Sheets 접근 시 테스트 간격 10초 유지.

## Google Sheets 구조 (서비스 계정 연동)

- 테스트용 시트 ID: `1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww`
- 서비스용 시트 ID: `13OuY3j6nzUxOfIT07LiU264OImtkxrdPDEdRW8eRTv8`

6개 시트:
1. `registrations` — 사용자 등록 정보
2. `credit_sync` — 사용자별 앱별 크레딧 현황
3. `usage_logs` — 크레딧 사용 내역
4. `purchase_history` — 크레딧 구매 내역
5. `app_policies` — 앱별 정책
6. `admin_config` — 관리자 설정 (SMTP, 관리자 비밀번호 등)

## 크레딧 시스템 설계

- 로컬 `credit_history.json`에 잔고 캐시, `credit_changed: true` 플래그 설정
- 앱 종료 시 또는 스케줄러가 Google Sheets와 동기화
- `trial_credits: -1` = 무료 앱 (차감 없음, 사용 로그는 항상 기록)
- `purchased_credits: -1` = 영구 라이선스

## 관리자 비밀번호

Google Sheets `admin_config` 시트의 `admin_pw` 값. fallback: `"admin2024"`. dev 모드에서는 비밀번호 없이 즉시 진입.
