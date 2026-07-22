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
