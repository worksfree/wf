# EP04: repeat_penalty의 역설 — 반복 폭주를 막으려다 정확도를 되려 깎아먹은 이야기

**시리즈**: OCR 서비스구축 #4
**이 글을 읽고 나면**: LLM/VLM의 "반복 폭주 방지" 옵션을 상시로 걸어두면 안 되는 이유와, 안전장치를 "항상 켜기"가 아니라 "필요할 때만 재시도"로 설계하는 패턴을 알 수 있습니다.

---

## 핵심 한 줄 요약
> repeat_penalty를 상시로 걸어두면 표에 정당하게 반복되는 내용(동그라미 번호, "종합검사" 같은 반복 라벨)까지 억제돼서, 정상 문서의 문자 오류율이 0.19에서 1.08까지 악화될 수 있다. 폭주가 실제로 감지된 경우에만 재시도하는 구조가 정답이었다.

> **자주 묻는 질문**
> **Q. repeat_penalty가 정확히 뭘 하는 옵션인가요?** → 모델이 이미 생성한 토큰을 다시 생성할 확률을 인위적으로 낮추는 옵션이다. 반복 루프에 빠지는 걸 막는 용도로 흔히 쓰인다.
> **Q. 그럼 아예 안 쓰면 되지 않나요?** → 아니다. 흐릿하거나 저해상도인 이미지에서는 여전히 반복 폭주가 실제로 재현된다. 완전히 빼면 그 케이스에서 무방비 상태가 된다.
> **Q. 후처리로 반복을 잘라내는 것만으론 부족한가요?** → 후처리는 이미 생성된 걸 사후에 자르는 것뿐이라, 폭주로 낭비된 토큰·시간은 못 돌려놓는다. repeat_penalty 재시도는 애초에 폭주가 안 나게 유도하는 사전 대응이다.

---

## 문제 상황

EP02에서 확정한 glm-ocr 시절, 흐릿한 영수증 사진에서 텍스트가 수백 번 반복되는 폭주 증상이 있었다. 원인은 이미 알고 있었다 — Ollama의 `repeat_penalty` 옵션으로 막을 수 있다. 새 모델(olmOCR-2)로 교체하면서도 당연히 그대로 가져다 걸었다.

```js
options: {
  temperature: 0, num_predict: 3000, num_ctx: 6144,
  repeat_penalty: 1.3, repeat_last_n: 256,   // ← 상시 적용
}
```

배포 전 마지막 검증 삼아, 이미 CER 0.19로 잘 나왔던 정부 서식 문서를 다시 돌려봤다.

```
CER: 1.084   (기존 0.19에서 오히려 5배 이상 악화)
```

결과가 아예 못 쓸 수준으로 나왔다.

---

## STEP 1: 무엇이 바뀌었는지 하나씩 되돌려보기

의심 가는 옵션을 하나씩 껐다 켜며 재현했다.

```python
tests = [
    ('ctx6144_norepeat',     {'num_ctx':6144}),                                    # CER 0.194
    ('ctx4096_repeat1.3',    {'num_ctx':4096, 'repeat_penalty':1.3}),              # CER 1.084
    ('ctx6144_repeat1.15',   {'num_ctx':6144, 'repeat_penalty':1.15}),             # CER 0.208
]
```

`repeat_penalty`를 빼면 원래대로 돌아오고, 값을 낮춰도(1.3→1.15) 여전히 소폭 나빠진다. **범인은 확정됐다 — repeat_penalty 자체였다.**

---

## STEP 2: 왜 이런 일이 벌어지나

정부 서식 문서에는 "①②③..." 같은 동그라미 번호나 "종합검사"처럼 표 안에서 여러 번 반복되는 라벨이 많다. `repeat_penalty`는 **이미 나온 토큰을 다시 쓸 확률을 인위적으로 낮추는 방식**으로 동작한다 — 이게 흐릿한 사진의 "의미 없는 반복"과 표 문서의 "정당한 반복"을 구분하지 못한다. 정당한 반복까지 억제되면서 모델이 서식을 깨거나 없는 내용을 지어내기 시작한 것이다.

즉 **"반복을 막는 도구"가 "반복이 정상인 문서"에서는 오히려 독**이 된다.

---

## STEP 3: 해결 — 상시 적용에서 "감지 후 재시도"로 전환

핵심 아이디어는 간단하다. **1차 호출은 penalty 없이 시도하고, 후처리로 실제 폭주가 감지된 경우에만 penalty를 걸어 재시도한다.**

```js
const BASE_OPTIONS = { temperature: 0, num_predict: 3000, num_ctx: 6144 };
const REPEAT_RETRY_OPTIONS = { ...BASE_OPTIONS, repeat_penalty: 1.3, repeat_last_n: 256 };

async function runOcr(env, imageBase64) {
  const first = await callOllamaGenerate(env, imageBase64, BASE_OPTIONS);
  const firstCleaned = stripMarkupArtifacts(first);
  const firstFinal = truncateRunawayRepetition(firstCleaned);

  if (firstFinal.length === firstCleaned.length) {
    return { text: firstFinal, lowConfidence: false }; // 폭주 없음 — 재시도 없이 반환
  }

  // 폭주가 감지된 경우에만 penalty를 걸어 재시도
  const retry = await callOllamaGenerate(env, imageBase64, REPEAT_RETRY_OPTIONS);
  const retryCleaned = stripMarkupArtifacts(retry);
  const retryFinal = truncateRunawayRepetition(retryCleaned);
  if (retryFinal.length > firstFinal.length) return { text: retryFinal, lowConfidence: true };
  return { text: firstFinal, lowConfidence: true };
}
```

`truncateRunawayRepetition`이 "잘라낼 게 있었는지"를 폭주 감지 신호로 그대로 재활용한다는 게 포인트다 — 별도의 판단 로직을 새로 만들 필요가 없었다.

```js
// 반복 폭주 감지 — 줄 시작 접두어가 최근 몇 줄 안에서 3번째 등장하면 그 지점부터 잘라낸다
function truncateRunawayRepetition(text) {
  const lines = text.split("\n");
  const WINDOW = 6, PREFIX_LEN = 16, REPEAT_THRESHOLD = 3;
  const counts = new Map();
  const order = [];
  for (let i = 0; i < lines.length; i++) {
    const prefix = lines[i].trim().slice(0, PREFIX_LEN);
    if (prefix.length >= PREFIX_LEN) {
      const next = (counts.get(prefix) || 0) + 1;
      counts.set(prefix, next);
      if (next >= REPEAT_THRESHOLD) return lines.slice(0, i).join("\n").trim();
      order.push(prefix);
      if (order.length > WINDOW) counts.set(order.shift(), (counts.get(order[0]) || 1) - 1);
    }
  }
  return text;
}
```

이 재시도 구조 덕분에 **정상 문서는 추가 호출 없이 그대로 빠르게 처리**되고, **폭주가 실제로 벌어진 소수 케이스에서만 한 번 더 호출**해서 시간을 쓴다.

---

## STEP 4: 덤으로 얻은 것 — "낮은 신뢰도" 신호

폭주가 감지됐다는 사실 자체가 "이 이미지는 모델이 다루기 어려웠다"는 신뢰할 만한 신호였다. 이 신호를 그대로 응답에 실어 보내, 클라이언트가 사용자에게 재촬영을 안내하도록 확장했다(다음 편에서 이어서 다룬다).

```js
return json({ ok: true, text: result.text, low_confidence: result.lowConfidence, ... });
```

---

## ✅ 완료 확인

- [ ] repeat_penalty 상시 적용 시 정상 문서 CER 악화 재현 확인
- [ ] 1차 호출(penalty 없음) → 폭주 감지 시에만 2차 재시도 구조로 전환
- [ ] 정상 문서는 재시도 없이 기존 정확도 유지 확인
- [ ] 흐릿한 이미지에서는 재시도가 실제로 발동하는지 확인

---

## 다음 편 예고
> **EP05**: "구겨진 영수증"이 마지막 약점으로 남았다. 최신 문서 디워핑(dewarping) 논문까지 찾아 실제로 설치해 통제 실험을 해봤는데 — 결론은 "도입하지 않는다"였다. 그 이유와, 전체 배포 자동화 회고로 시리즈를 마무리한다.

---

## 📱 30초 쇼츠 스크립트

**제목**: "반복 폭주 막으려다 정확도가 5배 나빠진 이유"
**길이**: 28초

| 구간 | 화면 | 자막 |
|------|------|------|
| 00:00~00:04 | CER 0.19 → 1.08 그래프 | "폭주 방지 옵션을 걸었더니 오차율이 5배로" |
| 00:04~00:10 | 동그라미 번호 표 이미지 | "표엔 원래 반복되는 내용이 많다" |
| 00:10~00:12 | 억제된 반복 → 깨진 서식 | "그 반복까지 억제되면서 서식이 깨졌다" |
| 00:12~00:24 | 감지 후 재시도 구조 다이어그램 | "그래서 1차는 안전장치 없이, 폭주가 감지될 때만 재시도" |
| 00:24~00:28 | 블로그 링크 | "→ 코드 전체는 블로그에" |

**해시태그**: `#LLM옵션 #repeatpenalty #프롬프트엔지니어링 #Ollama #버그해결`
