# EP02: 오픈소스 OCR 모델 5종 실측 비교 — dots.ocr·PaddleOCR-VL·Baidu Unlimited-OCR이 전부 막힌 이유

**시리즈**: OCR 서비스구축 #2
**이 글을 읽고 나면**: "OCR 잘하는 오픈소스 모델"을 이름만 보고 고르면 안 되는 이유와, RTX 5090 + Ollama 환경에서 실제로 뭐가 되고 안 되는지를 직접 검증한 결과를 알 수 있습니다.

---

## 핵심 한 줄 요약
> 논문·모델카드의 벤치마크 점수와, 내 GPU에서 실제로 도는지는 완전히 다른 문제다 — 5개 후보 중 2개는 Ollama 커뮤니티 패키징이 깨져서 아예 실행조차 안 됐다.

> **자주 묻는 질문**
> **Q. 벤치마크 1위 모델을 쓰면 되는 거 아닌가요?** → 벤치마크는 대개 논문 저자의 원본 런타임(vLLM, 커스텀 llama.cpp 포크 등) 기준이다. 내가 쓰는 Ollama에서 그대로 도는지는 별개 문제다.
> **Q. 모델이 Ollama 라이브러리에 있으면 무조건 되는 거 아닌가요?** → 아니다. 커뮤니티가 GGUF만 변환하고 비전 프로젝터(mmproj)를 안 붙이거나, 잘못된 아키텍처로 변환하면 로드 자체가 실패한다.
> **Q. 실패한 모델은 영영 못 쓰나요?** → 아니다. Ollama 자체 엔진이 해당 아키텍처를 지원하게 되거나, 커뮤니티가 재패키징하면 그때 재검토하면 된다. 지금 이 시점의 기록일 뿐이다.

---

## 문제 상황

리서치 자료에 "OCR 잘하는 오픈소스 모델"로 꼽힌 후보는 5개였다: GLM-OCR(기존 사용 중), dots.ocr, olmOCR-2-7B, PaddleOCR-VL, 그리고 나중에 추가로 검토한 Baidu Unlimited-OCR. 전부 RTX 5090에 실제로 받아서 돌려봤다.

---

## STEP 1: 채점 기준 만들기 — "느낌"이 아니라 숫자로

같은 문서를 여러 모델·설정으로 반복 비교하려면 사람이 매번 눈으로 보고 판단할 수 없다. 문자 오류율(CER, Character Error Rate)을 직접 구현했다.

```python
def levenshtein(a: str, b: str) -> int:
    # 편집거리(삽입·삭제·치환 횟수) 계산
    ...

def cer(ref: str, hyp: str):
    rn, hn = normalize(ref), normalize(hyp)
    return levenshtein(rn, hn) / len(rn)
```

정답지는 테스트 이미지를 직접 눈으로 읽어 손으로 옮겨 적었다 — 자동차등록증(정부 서식), 영수증 사진 3장, 손글씨 2장.

---

## STEP 2: dots.ocr — CLIP 비전 인코더 로드 실패

```bash
ollama pull hf.co/anthonym21/dots.ocr-GGUF:F16   # 6.1GB, 정상 다운로드
ollama run hf.co/anthonym21/dots.ocr-GGUF:F16 "test"
```

```json
{"error":"llama-server process has terminated: exit status 1: error: Failed to load CLIP model from ...sha256-b65a1db5..."}
```

다운로드까지는 문제없이 끝났지만, 실제 추론 시점에 비전 인코더 로드 자체가 실패했다. dots.ocr은 자체 아키텍처(DotsOCRForCausalLM)를 쓰는데, Ollama의 표준 엔진이 아직 이 구조를 지원하지 않는다 — GitHub 이슈에도 동일 요청이 열려 있지만 미해결 상태였다.

---

## STEP 3: PaddleOCR-VL — 비전 프로젝터가 아예 없다

```bash
ollama pull MedAIBase/PaddleOCR-VL:0.9b   # 935MB, 정상 다운로드
```

`ollama show`로 확인해보니:

```
Capabilities
    completion
```

`vision` 항목이 없다. 이미지를 보내보면:

```json
{"error":"image input is not supported - hint: if this is unexpected, you may need to provide the mmproj"}
```

이 커뮤니티 빌드는 **언어모델 파트만 올리고 비전 프로젝터(mmproj)를 안 붙였다** — 애초에 이미지를 볼 수 없는 텍스트 전용 패키징이었다. 아키텍처 문제가 아니라 순전히 패키징 실수다.

---

## STEP 4: Baidu Unlimited-OCR — "unlimited-ocr"이라는 이름의 함정

Ollama 로컬 캐시에 `frob/unlimited-ocr:q8_0`이라는 모델이 있었다. `ollama show`로 보니 architecture가 `deepseek2-ocr`로 나와서 처음엔 DeepSeek-OCR인 줄 알았다. 그런데 실제로 리서치해보니 2026-06-22에 공개된 **진짜 바이두(Baidu)의 Unlimited-OCR**(3B MoE, R-SWA 어텐션, OmniDocBench 93%+)이었다 — Ollama의 아키텍처 라벨링이 계열명만 따온 것이었다.

기본 프롬프트로 테스트하니 반복 폭주(`( ) . ( ) . ( ) . ...`)가 났다. 공식 GitHub의 권장 프롬프트를 다시 찾아 적용했다.

```
공식 권장 프롬프트: "document parsing."  (단일 이미지 기준)
```

프롬프트를 바로잡으니 폭주는 멈췄지만, 손글씨 CER 0.22(78% 정확도)로 다음 편에서 다룰 최종 채택 모델보다 크게 낮았다.

---

## STEP 5: olmOCR-2-7B — 유일하게 전부 통과

```bash
ollama pull richardyoung/olmocr2:7b-q8   # Qwen2.5-VL 기반, Ollama 공식 아키텍처 지원
```

`ollama show` 결과 `vision` 캐퍼빌리티 정상, 비전 프로젝터(clip, 676M 파라미터) 정상 로드. 첫 테스트부터 표가 있는 정부 서식 문서에서 **다른 모델이 전부 놓친 우측 표 섹션 전체를 정확히 인식**했다.

---

## STEP 6: 최종 비교표

| 모델 | 결과 |
|------|------|
| glm-ocr(기존) | 실행은 됨. 복잡한 표 섹션 통째 누락, 존재하지 않는 LaTeX 마크업을 지어냄 |
| dots.ocr | **실행 불가** — CLIP 로드 실패 |
| PaddleOCR-VL | **실행 불가** — mmproj 누락, 텍스트 전용 |
| Baidu Unlimited-OCR | 실행됨. 공식 프롬프트로도 손글씨 78% 수준 |
| **olmOCR-2-7B** | **채택** — 표 전체 인식, 손글씨 97~99.8% |

---

## ✅ 완료 확인

- [ ] 5개 모델 전부 `ollama pull` 성공 또는 실패 원인 특정
- [ ] 각 모델에 동일 테스트 이미지 3종(문서·영수증·손글씨) 통과
- [ ] CER 채점 스크립트로 수치 비교표 확정
- [ ] 최종 모델을 프로덕션 Worker 코드에 반영

---

## 다음 편 예고
> **EP03**: 회전 버튼까지 만들어서 배포했는데, 사용자가 찍은 영수증 사진이 이상하게 나왔다. "회전 문제인 줄 알았는데" 진짜 원인은 전혀 다른 곳에 있었다.

---

## 📱 30초 쇼츠 스크립트

**제목**: "OCR 오픈소스 모델 5개 받아봤더니 2개는 실행조차 안 됐다"
**길이**: 29초

| 구간 | 화면 | 자막 |
|------|------|------|
| 00:00~00:04 | 모델 5개 리스트 | "논문에서 추천한 OCR 모델 5개 전부 받아봤다" |
| 00:04~00:10 | dots.ocr 에러 화면 | "CLIP 로드 실패 — 실행 자체가 안 됨" |
| 00:10~00:15 | PaddleOCR-VL 에러 | "비전 프로젝터가 없어서 이미지를 못 봄" |
| 00:15~00:24 | olmOCR-2 표 인식 화면 | "결국 남은 건 하나, 표까지 전부 잡아냈다" |
| 00:24~00:29 | 블로그 링크 | "→ 실측 비교표는 블로그에" |

**해시태그**: `#OCR #오픈소스AI #dotsocr #PaddleOCR #Ollama`
