# 테스트 구조 및 작성 가이드

## 📁 테스트 파일 위치 규칙

모든 테스트 파일은 **`90.tests/`** 디렉토리 아래에 원본 코드의 폴더 구조와 동일하게 배치됩니다.

### 구조 매핑

```
10.rpa/
├── 10.common/              → 90.tests/10.common/
│   ├── wf_email.py        → test_wf_email_*.py
│   ├── wf_credit_manager.py → test_wf_credit_*.py
│   └── wf_register.py     → test_wf_register_*.py
│
├── 30.apps/               → 90.tests/30.apps/
│   └── bom2excel/         → 90.tests/30.apps/bom2excel/
│       └── automation.py  → test_automation_*.py
│
└── 90.tests/              # 모든 테스트 파일 위치
    ├── 10.common/
    │   ├── test_wf_email_success.py
    │   ├── test_wf_email_config_save.py
    │   ├── test_wf_credit_*.py
    │   └── ...
    └── 30.apps/
        └── bom2excel/
            ├── test_integration.py
            └── test_unlimited_credits.py
```

## 📝 테스트 파일 명명 규칙

### 패턴: `test_{module_name}_{feature}.py`

- **Prefix**: 항상 `test_`로 시작
- **Module**: 테스트 대상 모듈 이름 (예: `wf_email`, `automation`)
- **Feature**: 테스트하는 기능 (예: `success`, `config_save`, `integration`)

### 예시

```
wf_email.py               → test_wf_email_success.py
                          → test_wf_email_config_save.py
                          → test_wf_email_smtp_connection.py

automation.py             → test_automation_integration.py
                          → test_automation_error_handling.py

wf_credit_manager.py      → test_wf_credit_refresh.py
                          → test_wf_credit_logging_integration.py
```

## 🏗️ 테스트 파일 템플릿

### 기본 구조

```python
"""
{기능 설명}

위치: 90.tests/{폴더경로}/{파일명}.py
테스트 대상: {원본경로}/{원본파일}.py
"""
import sys
import os
import pytest

# 경로 설정 (90.tests 하위 → 프로젝트 루트)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 90.tests/10.common → 10.rpa/10.common
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
common_dir = os.path.join(project_root, '10.common')
sys.path.insert(0, common_dir)

# 테스트 대상 모듈 import
import wf_email as wfm
import wf_log as wflog
import logging

# 로거 설정
logger = wflog.get_app_logger('test_name', console_level=logging.DEBUG)
wfm.set_logger(logger)


@pytest.mark.unit  # 또는 @pytest.mark.integration
def test_feature_name():
    """기능 설명"""
    # Given (준비)
    expected_value = "test"
    
    # When (실행)
    result = some_function(expected_value)
    
    # Then (검증)
    assert result == expected_value


if __name__ == '__main__':
    # 직접 실행 시
    test_feature_name()
    print("✅ 테스트 성공!")
```

## 📂 테스트 위치 결정 가이드

### 1. 공통 모듈 테스트 (`10.common/`)

**대상**: `10.rpa/10.common/` 내의 모든 공통 모듈

**위치**: `90.tests/10.common/`

**예시**:
```python
# 10.rpa/10.common/wf_email.py 테스트
# → 90.tests/10.common/test_wf_email_*.py

# 10.rpa/10.common/wf_credit_manager.py 테스트
# → 90.tests/10.common/test_wf_credit_*.py
```

### 2. 앱별 테스트 (`30.apps/`)

**대상**: `10.rpa/30.apps/{앱이름}/` 내의 앱별 코드

**위치**: `90.tests/30.apps/{앱이름}/`

**예시**:
```python
# 10.rpa/30.apps/bom2excel/automation.py 테스트
# → 90.tests/30.apps/bom2excel/test_automation_*.py

# 10.rpa/30.apps/bom2excel/ui_main.py 테스트
# → 90.tests/30.apps/bom2excel/test_ui_*.py
```

### 3. 통합 테스트

**여러 모듈 간 상호작용 테스트**

**위치**: 주된 모듈의 테스트 폴더

**예시**:
```python
# wf_credit_manager + wf_googlesheets 통합
# → 90.tests/10.common/test_wf_credit_integration.py

# automation + wf_email 통합
# → 90.tests/30.apps/bom2excel/test_integration.py
```

## 🔧 경로 설정 패턴

### `90.tests/10.common/` 테스트

```python
# 90.tests/10.common/test_wf_*.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
common_dir = os.path.join(project_root, '10.common')
sys.path.insert(0, common_dir)
```

### `90.tests/30.apps/{앱}/` 테스트

```python
# 90.tests/30.apps/bom2excel/test_*.py
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
common_dir = os.path.join(project_root, '10.common')
app_dir = os.path.join(project_root, '30.apps', 'bom2excel')
sys.path.insert(0, common_dir)
sys.path.insert(0, app_dir)
```

## ✅ 체크리스트

새로운 테스트 파일 작성 시:

- [ ] `90.tests/` 아래 적절한 폴더에 위치
- [ ] 파일명이 `test_`로 시작
- [ ] 원본 코드 구조와 매핑됨
- [ ] 파일 상단에 독스트링 (위치, 테스트 대상 명시)
- [ ] 경로 설정 코드 포함
- [ ] `@pytest.mark.unit` 또는 `@pytest.mark.integration` 마커 추가
- [ ] AAA 패턴 (Given-When-Then) 사용
- [ ] `if __name__ == '__main__':` 블록으로 직접 실행 가능

## 🎯 좋은 테스트 예시

```python
"""
이메일 설정이 로컬에 저장되는지 테스트

위치: 90.tests/10.common/test_wf_email_config_save.py
테스트 대상: 10.common/wf_email.py - init() 함수의 로컬 저장 기능
"""
import sys
import os
import json
from pathlib import Path
import pytest

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
common_dir = os.path.join(project_root, '10.common')
sys.path.insert(0, common_dir)

import wf_email as wfm


@pytest.mark.integration
def test_email_config_save_to_local():
    """구글 시트에서 로드한 이메일 설정이 로컬에 저장되는지 검증"""
    # Given - 로컬 설정 초기화
    config_file = Path.home() / '.wf_rpa' / 'wf_rpa_config.json'
    _clear_local_email_settings(config_file)
    
    # When - init 실행 (구글 시트 → 로컬 저장)
    wfm.init(common_dir)
    
    # Then - 설정 파일 검증
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    email_settings = config.get('email_settings', {})
    assert email_settings.get('email_from'), "email_from이 저장되어야 함"
    assert email_settings.get('email_to'), "email_to가 저장되어야 함"
    assert email_settings.get('login_key'), "login_key가 저장되어야 함"


def _clear_local_email_settings(config_file):
    """테스트용 헬퍼: 로컬 이메일 설정 초기화"""
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['email_settings'] = {
            'use_local_email_config': False,
            'email_from': '',
            'email_to': '',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'login_key': ''
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
```

## 📚 참고 사항

1. **pytest 실행**: 프로젝트 루트(`10.rpa/`)에서 `pytest` 명령 실행
2. **독립 실행**: 각 테스트 파일은 `python test_*.py`로도 실행 가능
3. **Fixture 활용**: `conftest.py`의 공통 fixture 적극 활용
4. **Mock 사용**: 외부 의존성(구글 시트, SMTP 등)은 모킹

## 🔗 관련 문서

- [90.tests/README.md](./README.md) - 전체 테스트 가이드
- [pytest.ini](../pytest.ini) - pytest 설정
- [conftest.py](./conftest.py) - 공통 fixture
