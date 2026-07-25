# OCR 서비스구축 시리즈 — SEO 태그셋

`_auto/posting_schedule.md`의 태그 형식(시리즈 공통 태그 + 편별 특화 태그)을 그대로 따른다.
네이버 블로그 발행 시 이 문서의 태그를 그대로 복사해 사용.

> ⚠ 이 시리즈는 아직 `_auto/posting_schedule.md`의 발행 일정표(NAS 인프라구축 20편 / 연금·자산관리 38편, 2026-07-21~11-27 예약 완료)에 편입되지 않았다. 기존 일정과 겹치지 않는 별도 슬롯(예: NAS 20편 완주 이후, 또는 격주 3번째 채널)에 넣을지는 발행 전 확인 필요.

---

## 시리즈 공통 태그 (10개)

```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
```

---

## 편별 특화 태그

**EP01: 클라우드 Vision API 대신 집 PC — Ollama + Cloudflare Tunnel로 로컬 GPU를 안전하게 서비스로 노출하기**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
CloudflareAccess ServiceToken Host헤더 온디맨드백엔드 자체호스팅AI 홈서버AI PC서버구축
로컬GPU활용 AI백엔드구축 Tunnel프록시
```

**EP02: 오픈소스 OCR 모델 5종 실측 비교 — dots.ocr·PaddleOCR-VL·Baidu Unlimited-OCR이 전부 막힌 이유**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
dotsocr PaddleOCR olmOCR BaiduOCR GGUF 모델비교 CER문자오류율 OCR정확도 오픈소스VLM비교
비전언어모델 문서인식AI
```

**EP03: "회전 버튼까지 만들었는데 진짜 원인은 해상도였다" — 컨텍스트 예산 초과 버그 발견기**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
컨텍스트윈도우 numctx 비전토큰 이미지다운스케일 VLM버그 AI디버깅 토큰예산
해상도최적화 이미지전처리 AI트러블슈팅
```

**EP04: repeat_penalty의 역설 — 반복 폭주를 막으려다 정확도를 되려 깎아먹은 이야기**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
repeatpenalty 프롬프트엔지니어링 LLM옵션튜닝 반복폭주 AI안전장치설계 재시도패턴
LLM파라미터 추론옵션최적화 텍스트생성버그
```

**EP05: 최신 논문(문서 디워핑)까지 검증했지만 도입하지 않은 이유 + 배포 자동화 회고**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
문서디워핑 UVDoc PaddleOCR documentdewarping 통제실험 논문검증 배포자동화
wrangler deployps1 AI엔지니어링의사결정
```

**EP06: "대비 +15%, 샤프니스 25%"는 어디서 나온 숫자였나 — 그리드서치로 최적 설정값 찾기**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
그리드서치 하이퍼파라미터튜닝 CER문자오류율 이미지전처리 콘트라스트 샤프니스 실측검증
파라미터최적화 데이터사이언스 AI실험설계
```

**EP07: CER이 4.19가 나왔다 — OCR이 망가진 게 아니라 채점 기준이 잘못됐다**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
AIHub 데이터라벨링 CER 데이터셋검증 머신러닝평가 무효측정 벤치마크함정
데이터사이언스 모델검증 QA프로세스
```

**EP08: 슬라이더를 없애지 않고도 손 안 대게 만들기 — 문서 유형 프리셋 설계**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
UX설계 프리셋패턴 프론트엔드 UI투명성 사용자경험 문서유형분류
자바스크립트 웹개발 인터페이스디자인
```

**EP09: 파일 하나와 폴더 통째로는 완전히 다른 UI가 필요했다 — 배치 처리 설계**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
배치처리 UX설계 진행률UI 이동평균 프론트엔드설계 UI분리패턴
자바스크립트 웹개발 사용자경험
```

**EP10: 텍스트로는 다 나오는데 엑셀은 왜 비는가 — 구조화의 조용한 실패**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
LLM구조화 정규식 JSON스키마 프롬프트엔지니어링 안전망패턴 조용한실패
데이터추출 영수증OCR 버그헌팅
```

**EP11: 촬영한 사진이 사라지는 미스터리 — 범인을 세 번 잘못 짚은 이야기**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
모바일웹 getUserMedia 카메라API 버그헌팅 세션스토리지 프론트엔드디버깅
안드로이드웹 브라우저버그 UX복원
```

**EP12: 위치는 아는데 글자는 못 믿는 모델 — 두 모델을 섞어야 했던 이유**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
EasyOCR PaddleOCR Tesseractjs 하이브리드AI 모델조합 텍스트위치탐지
바운딩박스 오버레이UI AI아키텍처설계
```

**EP13: "고치려고 클릭했는데 못 찾는다"는 모순 — 내용 대신 순서를 믿기로 했다**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
알고리즘설계 편집거리 레벤슈타인 순환논리 소프트웨어재설계 사용자피드백
버그헌팅 프론트엔드디버깅 UX개선
```

**EP14: 클릭 한 번으로 테스트하기 — 샘플 갤러리와 라이선스 다시 점검하기(완결편)**
```
로컬LLM Ollama OCR오픈소스 VLM CloudflareWorker CloudflareTunnel 온디바이스AI RTX5090 GPU서버 worksfree
데이터라이선스 CCBY 오픈데이터 웹개발 샘플갤러리 UX개선
개발일지 소프트웨어윤리 데이터거버넌스
```
