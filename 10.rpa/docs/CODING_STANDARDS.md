# 코딩 표준 및 네이밍 컨벤션

본 문서는 모든 WorksFree 앱에 공통 적용되는 함수/이벤트/내부 헬퍼 네이밍 규칙을 정의합니다.

---

## 함수 네이밍 컨벤션 (발췌)

(원문: FUNCTION_NAMING_CONVENTION.md)

## 개요
앱스토어 확장을 위한 일관된 코드 패턴 구축 목적으로, 모든 RPA 앱에서 동일한 함수 네이밍 규칙을 적용합니다.

## 공통 패턴
- 창 열기: `open_*_window`
- 메인 기능: `start_*`
- 이벤트 핸들러: `on_*`
- 내부 헬퍼: `_*`

## 예시
- 등록: `check_user_registration()`, `open_registration_window()`, `post_registration_update()`
- 크레딧: `update_credit_display()`, `on_refresh_credit()`
- 스피너: `start_spinner()`, `stop_spinner()`
- BOM2Excel: `start_bom_extraction()`
- DWG: `start_classification()`
- CV: `start_conversion_check()`
- KFN: `start_normalization()`

자세한 세부 목록과 리팩토링 이력은 히스토리 문서를 참고하세요.
