# 정적 테스트 (Static Testing)

## 개요
코드를 실행하지 않고 구문, 스타일, 보안 취약점을 검사하는 정적 분석 도구 모음입니다.

## 디렉토리 구조
```
90.tests/static/
├── run_static_tests.py      # 메인 실행 스크립트
├── results/                  # 테스트 결과 저장 폴더
│   ├── static_test_report_YYYYMMDD_HHMMSS.txt
│   └── static_test_results_YYYYMMDD_HHMMSS.json
└── README.md                 # 이 파일
```

## 실행 방법

### 전체 테스트 실행
```bash
cd d:\drive_files\10.worksfree\10.rpa\90.tests\static
python run_static_tests.py
```

### 개별 도구 실행
```bash
# 구문 검사
python -m py_compile path/to/ui_main.py

# 스타일 검사 (Flake8)
python -m flake8 path/to/ui_main.py --max-line-length=120 --statistics

# 보안 검사 (Bandit)
python -m bandit -r path/to/ui_main.py -f json
```

## 테스트 항목

### 1. 구문 검사 (Syntax Check)
- **도구**: `py_compile`
- **목적**: Python 문법 오류 검출
- **통과 조건**: 0개 오류

### 2. 스타일 검사 (Flake8)
- **도구**: `flake8`
- **목적**: PEP 8 스타일 가이드 준수 여부
- **주요 검사 항목**:
  - 들여쓰기 및 공백 문제
  - 줄 길이 (최대 120자)
  - 사용하지 않는 변수/임포트
  - 함수 정의 간격
- **통과 조건**: 0개 경고 (현재는 WARNING으로 표시)

### 3. 보안 검사 (Bandit)
- **도구**: `bandit`
- **목적**: 보안 취약점 탐지
- **심각도**:
  - HIGH: 즉시 수정 필요
  - MEDIUM: 검토 필요
  - LOW: 정보성
- **통과 조건**: HIGH 0개

## 최근 테스트 결과 (2025-11-20 12:32:29)

### 요약
| 앱 이름 | 구문검사 | 스타일검사 | 보안검사 |
|--------|---------|-----------|---------|
| DWG Classifier | ✓ 통과 | ⚠ 265개 | ⚠ 21개 (LOW) |
| BOM2Excel | ✓ 통과 | ⚠ 302개 | ⚠ 29개 (LOW) |
| Conversion Verifier | ✓ 통과 | ⚠ 247개 | ⚠ 21개 (LOW) |
| Korean Filename Normalizer | ✓ 통과 | ⚠ 284개 | ⚠ 29개 (LOW) |

**총 테스트**: 12개  
**통과**: 4개 (구문검사 전체 통과)  
**경고**: 8개 (스타일 + 보안)  
**실패**: 0개

### 주요 스타일 이슈 (공통)

#### 높은 빈도 이슈
1. **W293** - 빈 줄에 공백 문자 포함 (206~210개)
   - 영향: 낮음 (가독성 문제만)
   - 수정: 자동 포매터 적용

2. **E702** - 세미콜론으로 여러 구문 한 줄에 작성 (1~59개)
   - 영향: 중간 (가독성 저하)
   - 예: `if x: y=1; z=2`
   - 수정: 별도 줄로 분리

3. **E701** - 콜론으로 여러 구문 한 줄에 작성 (3~36개)
   - 영향: 중간
   - 예: `if x: return y`
   - 수정: 별도 줄로 분리

4. **E231** - 쉼표 뒤 공백 누락 (9~38개)
   - 영향: 낮음
   - 예: `func(a,b,c)` → `func(a, b, c)`

5. **E501** - 줄 길이 초과 (7~22개)
   - 영향: 중간 (120자 초과)
   - 수정: 줄 바꿈 또는 리팩토링

#### 중요 이슈
1. **F811** - 사용하지 않는 변수 재정의 (5~12개)
   - 영향: 높음 (버그 가능성)
   - 예: `Path` 임포트 중복
   - 수정: 불필요한 임포트 제거

2. **E402** - 모듈 임포트가 최상단에 없음 (11~12개)
   - 영향: 중간 (코드 구조)
   - 수정: 임포트를 파일 상단으로 이동

3. **F841** - 사용하지 않는 로컬 변수 (1~4개)
   - 영향: 낮음
   - 예: `except Exception as e:` (e 미사용)
   - 수정: `except Exception:` 또는 변수 활용

### 보안 이슈

모든 앱에서 **LOW** 등급 이슈만 발견됨 (HIGH/MEDIUM 없음):
- 주로 정보성 경고 (assert 사용, subprocess 호출 등)
- 즉시 수정 필요한 보안 취약점 없음

## 개선 계획

### 단기 (즉시 가능)
1. **자동 포매터 적용**
   ```bash
   pip install black autopep8
   black --line-length 120 ui_main.py
   ```

2. **공백 정리**
   - W293, W291, W292 자동 수정

3. **임포트 정리**
   - F811, E401 수정
   - `isort` 도구 활용

### 중기 (리팩토링 시)
1. **한 줄 구문 분리**
   - E701, E702 수정
   - 가독성 향상

2. **긴 줄 분리**
   - E501 수정
   - 120자 제한 준수

3. **사용하지 않는 변수 제거**
   - F841 수정

### 장기 (아키텍처 개선)
1. **CI/CD 통합**
   - 커밋 전 자동 검사
   - Pre-commit hook 설정

2. **코드 품질 목표 설정**
   - Flake8 점수 목표: 90점 이상
   - 점진적 개선

## 도구 설치

```bash
pip install pylint flake8 bandit black autopep8 isort
```

## 참고 자료
- [PEP 8 스타일 가이드](https://peps.python.org/pep-0008/)
- [Flake8 문서](https://flake8.pycqa.org/)
- [Bandit 보안 검사](https://bandit.readthedocs.io/)
- [함수 네이밍 컨벤션](../../FUNCTION_NAMING_CONVENTION.md)

## 변경 이력
- 2025-11-20: 정적 테스트 스크립트 초기 구축 및 첫 실행
