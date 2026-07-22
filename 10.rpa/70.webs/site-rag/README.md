# site-rag — PC 로컬 LLM 기반 RAG 인덱스 빌더

WorksFree 허브의 "🤖 AI 상담사" 노드(`synology-web/consulting/ai-helper/`)가 쓰는 RAG(검색 증강 생성) 인덱스를
PC에서 오프라인으로 빌드하는 프로젝트. 빌드 결과는 **Cloudflare Vectorize**에 업로드하고, 실제 질의응답은
Cloudflare Worker(`biz-rag`)가 Vectorize로 검색 → PC의 Ollama로 질문 임베딩·답변 생성을 요청하는 구조다.

전체 아키텍처는 최상위 계획 문서 참고. 이 프로젝트는 "①오프라인 빌드" 단계만 담당한다.

> **왜 정적 JSON이 아니라 Vectorize인가**: 처음엔 인덱스를 `rag_index.json`으로 만들어 허브 정적 경로에
> 배포하고 Worker가 통째로 fetch+parse해서 코사인 유사도를 직접 계산하는 방식으로 설계했다. 그런데
> 45.Slife 폴더를 포함해 실제로 빌드해보니 청크 6,305개·80MB가 나왔고, 이 정도 크기를 매 요청마다
> Worker 메모리(128MB 한도)에 올리는 건 위험했다. 그래서 검색 자체를 Cloudflare Vectorize에 맡기는
> 구조로 바꿨다 — 부수 효과로, 인덱스 내용이 더 이상 URL로 직접 열어볼 수 있는 공개 정적 파일이 아니라
> Worker의 인증된 `/chat` 엔드포인트를 통해서만 조회 가능해져 45.Slife 같은 민감한 소스의 노출 범위도
> 줄었다(다만 로그인한 컨설턴트가 질문으로 끌어낼 수는 있다는 점은 동일).

## 사전 준비 (PC)

- Ollama 설치 (`winget install Ollama.Ollama`)
- 임베딩 모델: `ollama pull bge-m3` (1024차원, 멀티링구얼)
- 생성 모델: `gemma4:12b` (이미 로컬에 있으면 재사용 — 없으면 `ollama pull gemma4:12b`)
  - `qwen3:30b` 등 hybrid-thinking 계열 모델은 답변 전 긴 reasoning을 강제로 생성해 응답이 12초 이상
    걸리므로 인터랙티브 챗봇에는 권장하지 않음 (직접 측정: qwen3:30b 웜 상태 12.5초 vs gemma4:12b 웜 상태 5~10초)

## 사용법

### 1. 인덱싱 대상 등록

`rag_sources.txt`에 경로 패턴을 한 줄씩 추가한다. **이 파일에 없는 경로는 인덱싱되지 않는다** —
고객 컨설팅 원본·개인정보성 자료가 실수로 섞이지 않도록 화이트리스트 방식을 강제한다.

```
../biz-support/cards/*.json
../../../30.publish/시놀로지NAS_풀스택가이드/**/*.md
```

지원 형식: `.json`(biz-support 카드 스키마), `.md`(`##` 헤딩 기준 자동 분할), `.txt`, `.pdf`, `.pptx`.
그 외 형식(이미지, `.gdoc` 등)은 로더가 없어 자동으로 건너뛴다.

⚠ **폴더를 통째로 추가하기 전에 내용을 먼저 훑어볼 것.** Vectorize로 옮기면서 URL로 직접 열어볼 수 있는
정적 파일은 없어졌지만, 인덱싱된 내용은 로그인한 사용자가 챗봇에 질문해서 끌어낼 수 있다는 점은 여전하다.
개인정보·고객 데이터가 섞인 폴더는 반드시 검토 후 추가할 것.

### 2. 인덱스 빌드

```powershell
pip install -r requirements.txt   # pypdf, python-pptx — PDF/PPTX 파싱용 (최초 1회)
ollama serve   # 이미 실행 중이면 생략
python scripts/build_rag_index.py
```

`vectors.ndjson`이 생성된다 (한 줄당 `{id, values, metadata:{title, source, text, chunk_ref}}`).
이 파일은 `.gitignore` 대상이며 언제든 재생성 가능하다.

### 3. Vectorize에 업로드

최초 1회, `synology-web/workers/biz-rag/` 폴더에서 인덱스를 만든다:

```powershell
npx wrangler vectorize create biz-rag-index --dimensions=1024 --metric=cosine
```

빌드할 때마다 `vectors.ndjson`을 업로드한다:

```powershell
npx wrangler vectorize insert biz-rag-index --file=../../../site-rag/vectors.ndjson
```

같은 `id`(원본 청크의 sha1 해시)로 다시 insert하면 upsert되어 덮어써진다. 소스 문서를 **삭제**한 경우
(예: 카드 하나를 없앰) 그 청크는 옛 id로 Vectorize에 남아 있게 되므로, 소스가 크게 줄어드는 재구축이라면
`wrangler vectorize delete-index biz-rag-index` 후 `create`+`insert`로 완전히 새로 만드는 편이 안전하다.

허브 쪽에는 배포할 정적 파일이 없다 — `synology-web/deploy.ps1`은 이 기능과 무관하게 그대로 두면 된다.

## 소스 추가 절차

1. `rag_sources.txt`에 경로 패턴 한 줄 추가 (민감 정보 여부 직접 확인 후)
2. `python scripts/build_rag_index.py` 재실행
3. `npx wrangler vectorize insert biz-rag-index --file=vectors.ndjson` (workers/biz-rag 폴더에서)

## PC 쪽 Cloudflare Tunnel / Access 설정

별도 문서: [`PC_설정가이드.md`](PC_설정가이드.md)
