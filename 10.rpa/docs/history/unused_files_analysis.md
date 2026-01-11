# 4개 앱 미사용 파일 분석 결과

## 분석 기준
- ui_main.py와 automation.py에서 직접 또는 간접 참조되는 파일만 유지
- config 폴더 제외 (설정 파일)
- __pycache__ 제외
- 공통 모듈 (10.common) 제외

---

## 1. bom2excel (30.apps/bom2excel)

### 현재 파일 목록
1. ✅ **app_setting_data.py** - automation.py에서 import (필수)
2. ✅ **automation.py** - 핵심 로직 (필수)
3. ❌ **create_installer.py** - 참조 없음 (빌드 도구)
4. ✅ **memory_monitor.py** - automation.py에서 사용 가능성 (확인 필요)
5. ❌ **optimize_build.py** - 참조 없음 (빌드 도구)
6. ❌ **run_post_build.py** - 참조 없음 (빌드 도구)
7. ❌ **test_console_progress.py** - 참조 없음 (테스트 파일)
8. ❌ **test_registration.py** - 참조 없음 (테스트 파일)
9. ❌ **test_threading_safety.py** - 참조 없음 (테스트 파일)
10. ❌ **test_ui_main_scenarios.py** - 참조 없음 (테스트 파일)
11. ❌ **test_ui_spinner.py** - 참조 없음 (테스트 파일)
12. ✅ **ui_main.py** - 메인 UI (필수)
13. ✅ **ui_setting.py** - ui_main.py에서 import (필수)

### 제거 대상 (8개)
```
30.apps/bom2excel/create_installer.py
30.apps/bom2excel/optimize_build.py
30.apps/bom2excel/run_post_build.py
30.apps/bom2excel/test_console_progress.py
30.apps/bom2excel/test_registration.py
30.apps/bom2excel/test_threading_safety.py
30.apps/bom2excel/test_ui_main_scenarios.py
30.apps/bom2excel/test_ui_spinner.py
```

**참고**: memory_monitor.py는 추가 확인 필요

---

## 2. conversion_verifier (50.data/conversion_verifier)

### 현재 파일 목록
1. ✅ **automation.py** - 핵심 로직 (필수)
2. ✅ **config.py** - 설정 관리 (필수)
3. ❓ **ConversionVerifier.py** - 참조 확인 필요
4. ✅ **ui_main.py** - 메인 UI (필수)
5. ✅ **ui_setting.py** - UI 설정 (필수로 추정)

### 제거 대상
```
(추가 확인 후 결정)
```

---

## 3. dwg_classifier (50.data/dwg_classifier)

### 현재 파일 목록
1. ✅ **app_setting_data.py** - 설정 관리 (필수로 추정)
2. ✅ **automation.py** - ui_main.py에서 import (필수)
3. ✅ **config.py** - 설정 관리 (필수)
4. ❓ **DemoDrawingClassifier.py** - 참조 확인 필요
5. ✅ **ui_main.py** - 메인 UI (필수)
6. ❓ **ui_register.py** - 참조 확인 필요
7. ✅ **ui_setting.py** - UI 설정 (필수로 추정)

### 제거 대상
```
(추가 확인 후 결정)
```

---

## 4. korean_filename_normalizer (50.data/korean_filename_normalizer)

### 현재 파일 목록
1. ✅ **automation.py** - ui_main.py에서 import (필수)
2. ✅ **config.py** - automation.py에서 import (필수)
3. ❓ **filename_normalizer.py** - 참조 확인 필요
4. ❌ **ui_main_backup.py** - 백업 파일 (제거 대상)
5. ❌ **ui_main_new.py** - 백업/테스트 파일 (제거 대상)
6. ✅ **ui_main.py** - 메인 UI (필수)
7. ❓ **ui_register.py** - 참조 확인 필요
8. ✅ **ui_setting.py** - ui_main.py에서 import (필수)

### 제거 대상 (2개 확정)
```
50.data/korean_filename_normalizer/ui_main_backup.py
50.data/korean_filename_normalizer/ui_main_new.py
```

---

## 요약

### 즉시 제거 가능 (확정)
**bom2excel (8개)**:
- create_installer.py
- optimize_build.py
- run_post_build.py
- test_console_progress.py
- test_registration.py
- test_threading_safety.py
- test_ui_main_scenarios.py
- test_ui_spinner.py

**korean_filename_normalizer (2개)**:
- ui_main_backup.py
- ui_main_new.py

**총 10개 파일**

### 추가 확인 필요
1. bom2excel/memory_monitor.py
2. conversion_verifier/ConversionVerifier.py
3. dwg_classifier/DemoDrawingClassifier.py
4. dwg_classifier/ui_register.py
5. korean_filename_normalizer/filename_normalizer.py
6. korean_filename_normalizer/ui_register.py

---

## 다음 단계
1. 추가 확인 필요 파일들의 import 관계 분석
2. 사용자 승인 후 제거 실행
