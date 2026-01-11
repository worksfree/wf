# 솔리드웍스 메모리 부족 문제 해결 가이드

## 🚨 문제 상황
- SolidWorks에서 "Resource Monitor: Available system memory is low" 경고 발생
- Windows에서 "경고! SOLIDWORKS 실행에 Windows 리소스가 부족합니다" 팝업 발생
- **한 번 실패하면 이후 모든 파일이 연쇄적으로 실패하는 현상**

## ✅ 구현된 해결책

### 방법 1: 선제적 메모리 모니터링 (자동 재시작) 🎯

**동작 원리:**
- 매 파일 처리 전에 시스템 메모리 상태를 체크
- 가용 메모리가 임계치(기본 20%) 이하로 떨어지면 자동으로 SolidWorks 재시작
- 메모리가 회복되면 작업 재개

**설정 방법:**
`.bom2excel_settings.json` 파일에 다음 설정 추가:

```json
{
  "app_config": {
    "enable_memory_monitor": true,
    "memory_threshold_percent": 20,
    "restart_count": 15,
    "base_wait_time": 60,
    "seconds_per_10mb": 60,
    "file_save_wait_multiplier": 2,
    "consec_timeout_limit": 2
  }
}
```

**설정 항목 설명:**
- `enable_memory_monitor` (true/false): 메모리 모니터링 활성화 여부
- `memory_threshold_percent` (숫자): 가용 메모리 임계치 (%)
  - 20 = 가용 메모리 20% 이하면 재시작
  - 낮을수록 공격적 (15~25 권장)
- `restart_count` (숫자): 정기 재시작 주기 (파일 개수)

**장점:**
- ✅ 메모리 부족 **사전 감지** 및 자동 대응
- ✅ 연쇄 실패 방지
- ✅ 로그에 메모리 상태 자동 기록
- ✅ 백그라운드에서 자동 작동 (사용자 개입 불필요)

**로그 예시:**
```
⚠️ 메모리 부족 감지! 가용 메모리: 3.2GB (18.5%) < 임계치 20% → 선제적 SolidWorks 재시작 수행
SolidWorks 메모리 사용량: 8.3GB
솔리드웍스 재시작 시도 1/3...
✅ 메모리 확보를 위한 재시작 완료
재시작 후 메모리: 가용 8.7GB (51.2%)
```

---

### 방법 2: 재시작 주기 단축 (빠른 적용) ⚡

**동작 원리:**
- 메모리가 쌓이기 전에 더 자주 SolidWorks 재시작

**설정 방법:**
```json
{
  "app_config": {
    "restart_count": 5  // 15 → 5로 변경 (5개 파일마다 재시작)
  }
}
```

**장점:**
- ✅ 5초 안에 적용 가능
- ✅ 즉시 효과 확인 가능

**단점:**
- ⚠️ 재시작이 자주 일어나서 전체 속도 약간 저하

---

### 방법 3: 연속 타임아웃 재시작 (기존 기능 활용)

**동작 원리:**
- 메모리 부족으로 인한 타임아웃 2회 발생 시 자동 재시작
- 이미 구현되어 있음 (활성화됨)

**설정:**
```json
{
  "app_config": {
    "consec_timeout_limit": 2  // 연속 2회 타임아웃 시 재시작
  }
}
```

---

## 📊 권장 설정 조합

### 추천 1: 안정성 중시 (메모리 문제 완전 해결)
```json
{
  "app_config": {
    "enable_memory_monitor": true,
    "memory_threshold_percent": 20,
    "restart_count": 10,
    "base_wait_time": 60,
    "seconds_per_10mb": 60,
    "consec_timeout_limit": 2
  }
}
```

### 추천 2: 속도 중시 (메모리 여유 있는 경우)
```json
{
  "app_config": {
    "enable_memory_monitor": true,
    "memory_threshold_percent": 15,
    "restart_count": 20,
    "base_wait_time": 60,
    "seconds_per_10mb": 60
  }
}
```

### 추천 3: 긴급 대응 (즉시 적용)
```json
{
  "app_config": {
    "restart_count": 5,
    "enable_memory_monitor": false
  }
}
```

---

## 🔧 적용 방법

### 1단계: psutil 패키지 설치
```powershell
pip install psutil
```

### 2단계: 설정 파일 수정
파일 위치: `C:\Users\[사용자명]\.wf_rpa\bom2excel\.bom2excel_settings.json`

위 JSON 설정 중 하나를 복사하여 파일에 붙여넣기

### 3단계: 프로그램 재시작
BOM2Excel 앱을 완전히 종료하고 다시 실행

---

## 📝 테스트 방법

### 메모리 모니터 테스트 스크립트
```python
# test_memory_monitor.py
import psutil

# 현재 메모리 상태 확인
mem = psutil.virtual_memory()
print(f"전체 메모리: {round(mem.total / (1024**3), 2)}GB")
print(f"사용중: {round(mem.used / (1024**3), 2)}GB ({mem.percent}%)")
print(f"가용: {round(mem.available / (1024**3), 2)}GB ({100 - mem.percent:.1f}%)")

# SolidWorks 메모리 확인
for proc in psutil.process_iter(['name', 'memory_info']):
    if proc.info['name'] == 'SLDWORKS.exe':
        sw_mem = round(proc.info['memory_info'].rss / (1024**3), 2)
        print(f"SolidWorks 메모리: {sw_mem}GB")
        break
```

실행:
```powershell
python test_memory_monitor.py
```

---

## 🛠️ 문제 해결 (Troubleshooting)

### Q1: "import psutil" 에러 발생
**A:** psutil 패키지 설치 필요
```powershell
pip install psutil
```

### Q2: 메모리 모니터가 작동하지 않음
**A:** 로그 파일 확인
- 위치: `C:\Users\[사용자명]\.wf_rpa\bom2excel\.logs\[날짜].txt`
- "메모리 상태" 키워드로 검색
- `enable_memory_monitor: true` 설정 확인

### Q3: 여전히 메모리 부족 발생
**A:** 임계치 상향 조정
```json
{
  "memory_threshold_percent": 25  // 20 → 25로 증가
}
```

### Q4: 너무 자주 재시작됨
**A:** 임계치 하향 조정
```json
{
  "memory_threshold_percent": 15  // 20 → 15로 감소
}
```

---

## 📈 모니터링 명령어

### 실시간 메모리 모니터링 (PowerShell)
```powershell
# 5초마다 메모리 상태 출력
while ($true) {
    $mem = Get-CimInstance Win32_OperatingSystem
    $freeGB = [math]::Round($mem.FreePhysicalMemory / 1MB, 2)
    $totalGB = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 2)
    $percent = [math]::Round(($freeGB / $totalGB) * 100, 1)
    Write-Host "$(Get-Date -Format 'HH:mm:ss') | 가용: ${freeGB}GB / ${totalGB}GB (${percent}%)"
    Start-Sleep -Seconds 5
}
```

### SolidWorks 프로세스 메모리 확인
```powershell
Get-Process SLDWORKS | Select-Object Name, @{Name="Memory(GB)";Expression={[math]::Round($_.WorkingSet64 / 1GB, 2)}}
```

---

## 📚 관련 파일

- `automation.py`: 메모리 체크 로직 구현
- `memory_monitor.py`: 메모리 모니터링 유틸리티 (선택 사항)
- `.bom2excel_settings.json`: 설정 파일
- `app_setting_data.py`: 설정 로더

---

## 🎯 결론

**즉시 적용 (긴급):**
```json
{"app_config": {"restart_count": 5}}
```

**안정적 해결 (권장):**
1. `pip install psutil` 실행
2. 설정 파일에 `"enable_memory_monitor": true` 추가
3. 프로그램 재시작

**모든 변경 사항은 로그에 기록되므로, 로그 파일을 확인하면 문제 진단 가능합니다.**
