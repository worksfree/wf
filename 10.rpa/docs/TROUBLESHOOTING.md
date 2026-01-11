# 빌드 문제 해결 가이드

## dist 폴더 PermissionError 재발방지 대책

### 문제 원인
1. **Windows 파일 락**: 이전 빌드의 exe나 DLL 파일이 여전히 메모리에 로드되어 있음
2. **백그라운드 프로세스**: 테스트나 실행 중인 앱이 종료되지 않음
3. **NSIS 인스톨러 빌드 중단**: Ctrl+C로 중단 시 파일 핸들이 열린 상태로 유지

### 적용된 해결책

#### 1. 강력한 폴더 정리 함수 (3단계 시도)

모든 빌드 스크립트에 `Remove-LockedFolder` 함수가 추가되었습니다:

```powershell
function Remove-LockedFolder {
    param([string]$Path)
    
    if (Test-Path $Path) {
        # 1차: 일반 삭제 시도
        # 2차: 관련 프로세스 종료 후 재시도
        # 3차: 하위 파일 개별 삭제 시도
        # 실패 시: 경고만 출력하고 빌드 계속 진행
    }
}
```

#### 2. 적용된 스크립트
- `10.rpa/30.apps/bom2excel/build_bom2excel.ps1`
- `10.rpa/50.data/dwg_classifier/build_dwg_classifier.ps1`
- `10.rpa/50.data/conversion_verifier/build_conversion_verifier.ps1`
- `10.rpa/50.data/korean_filename_normalizer/build_korean_filename_normalizer.ps1`

### 사용법

#### 개별 빌드
```powershell
# 각 앱 폴더에서 실행
.\build_bom2excel.ps1
.\build_dwg_classifier.ps1
.\build_conversion_verifier.ps1
.\build_korean_filename_normalizer.ps1
```

#### 배치 빌드
```powershell
# 10.rpa 폴더에서 실행
.\build_all_apps.ps1
```

### 예방 조치

#### 빌드 전 체크리스트
1. **모든 앱 종료**: 실행 중인 exe 파일이 없는지 확인
2. **탐색기 닫기**: dist/build 폴더를 열어둔 탐색기 창 닫기
3. **테스트 프로세스 확인**: 백그라운드에서 실행 중인 테스트 프로세스 확인

```powershell
# 실행 중인 앱 확인
Get-Process | Where-Object { $_.Name -like "*bom2excel*" -or $_.Name -like "*dwg_classifier*" -or $_.Name -like "*conversion_verifier*" -or $_.Name -like "*korean_filename_normalizer*" }

# 모두 종료
Get-Process | Where-Object { $_.Name -like "*bom2excel*" -or $_.Name -like "*dwg_classifier*" -or $_.Name -like "*conversion_verifier*" -or $_.Name -like "*korean_filename_normalizer*" } | Stop-Process -Force
```

#### 빌드 중 주의사항
1. **Ctrl+C 최소화**: 가능한 빌드가 완료될 때까지 대기
2. **인스톨러 빌드 중단 시**: 다음 빌드 전 프로세스 확인
3. **오류 발생 시**: 에러 메시지 확인 후 재시도

### 여전히 문제가 발생할 경우

#### 수동 정리 방법
```powershell
# 1. 모든 관련 프로세스 강제 종료
Get-Process | Where-Object { $_.Path -like "*\10.rpa\*" } | Stop-Process -Force

# 2. 폴더 삭제 재시도
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue

# 3. 재부팅 (최후의 수단)
```

#### Handle.exe 사용 (Sysinternals)
```powershell
# 1. Handle.exe 다운로드
# https://docs.microsoft.com/en-us/sysinternals/downloads/handle

# 2. 파일을 잡고 있는 프로세스 찾기
.\handle.exe dist

# 3. 해당 프로세스 종료
```

### 성능 최적화 적용 상태

#### BOM2Excel
- ✅ Logger lazy loading 적용
- ✅ Background policy loading 적용
- ✅ File caching 적용
- 성능 개선: 2446ms → 1046ms (57% 향상)

#### DWG Classifier
- ✅ Logger lazy loading 적용
- ✅ File naming cleanup (`.` 접두어 제거)
- 예상 성능 개선: ~1초

#### Conversion Verifier
- ✅ 최적화 불필요 (logger 초기화 없음)
- 현재 성능: 양호

#### Korean Filename Normalizer
- ✅ 최적화 불필요 (logger 초기화 없음)
- 현재 성능: 양호

### 향후 개선 사항
1. PyInstaller 캐시 활용으로 빌드 시간 단축
2. 증분 빌드 지원
3. 빌드 전 자동 프로세스 정리 스크립트
4. CI/CD 파이프라인 구축

### 참고 자료
- [PyInstaller 공식 문서](https://pyinstaller.org/)
- [Windows 파일 락 문제 해결](https://stackoverflow.com/questions/tagged/file-locking+windows)
- [PowerShell 프로세스 관리](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/)
