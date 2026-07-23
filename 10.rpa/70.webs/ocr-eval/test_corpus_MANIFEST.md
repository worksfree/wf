# OCR 테스트 코퍼스 (test_corpus/) — 출처·라이선스

2026-07-24. "인터넷에서 300장 수집" 요청에 대해, 무작위 스크래핑(도구 없음 + 저작권 불명확) 대신
**라이선스가 명시된 공개 데이터셋에서 실제로 다운로드**하는 방식으로 대체했다. 재현 방법은
`collect_test_corpus.py` 참고. 원본 이미지 파일 자체(660MB)는 용량 때문에 git에는 커밋하지
않는다(`.gitignore`) — 이 문서와 스크립트만 저장소에 남긴다.

## 구성 (총 298장)

| 폴더 | 장수 | 출처 | 라이선스 | 비고 |
|---|---|---|---|---|
| `receipt/korie_*` | 286 | [KORIE](https://github.com/MahmoudSalah/KORIE) (Mathematics지 2026, Google Drive 공개) | README에 명시 없음 — 학술 벤치마크, 로컬 R&D 테스트 용도로 사용. 재배포/상업 활용 전 저자(mahmoud.salah@aun.edu.eg) 확인 권장 | detection test+val 세트, 실제 한국 소매 영수증(구겨짐·번짐·기울어짐 등 실제 열화 포함) |
| `receipt/hf_*` | 20 | [HumynLabs/Korean_Receipts_Dataset](https://huggingface.co/datasets/HumynLabs/Korean_Receipts_Dataset) | CC-BY-4.0 | 마트·음식점 영수증 |
| `handwriting/hf_*` | 9 | [HumynLabs/Korean_Handwritten_Notes_Dataset](https://huggingface.co/datasets/HumynLabs/Korean_Handwritten_Notes_Dataset) | CC-BY-4.0 | 손글씨 노트 |
| `document/hf_*` | 3 | [Kratos-AI/Korean-Documents-Dataset](https://huggingface.co/datasets/Kratos-AI/Korean-Documents-Dataset) | 명시 없음(HF 페이지 참고) | 스캔 문서 |

## 왜 300장을 못 채웠나 / 왜 영수증이 대부분인가

- KORIE만으로 286장이 확보돼 목표치 대부분을 차지한다 — 마침 이번 세션 로컬 스윕에서 영수증
  카테고리가 CER이 가장 높게(가장 어렵게) 나온 카테고리라, 실측 검증 우선순위와도 맞아떨어진다.
- 손글씨·일반문서는 라이선스가 명확하고 게이트 없이 즉시 받을 수 있는 대형 공개셋을 찾지
  못해 소규모(9장·3장) 표본만 확보됨 — `10.rpa/70.webs/ocr-eval/AIHub_샘플_다운로드_가이드.md`의
  AI-Hub 승인 절차를 거치면 이 두 카테고리를 훨씬 크게 보강할 수 있다(한국어 글자체 이미지·
  금융업 특화 문서 OCR 데이터 등).

## 사용법

```powershell
cd D:\drive_files\10.worksfree\10.rpa\70.webs\ocr-eval
python collect_test_corpus.py   # 최초 실행 시 660MB 다운로드, 이후 재실행은 캐시 재사용
```

`sweep_contrast_sharpen.py` 계열 스크립트에서 `test_corpus/{receipt,handwriting,document}/`를
이미지 소스로 지정해 사용할 수 있다(단, 정답 텍스트가 없으므로 CER 채점은 불가 — 인식 결과
육안 검수나 처리 성공률 측정 등 정답 없이도 가능한 지표에 활용).
