# WF-ACT EXE 모드 인증 문제 해결

## 문제점 분석

### 1. EXE 모드 테스트 실패 (IPC 타임아웃)
- **원인**: exe 파일이 `--test-mode` 파라미터를 인식하지 못하고 TestServer를 시작하지 않음
- **증상**: 11초 타임아웃 후 "Server not ready" 에러

### 2. 싱글 인스턴스 모드 미고려
- **원인**: exe는 동시에 하나만 실행 가능한데, 앱 간 전환 시 이전 앱 종료를 확실히 기다리지 않음
- **증상**: 2번째 앱 실행 시 싱글 인스턴스 락으로 실행 실패 가능

### 3. 설정 폴더 참조 위치 차이
- **DEV 모드**: `D:\drive_files\10.worksfree\10.rpa\10.common\config`
- **EXE 모드**: `~/.wf_rpa` (사용자 홈 폴더)
- **문제**: 이 차이에 대한 검증 테스트 부재

### 4. 사용자 홈 초기화 로직
- **EXE 모드**: 인증 시작 시 `~/.wf_rpa` 삭제 후 최초 앱이 초기화
- **문제**: 이 과정이 제대로 작동하는지 검증 필요

## 구현된 해결 방안

### 1. TestClient 개선 (test_client.py)

```python
# 사용자 홈 정리 기능 추가
@staticmethod
def cleanup_user_home() -> None:
    """Clean up user home .wf_rpa directory for fresh EXE testing"""
    user_wf_dir = TestClient.USER_HOME_WF_DIR
    if user_wf_dir.exists():
        shutil.rmtree(user_wf_dir)
        logger.info(f"[TestClient] Cleaned user home: {user_wf_dir}")

# 앱 종료 시 싱글 인스턴스 정리 대기
def terminate_app(self, graceful: bool = True, wait_time: float = 2.0):
    # ... 종료 로직 ...
    
    # EXE 모드에서 싱글 인스턴스 정리 대기
    if not self.dev_mode and wait_time > 0:
        logger.info(f"[TestClient] Waiting {wait_time}s for single-instance cleanup...")
        time.sleep(wait_time)
```

### 2. 인증 시작 시 사용자 홈 정리 (run_certification.py)

```python
# EXE 모드에서 사용자 홈 폴더 초기화
if candidates_dir and not dev_mode:
    from core.test_client import TestClient
    TestClient.CANDIDATES_DIR = candidates_dir
    
    logger.info("EXE 모드: 사용자 홈 폴더 초기화 중...")
    TestClient.cleanup_user_home()
```

### 3. 앱 간 전환 시 대기 시간 추가 (certification.py)

```python
# EXE 모드에서 더 긴 대기 시간
finally:
    wait_time = 2.0 if not self.dev_mode else 0.5
    client.terminate_app(wait_time=wait_time)
```

### 4. ExecutionEnvironmentSuite 추가 (cert_env.py)

새로운 테스트 suite 추가:

**테스트 항목**:
1. `test_01_config_folder_location`: 설정 폴더 참조 위치 확인
   - DEV: 프로젝트 `10.common/config`
   - EXE: 사용자 홈 `~/.wf_rpa`

2. `test_02_config_files_exist`: 설정 파일 존재 확인

3. `test_03_user_home_initialized`: 사용자 홈 폴더 초기화 확인 (EXE 모드만)
   - `~/.wf_rpa/{app_name}` 폴더 생성 확인
   - `settings.json` 파일 생성 확인

4. `test_04_wf_rpa_config_accessible`: wf_rpa_config.json 접근 가능 확인

5. `test_05_credentials_accessible`: 크리덴셜 파일 접근 확인

6. `test_06_config_reload_works`: 설정 재로드 기능 확인

7. `test_07_multiple_config_reads`: 동시 설정 읽기 테스트

8. `test_08_dev_exe_mode_detection`: DEV/EXE 모드 자동 감지 확인

### 5. 배치 파일 추가

**run_certification_all.bat** (DEV 모드)
```bat
python run_certification.py --app be dp ar dc cv kfn qr -l full
```

**run_certification_all_exe.bat** (EXE 모드)
```bat
python run_certification.py --app be dp ar dc cv kfn qr -l full --exe --candidates-dir D:\release\candidates
```

## 남은 문제

### EXE 파일에 TestServer 모듈 포함 필요

현재 EXE 모드가 실패하는 근본 원인:
1. **ui_main.py에서 --test-mode 파라미터 처리 누락**
2. **TestServer 모듈이 exe에 포함되지 않음**

해결 방법:
1. 각 앱의 `ui_main.py`에 test mode 처리 코드 추가:
```python
if '--test-mode' in sys.argv:
    from test_server import TestServer
    test_server = TestServer(app, port=19800)
    test_server.start()
```

2. `.spec` 파일에 TestServer 모듈 포함:
```python
hiddenimports=[
    'socket',
    'threading',
    'json',
    # ... 기타 imports
],
```

## 테스트 실행 방법

### DEV 모드 (소스 코드)
```bash
# 간단한 방법
run_certification_all.bat

# 또는 직접 실행
python run_certification.py --app be dp ar dc cv kfn qr -l full
```

### EXE 모드 (패키징된 파일)
```bash
# 간단한 방법
run_certification_all_exe.bat

# 또는 직접 실행
python run_certification.py --app be dp ar dc cv kfn qr -l full --exe --candidates-dir D:\release\candidates
```

## 예상 결과

### DEV 모드
- ✅ 154개 테스트 × 7개 앱 = 1,078개 (ExecutionEnvironmentSuite 8개 테스트 추가)
- ✅ 모든 테스트 통과 예상
- ⏱️ 약 1분 30초 소요

### EXE 모드 (TestServer 포함 후)
- ✅ 154개 테스트 × 7개 앱 = 1,078개
- ⚠️ PackageIntegritySuite 12개 테스트만 실행 (EXE 모드 전용)
- ⚠️ ExecutionEnvironmentSuite 8개 테스트 실행
- ⏱️ 약 2분 소요 (앱 간 대기 시간 포함)

## 다음 단계

1. **ui_main.py 수정**: 모든 앱에 --test-mode 처리 추가
2. **.spec 파일 수정**: TestServer 모듈 포함
3. **재빌드**: BuildType=2로 전체 앱 재빌드
4. **EXE 인증 실행**: `run_certification_all_exe.bat`
5. **리포트 확인**: 1,078개 테스트 모두 통과 확인
