# Batch Print

DWG 도면 파일들을 자동으로 eDrawings에서 열어서 기본 프린터로 인쇄하는 애플리케이션입니다.

## 기능

- **폴더 기반 처리**: 선택 폴더 내 모든 DWG 파일 자동 인식
- **자동 인쇄**: eDrawings에서 각 파일을 순차적으로 인쇄
- **크레딧 연동**: WorksFree 크레딧 시스템 통합, 파일당 크레딧 자동 차감
- **재시작 관리**: 안정성 위해 주기적으로 eDrawings 재시작
- **진행도 표시**: 실시간 진행률 및 크레딧 잔량 표시
- **데모 모드**: run_mode=demo일 때만 자동 화면 캡처 (Alt+C 수동 캡처 포함)
- **설정 관리**: eDrawings 경로, 재시작 주기, 타임아웃 등을 UI에서 조정 가능

## 설치

1. 폴더 구조 확인:
   ```
   batch_print/
   ├── app_setting_data.py
   ├── automation.py
   ├── ui_main.py
   ├── requirements.txt
   ├── config/batch_print/settings.json
   ├── logs/
   └── demo_captures/
   ```

2. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. eDrawings 설치 확인:
   - SOLIDWORKS eDrawings 2023 이상 설치
   - 기본 경로: `C:\Program Files\SOLIDWORKS Corp\eDrawings\eDrawings.exe`

## 사용법

### 기본 실행

```bash
python ui_main.py
```

### 개발 모드 (데모 캡처 활성화)

```bash
set WF_RPA_MODE=demo
python ui_main.py
```

### 콘솔 모드 (자동화 단독 실행)

```python
from automation import BatchPrintAutomation
from app_setting_data import get_config

config = get_config()
automation = BatchPrintAutomation(folder_path="D:/path/to/dwg_folder", console_mode=True)
automation.set_edrawings_path(config.edrawings_path)
result = automation.print_dwg_files()
print(f"결과: {result}")
```

## 설정

### settings.json 주요 항목

```json
{
  "app_config": {
    "run_mode": "release",  // dev, release, demo
    "edrawings_path": "C:\\Program Files\\SOLIDWORKS Corp\\eDrawings\\eDrawings.exe",
    "restart_count": 30      // 30파일마다 eDrawings 재시작
  },
  "print_settings": {
    "wait_timeout": 300,     // 인쇄 대화상자 대기 시간 (초)
    "restart_sleep": 5,      // 재시작 후 대기 시간
    "final_sleep": 3         // 마지막 파일 완료 대기 시간
  },
  "credit_policy": {
    "credits_per_print": 1,      // 파일당 차감 크레딧
    "check_shortage_stop": true  // 크레딧 부족 시 중단
  }
}
```

## 단축키

- **Alt+C** (데모 모드에서만): 현재 화면 수동 캡처
  - 캡처 파일: `demo_captures/demo_YYYYMMDD_HHMMSS_SSS_manual_capture.png`
  - 커서도 함께 캡처 (small_arrow.png 또는 cursor_arrow.png)

## 로그

- 개발 모드: `logs/` 폴더 아래 일별 로그
- 배포 모드: `~/.wf_rpa/batch_print/logs/` 아래 로그

## 주의사항

1. **eDrawings 경로**: 설치 경로가 다른 경우 설정에서 수정 필요
2. **멀티 인스턴스**: eDrawings는 기본적으로 싱글 인스턴스이므로, `restart_count` 설정으로 안정성 유지
3. **크레딧**: 크레딧 부족 시 중단 여부는 `check_shortage_stop` 설정으로 제어
4. **프린터**: 기본 프린터로 인쇄됨 (인쇄 대화상자에서 변경 불가)

## 문제 해결

### eDrawings가 열리지 않는 경우
- eDrawings 설치 경로 확인 (`설정` 버튼으로 변경 가능)
- eDrawings 2023 이상 버전 확인

### 인쇄가 진행되지 않는 경우
- 프린터 연결 상태 확인
- `wait_timeout` 값 증가 (설정에서 조정)
- 로그 파일 확인

### 크레딧이 차감되지 않는 경우
- 크레딧 관리자 초기화 로그 확인
- WorksFree 크레딧 정책 파일 존재 확인 (`config/wf_rpa_config.json`)

## 라이선스

WorksFree Internal Use Only
