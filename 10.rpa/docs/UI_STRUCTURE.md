# WorksFree Apps - UI 구조

앱별 UI 구성과 공통 UI 패턴을 정리합니다. (원문: UI_STRUCTURE_DOCUMENTATION.md)

## 포함 앱
- BOM2Excel
- Conversion Verifier
- DWG Classifier
- Korean Filename Normalizer

## 공통 UI 패턴 요약
- 적응형 UI: 해상도별 크기/폰트 자동 조정
- 공통 버튼: 폴더/파일 선택, 실행, 설정/등록, 업데이트, 종료
- 상태 표시: 진행률, 파일 카운트, 크레딧, 스피너
- 관리자 모드: 로그 프레임, 테스트 데이터 관리, 고급 설정
- 색상 코딩: 성공/오류/정보/경고

상세 컴포넌트 배치는 각 앱의 `ui_main.py`, `ui_setting.py` 구현을 참고하세요.
