# 정적 분석 및 품질 도구 계획

(원문: STATIC_ANALYSIS_TODO.md)

## 목표
- 코드 품질 자동 검증 (구문, 타입, 보안, 복잡도)
- 회귀 방지 및 유지보수성 향상
- CI/CD 통합 준비

## Tier 1 (즉시 적용)
- Ruff: `ruff check 10.rpa --exclude dist`
- MyPy: `mypy 10.rpa/10.common --ignore-missing-imports --no-strict-optional`
- Bandit: `bandit -r 10.rpa/10.common -ll -f screen`

## Tier 2 (중기)
- Radon, validate_config_schema.py, Vulture

## Tier 3 (선택)
- pydeps, isort, pylint

## 통합 실행 스크립트 예시
`scripts/run_static_analysis.sh` 또는 `.ps1`로 일괄 실행합니다.

## CI/CD 예시
GitHub Actions에서 ruff/mypy/bandit/radon/vulture를 실행하는 워크플로우 샘플을 제공합니다.
