# ocr-eval — OCR 파라미터 최적화 테스트 하네스

`service/ocr`(WorksFree 허브 OCR 서비스, `synology-web/service/ocr/`)의 콘트라스트·샤프니스
설정 슬라이더 최적값을 실측으로 찾기 위한 평가 프로젝트. 2026-07-23 새벽 세션에서
사용자가 유통/요식/제조업 AI-Hub 데이터셋으로 파라미터 테스트를 요청했으나, AI-Hub가
데이터셋별 본인인증·목적 심사를 요구해 무인 자동화가 불가능함을 확인 → 그 부분만 사람이
처리하고 나머지(전처리 스윕·정확도 채점·리포트)는 전부 자동화하는 구조로 대신 구현.

## 구성

| 파일 | 역할 |
|---|---|
| `ocr_eval_lib.py` | 프로덕션 OCR 파이프라인 재현 공용 라이브러리(다운스케일/콘트라스트/샤프니스/Ollama 호출/CER 채점) |
| `AIHub_샘플_다운로드_가이드.md` | AI-Hub 회원가입~다운로드~파일 배치 단계별 가이드 (사람이 해야 하는 부분) |
| `ingest_aihub_samples.py` | `aihub_samples/{retail,fnb,manufacturing}/`에 파일을 넣고 실행하면 자동으로 파라미터 스윕 + 리포트 생성 |
| `aihub_samples/` | AI-Hub에서 받은 표본을 넣는 폴더 (현재 비어 있음 — 가이드 참고) |

## 로컬 6종 표본 스윕 (2026-07-23, 완료)

AI-Hub 승인 대기 중에도 손 놓고 있지 않기 위해, 이전 세션에서 이미 확보해 둔 로컬 표본
6개(손글씨 2·긴 문서 2·영수증 2, `scratchpad/ocr_lab/`)로 먼저 동일한 방법론의 스윕을
실행함 — 스크립트: `scratchpad/ocr_lab/sweep_contrast_sharpen.py`, 결과:
`scratchpad/ocr_lab/sweep_report.md`. scratchpad는 세션 종료 후 정리될 수 있는 임시
공간이라, 최종 결과가 나오면 이 폴더(`ocr-eval/`)에도 리포트 사본을 남겨 영구 보존한다.

## 방법론

1단계(coarse): 콘트라스트 7단계 x 샤프니스 7단계 = 49개 조합을 전체 표본에 전수 테스트.
2단계(fine): 카테고리(문서 종류)별 1단계 최적점 주변을 5x5=25개 조합으로 정밀 탐색.
정확도는 CER(Character Error Rate, Levenshtein distance 기반) — 낮을수록 좋음.
`temperature=0`(결정론적 출력)이라 같은 설정은 반복 없이 1회만 테스트한다.

## 사용 순서

1. `AIHub_샘플_다운로드_가이드.md`를 보고 회원가입 → 데이터셋 신청 → 승인 대기
2. 승인된 데이터를 `aihub_samples/{retail,fnb,manufacturing}/`에 압축 해제
3. `python ingest_aihub_samples.py` 실행
4. `aihub_sweep_report.md` 확인 — 업종별 추천 콘트라스트/샤프니스 값과 로컬 6종 표본
   결과를 비교해, `service/ocr/index.html`의 슬라이더 기본값(현재 콘트라스트 +15%,
   샤프니스 25%)을 조정할지 결정
