/**
 * ocr-service — "OCR" 노드(서비스 섹션)용 Cloudflare Worker.
 *
 * 흐름:
 *   1) Supabase access_token으로 로그인 사용자를 검증한다 (biz-rag/biz-report와 동일 패턴).
 *   2) KV로 사용자당 일일 호출 횟수를 제한한다 (PC GPU를 실제로 쓰는 기능이라 남용 방지 필요).
 *   3) PC의 Ollama(olmOCR-2-7B 모델, Cloudflare Tunnel + Access로 보호됨)에 이미지를 보내 텍스트를 추출한다.
 *   4) PC가 꺼져 있으면 명확한 에러 코드를 반환한다.
 *
 * 모델 비교 실측 결과 (2026-07-22, RTX 5090 로컬 PC에서 자동차등록증 PDF·영수증 사진·손글씨
 * 이미지로 직접 테스트, 문자 단위 오류율로 채점):
 *   - glm-ocr(0.9B, 이전 기본값): 표가 있는 복잡한 문서에서 표 섹션 전체를 통째로 누락하는
 *     현상이 반복 확인됨. 동그라미 숫자·표 서식이 많으면 실제 없는 LaTeX 마크업을 지어냄.
 *   - dots.ocr, PaddleOCR-VL, DeepSeek-OCR(frob/unlimited-ocr) — 이 PC의 Ollama에서 전부
 *     실사용 불가로 확인(dots.ocr: CLIP 비전 인코더 로드 자체가 실패 / PaddleOCR-VL: 커뮤니티
 *     빌드에 mmproj가 누락되어 텍스트 전용으로만 동작 / DeepSeek-OCR: 프롬프트를 바꿔가며
 *     재시도해도 반복 폭주 또는 빈 응답만 발생). 세 모델 모두 아키텍처 자체보다 Ollama용
 *     커뮤니티 패키징이 아직 불완전한 것이 원인으로 보임.
 *   - olmOCR-2-7B(Qwen2.5-VL 기반): 위 문제가 없고 표 섹션까지 정확히 인식, 손글씨는
 *     별도 후처리 없이도 오차율 1~3% 수준(사실상 목표 90% 초과 달성). 이번 교체의 근거.
 *
 * 반드시 /api/generate 사용 (biz-rag·glm-ocr와 동일 패턴 유지, /api/chat의 vision 처리에
 * 알려진 문제가 있어 비권장). temperature:0으로 결과 안정성 확보.
 *
 * 반복 폭주는 모델을 바꿔도 여전히 발생한다 — 실측으로 확인: olmOCR-2도 심하게 흐릿하거나
 * 저해상도인 사진에서는 동일 문구를 수십 회 반복하는 증상이 재현됨. repeat_penalty +
 * 응답 후처리(truncateRunawayRepetition)는 모델과 무관한 안전장치이므로 그대로 유지한다.
 *
 * 고해상도 원본 사진(스마트폰 12MP=4000x3000 등)을 그대로 보내면 비전 인코더가 소모하는
 * 토큰 수가 모델의 컨텍스트 예산(num_ctx)을 넘어서 요청이 실패하거나 응답이 몇 글자만에
 * 잘리는 현상이 실측으로 확인됨(원인 규명 전에는 "회전 문제"로 오인하기 쉬우니 주의).
 * 그래서 클라이언트(service/ocr/index.html)에서 긴 변 기준 1800px로 미리 축소해 전송하고,
 * 이 워커도 num_ctx를 여유 있게 잡는다.
 *
 * PDF는 이 워커에서 처리하지 않는다 — 클라이언트(PDF.js)가 페이지별로 이미지 렌더링 후
 * 페이지마다 이 엔드포인트를 호출하는 구조 (service/ocr/index.html 참고).
 *
 * POST /receipt — 영수증 키/밸류 구조화(service/ocr-pro/index.html 전용). 1단계는 /ocr과
 * 동일한 runOcr()을 그대로 재사용하고, 2단계로 그 텍스트만(이미지 없이) 다시 한 번 호출해
 * Ollama format(JSON Schema)로 구조화한다 — structureReceipt() 주석 참고.
 *
 * POST /detect — "정밀 교정(베타)" 모드용 텍스트 위치(바운딩 박스) 감지(service/ocr/index.html).
 * PC의 EasyOCR 감지 전용 로컬 서버(workers/ocr-detect-pc/detect_server.py, Ollama와는 별개
 * 프로세스)에 이미지를 보내 박스 좌표만 받아온다. 텍스트 인식은 이 라우트가 하지 않는다 —
 * 클라이언트가 박스를 클릭하면 그 영역만 잘라 /ocr로 다시 호출해 이미 검증된 올mOCR-2로
 * 재인식한다(EasyOCR 자체 인식 텍스트는 신뢰도가 낮아 위치 참고용으로만 사용, 2026-07-24
 * 실측 확인 — detect_server.py 상단 주석 참고). 지금은 로그인 사용자 전원에게 열려 있는
 * 테스트 단계 기능이고, 유료 등급 전용으로 제한할 계획이라 canUseDetectFeature()에 게이트를
 * 분리해 뒀다 — 나중에 실제 결제 등급 체크만 그 함수 안에 추가하면 된다.
 *
 * 시크릿(전부 `wrangler secret put`으로만 설정, 평문 기재 금지):
 *   CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET — biz-rag와 동일 Service Token 재사용 가능
 *   PC_AI_URL          — 예: https://pc-ai.worksfree.kr (Ollama, /ocr·/receipt용)
 *   PC_DETECT_URL      — 예: https://detect.worksfree.kr (EasyOCR 감지 서버, /detect용).
 *                        Access 앱은 PC_AI_URL과 별개로 만들었지만 Service Token은 동일한 것 재사용.
 */

const SUPABASE_URL = "https://rkycwfpkzorfpcxfvaqt.supabase.co";
const SUPABASE_ANON =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJreWN3ZnBrem9yZnBjeGZ2YXF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgzMDk4OTQsImV4cCI6MjA5Mzg4NTg5NH0.u1HC0KiArbdqFAPpkRWsfZmMYqfZ-euRTHeNtUr2NBs";

const ALLOWED_ORIGINS = new Set([
  "https://test.worksfree.kr",
  "https://staging.worksfree.kr",
  "https://www.worksfree.kr",
  "https://portal.worksfree.kr",
]);

const DAILY_LIMIT = 30; // 이미지 1장 = 1회 (PDF는 페이지당 1회 소모). 관리자(profiles.role)는 무제한 — isAdmin() 참고
const OCR_MODEL = "richardyoung/olmocr2:7b-q8";
// 프롬프트는 짧고 단순하게 유지한다 — 실측으로 "HTML/Markdown 표를 쓰지 마라" 같은
// 부정 지시를 추가하면 오히려 결과가 더 불안정해짐을 확인했다(정상 문서에서 CER
// 0.19 → 0.47로 악화, <th colspan="2"> 같은 깨진 태그까지 섞여 나옴). OCR 특화
// 모델은 일반 지시문 준수보다 짧고 직접적인 요청에 더 안정적으로 반응한다.
const OCR_PROMPT =
  "Extract all text from this image exactly as it appears, preserving line breaks and reading order. " +
  "Output only the extracted text, no commentary.";
const OCR_TIMEOUT_MS = 30000;
const MAX_IMAGE_B64_CHARS = 12_000_000; // 대략 원본 이미지 9MB 상당 상한

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.has(origin) ? origin : "https://test.worksfree.kr";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}
function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json", ...corsHeaders(origin) },
  });
}

async function verifyUser(accessToken) {
  const r = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON },
  });
  if (!r.ok) return null;
  const u = await r.json();
  return u && u.id ? u : null;
}

// 관리자는 일일 횟수 제한 없이 사용 — profiles.role은 클라이언트가 아니라 서버(여기)에서
// 직접 조회해 신뢰한다(클라이언트가 role을 보내는 방식은 위조 가능해 금지 패턴).
async function isAdmin(accessToken, userId) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/profiles?id=eq.${userId}&select=role`, {
    headers: { Authorization: `Bearer ${accessToken}`, apikey: SUPABASE_ANON },
  });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return rows?.[0]?.role === "admin";
}

async function checkAndBumpRateLimit(env, userId) {
  const today = new Date().toISOString().slice(0, 10);
  const key = `${today}:${userId}`;
  const cur = parseInt((await env.OCR_RATE_LIMIT.get(key)) || "0", 10);
  if (cur >= DAILY_LIMIT) return { ok: false };
  await env.OCR_RATE_LIMIT.put(key, String(cur + 1), { expirationTtl: 90000 });
  return { ok: true, remaining: DAILY_LIMIT - cur - 1 };
}

function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

// 두 모델 모두 "텍스트만 그대로 뽑아달라"는 요청에 가끔 서식 마크업을 섞어 낸다.
// - glm-ocr(구 기본 모델): 표·동그라미 숫자·굵은 글씨가 많은 문서에서 실제로 없는 LaTeX
//   문법(\textcircled{1}, \textbf{...}, $...$ 등)을 지어냄(해상도를 올려도 동일 — 실측으로
//   해상도가 원인이 아님을 확인).
// - olmOCR-2(현재 모델): 프롬프트로 "HTML/Markdown 표 금지"를 지시해도 빈 셀이 많은 표에서
//   가끔 <table><tr><td> 마크업을 섞어 냄(실측 확인). 표 자체 인식은 정확하므로 태그만 걷어내고
//   내용은 살린다.
// 두 경우 다 모델 출력은 그대로 두고 후처리로 마크업만 걷어내는 편이 안전하다(모델에게
// "이렇게 하지 마"를 프롬프트로 지시해도 100% 지켜지지 않는 것도 실측으로 확인됨).
function stripMarkupArtifacts(t) {
  let s = t;
  s = s.replace(/\\textcircled\{([^{}]*)\}/g, "($1)");
  for (let i = 0; i < 2; i++) {
    s = s.replace(/\\(?:textbf|textit|texttt|textsc|mathrm|mathbf|text)\s*\{([^{}]*)\}/g, "$1");
  }
  s = s.replace(/\\[a-zA-Z]+/g, ""); // 남은 영문 LaTeX 명령어
  s = s.replace(/\\+/g, ""); // 명령어로 인식 안 된 잔여 백슬래시(한글 등에 바로 붙은 경우)
  s = s.replace(/\$/g, "");
  s = s.replace(/[{}]/g, "");
  s = s.replace(/<\/?(?:table|thead|tbody)>/gi, "");
  s = s.replace(/<\/tr>/gi, "\n");
  s = s.replace(/<tr>/gi, "");
  s = s.replace(/<\/?(?:td|th)>/gi, "\t");
  s = s.replace(/<br\s*\/?>/gi, "\n");
  s = s.replace(/[ \t]{2,}/g, " ");
  s = s.replace(/\n{3,}/g, "\n\n");
  return s.trim();
}

// 모델이 헷갈리면 텍스트를 무한 반복하는 증상의 안전장치.
// repeat_penalty를 걸어도 완전히 똑같은 문자열이 아니라 한자·영단어가 살짝 섞여 변주되며
// 반복되는 경우가 실측으로 확인됨(예: "매일샴페인 / 컵/CSO)" → "...龙 instyle" → "...科使제" 식으로
// 매번 조금씩 달라짐) — 그래서 정확 문자열 반복 탐지로는 못 잡는다. 대신 "줄 시작 부분이
// 최근 몇 줄 안에서 이미 나왔으면 그 줄부터 잘라낸다"는 느슨한 기준으로 판단한다.
function truncateRunawayRepetition(text) {
  // PREFIX_LEN을 짧게 잡으면 "(1)", "①" 같은 번호 매김이 서로 다른 섹션에서 우연히
  // 겹치는 것까지 반복으로 오판한다(실측으로 확인 — "1. 제원" 절이 번호를 ①부터 다시
  // 시작하는 문서에서 오탐 발생). 접두어를 충분히 길게 잡고, 2번이 아니라 "3번째 등장"에서만
  // 자르도록 해서 진짜 폭주(수십~수백 회 반복)만 잡고 우연의 일치는 통과시킨다.
  const lines = text.split("\n");
  const WINDOW = 6;
  const PREFIX_LEN = 16;
  const REPEAT_THRESHOLD = 3;
  const counts = new Map();
  const order = [];
  for (let i = 0; i < lines.length; i++) {
    const prefix = lines[i].trim().slice(0, PREFIX_LEN);
    if (prefix.length >= PREFIX_LEN) {
      const next = (counts.get(prefix) || 0) + 1;
      counts.set(prefix, next);
      if (next >= REPEAT_THRESHOLD) {
        return lines.slice(0, i).join("\n").trim();
      }
      order.push(prefix);
      if (order.length > WINDOW) {
        const dropped = order.shift();
        counts.set(dropped, (counts.get(dropped) || 1) - 1);
      }
    }
  }
  // 줄바꿈 없이 한 줄 안에서 반복되는 경우(완전 동일 문자열 폭주)도 방어.
  // 반복 단위 1글자·4회 기준은 "A04-1-00005-0004-1207" 같은 정상 문서번호 속 "0000"까지
  // 오탐하는 게 실측으로 확인되어, 단위 최소 3글자·6회 이상으로 훨씬 보수적으로 잡는다
  // (줄 단위 반복은 위 로직이 이미 담당하므로 이건 어디까지나 마지막 보루).
  const exact = text.match(/(.{3,20}?)\1{5,}/su);
  if (exact && typeof exact.index === "number") {
    return text.slice(0, exact.index).trim();
  }
  return text;
}

async function callOllamaGenerate(env, imageBase64, options) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({
        model: OCR_MODEL,
        prompt: OCR_PROMPT,
        images: [imageBase64],
        stream: false,
        options,
      }),
    },
    OCR_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`ocr failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`ocr failed: ${r.status}`);
  }
  const data = await r.json();
  return (data.response || "").trim();
}

// num_ctx: 기본값 4096은 클라이언트가 축소 전송해도(1800px) 여유가 빠듯해 실측으로 문제가
// 재현됨(비전 토큰이 예산을 넘기면 응답이 몇 글자만에 끊김) — 6144로 여유 확보.
const BASE_OPTIONS = { temperature: 0, num_predict: 3000, num_ctx: 6144 };
// repeat_penalty는 상시로 걸지 않는다 — 실측으로 확인: 정상 문서(표에 "종합검사"·동그라미
// 번호 등 정당한 반복이 있는 문서)에서 repeat_penalty를 걸면 그 정상 반복까지 억제되어
// 오히려 정확도가 크게 나빠짐(문자 오류율 0.19 → 1.08까지 악화된 사례 확인). 그래서 1차
// 호출은 penalty 없이 시도하고, 후처리로 실제 반복 폭주가 감지된 경우에만 penalty를 걸어
// 같은 이미지를 한 번 더 호출한다(흔치 않은 실패 케이스에서만 추가 지연 발생).
const REPEAT_RETRY_OPTIONS = { ...BASE_OPTIONS, repeat_penalty: 1.3, repeat_last_n: 256 };

// 반복 폭주가 감지됐다는 것은 원본 이미지 자체가 모델이 다루기 어려운 상태였다는
// 신뢰할 만한 신호다(실측: 심하게 흐릿한 사진·구겨진 영수증에서 반복적으로 재현됨).
// 기하 왜곡 보정(UVDoc 등 최신 document dewarping 모델)을 별도 PC 서비스로 도입하는
// 방안도 검토했으나, 합성 왜곡·그림자로 통제 실험을 해본 결과 olmOCR-2는 이미 이런
// 왜곡에 상당히 강건해서 사전 보정이 오히려 정확도를 깎는 경우도 있었다(실측: CER
// 0.246→0.281 악화) — 그래서 별도 전처리 인프라 대신, 폭주가 감지되면 결과와 함께
// "낮은 신뢰도" 신호만 반환해 클라이언트가 사용자에게 재촬영을 안내하도록 한다.
async function runOcr(env, imageBase64) {
  const first = await callOllamaGenerate(env, imageBase64, BASE_OPTIONS);
  // 순서 중요: 마크업 제거를 먼저 해야 한다 — 서로 다른 줄이 마크업 때문에 앞부분이 우연히
  // 같아지는 경우, 반복 감지가 먼저 돌면 정상 내용을 반복으로 오판해 잘라버릴 수 있다.
  const firstCleaned = stripMarkupArtifacts(first);
  const firstFinal = truncateRunawayRepetition(firstCleaned);
  if (firstFinal.length === firstCleaned.length) {
    return { text: firstFinal, lowConfidence: false }; // 반복 폭주 없음 — 재시도 없이 그대로 반환
  }
  // 반복이 감지된 경우에만 repeat_penalty를 걸어 재시도 — 원본이 폭주로 잘려나간 결과보다
  // 길고(더 많은 내용을 건졌고) 반복도 없다면 재시도 결과를 채택한다. 재시도로 살아나든
  // 못 살아나든, 1차 시도에서 폭주가 있었다는 사실 자체가 "낮은 신뢰도" 신호이므로 유지한다.
  try {
    const retry = await callOllamaGenerate(env, imageBase64, REPEAT_RETRY_OPTIONS);
    const retryCleaned = stripMarkupArtifacts(retry);
    const retryFinal = truncateRunawayRepetition(retryCleaned);
    if (retryFinal.length > firstFinal.length) return { text: retryFinal, lowConfidence: true };
  } catch (e) {
    console.error(`ocr retry failed: ${e}`);
  }
  return { text: firstFinal, lowConfidence: true };
}

// ── 영수증 키/밸류 구조화 (2단계: 이미지 OCR은 그대로 두고, 이미 검증된 텍스트를
// 텍스트 전용으로 다시 한 번 호출해 JSON으로 구조화한다) ──
//
// 왜 이미지+JSON스키마 한 번에가 아니라 2단계인가: 실측 검증된 자유 텍스트 추출
// 프롬프트(OCR_PROMPT)를 건드리지 않고 그대로 재사용할 수 있고, "이미지+문법제약
// 디코딩" 조합은 이 커뮤니티 GGUF 패키지에서 검증된 적이 없어 리스크가 있다(이
// 프로젝트에서 여러 번 확인된 패턴: 검증 안 된 조합은 사전 실측 없이 신뢰하지 않는다).
// 이미 정확도가 검증된 텍스트에서 구조만 뽑아내는 게 더 안전하다.
const RECEIPT_SCHEMA = {
  type: "object",
  properties: {
    store_name: { type: "string" },
    business_reg_no: { type: "string" },
    date: { type: "string" },
    phone: { type: "string" },
    address: { type: "string" },
    items: {
      type: "array",
      items: {
        type: "object",
        properties: {
          name: { type: "string" },
          qty: { type: "number" },
          price: { type: "number" },
        },
      },
    },
    subtotal: { type: "number" },
    tax: { type: "number" },
    total: { type: "number" },
  },
  required: ["store_name", "items", "total"],
};

const RECEIPT_STRUCTURE_PROMPT_HEAD =
  "다음은 영수증에서 추출한 텍스트입니다. 아래 항목을 이 텍스트에서만 찾아 JSON으로 정리하세요. " +
  "텍스트에 없는 값은 빈 문자열이나 0으로 두고 지어내지 마세요. " +
  "항목마다 텍스트 전체를 다시 확인하세요 — 값이 실제로 있는데 비워두는 실수를 하지 마세요.\n" +
  "- store_name: 상호명\n" +
  "- business_reg_no: 사업자등록번호(사업자번호로만 표기된 경우도 동일한 값)\n" +
  "- date: 거래일시\n" +
  "- phone: 전화번호\n" +
  "- address: 사업장 주소(있으면)\n" +
  "- items: 품목 배열, 각 항목은 name(품명)/qty(수량)/price(금액). 카드 결제 전표(매출표)처럼 " +
  "실제 구매 품목 목록이 없는 영수증이면 빈 배열로 두세요 — [일시불]/[할부] 같은 결제 방식 " +
  "표시는 품목이 아니니 items에 넣지 마세요.\n" +
  "- subtotal: 공급가액\n- tax: 부가세\n- total: 합계금액\n\n[영수증 텍스트]\n";

// JSON Schema를 Ollama의 format 파라미터로 넘기면 문법(GBNF) 제약으로 구조는 보장되지만,
// 스키마 자체가 프롬프트에 자동 주입되지는 않는다 — 그래서 위 프롬프트에 필드 설명을
// 직접 적어준다(실측 근거: Ollama 공식 문서 "The model has no visibility into the schema").
async function structureReceipt(env, rawText, options) {
  const r = await fetchWithTimeout(
    `${env.PC_AI_URL}/api/generate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({
        model: OCR_MODEL,
        prompt: RECEIPT_STRUCTURE_PROMPT_HEAD + rawText.slice(0, 4000),
        format: RECEIPT_SCHEMA,
        stream: false,
        options,
      }),
    },
    OCR_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`receipt structure failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`receipt structure failed: ${r.status}`);
  }
  const data = await r.json();
  return JSON.parse(data.response || "{}");
}

// 사업자등록번호·합계금액처럼 형식이 고정적인 고신뢰 필드는 모델 출력만 믿지 않고
// 이미 정확도가 검증된 원본 텍스트에서 정규식으로도 뽑아 대조용으로 함께 반환한다
// (연구 결과 권장 패턴 — 모델이 숫자 서식을 바꾸거나 누락하는 경우의 안전망).
//
// 2026-07-24 실측: 텍스트 출력에서는 "주소:", "TEL:", "거래일시:", "사업자번호:"처럼
// 라벨이 명확히 붙어 다 읽히는데, 엑셀(구조화) 출력에서는 상호명·합계 같은 눈에 띄는
// 필드만 채워지고 나머지는 비어서 나오는 문제 발견 — structureReceipt()가 JSON
// 파싱 자체는 성공(에러 없음)하지만 필드별로 골고루 채우지 못해서, 지금까지는 이걸
// 잡아내는 재시도 로직이 없었다. 라벨이 뚜렷한 필드는 LLM 구조화 결과를 기다리지 않고
// 정규식으로 직접 뽑아, LLM이 비워둔 자리를 메우는 용도로 쓴다(runReceiptExtraction 참고).
function regexFallback(rawText) {
  const bizNoLabeled = rawText.match(/사업자(?:등록)?번호\s*[:：]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{5})/);
  const bizNoLoose = rawText.match(/\d{3}[-\s]?\d{2}[-\s]?\d{5}/);
  const totalMatch = rawText.match(/(?:합\s*계|총\s*액|총\s*합\s*계)[^\d₩]{0,10}([\d,]{3,})/);
  const phoneMatch = rawText.match(/(?:TEL|전화(?:번호)?)\s*[:：]?\s*([\d\-]{9,13})/i);
  const dateMatch = rawText.match(/거래일시\s*[:：]?\s*([\d]{2,4}[./\-][\d]{1,2}[./\-][\d]{1,2}[^\n]{0,15})/);
  const addrMatch = rawText.match(/주소\s*[:：]?\s*([^\n]+)/);
  return {
    business_reg_no: (bizNoLabeled?.[1] || bizNoLoose?.[0] || "").replace(/\s/g, "") || null,
    total: totalMatch ? parseInt(totalMatch[1].replace(/,/g, ""), 10) : null,
    phone: phoneMatch ? phoneMatch[1].trim() : null,
    date: dateMatch ? dateMatch[1].trim() : null,
    address: addrMatch ? addrMatch[1].trim() : null,
  };
}

// ── 주소 검증/보정 (행안부 도로명주소 검색API) ──
// 영수증 주소는 OCR이 시각적으로 비슷한 글자를 혼동하기 쉬운 필드다(실측: "효원로"→
// "요원로", "팔달구"→"발달구" 등). 공식 주소 DB와 대조해 없는 주소면 근접한 실제
// 주소로 보정한다. 사용자가 제안한 방식 그대로 구현: 전체 주소로 검색 → 결과 없으면
// 뒤(가장 세부적인 토큰, 대개 도로명·번지)부터 한 단어씩 줄여가며 재검색 → 처음
// 결과가 나온 단계의 주소를 채택한다. 토큰을 줄여야 했다면(=상위 행정구역만으로
// 찾음) confidence를 "low"로 표시해 사용자가 한 번 더 보게 한다 — 잘못된 도시로
// 확신 없이 자동 치환하는 걸 피하기 위함(신뢰도 표시 없이 조용히 틀린 주소로
// 바꾸는 게 OCR 오류보다 더 나쁠 수 있어서).
// JUSO_API_KEY가 없으면 이 기능 전체가 조용히 no-op(원문 그대로 반환)한다 — 발급
// 전에도 영수증 처리 자체는 그대로 동작해야 하므로.
const JUSO_ENDPOINT = "https://business.juso.go.kr/addrlink/addrLinkApi.do";

async function searchJuso(env, keyword) {
  const url =
    `${JUSO_ENDPOINT}?confmKey=${env.JUSO_API_KEY}&currentPage=1&countPerPage=5` +
    `&keyword=${encodeURIComponent(keyword)}&resultType=json`;
  const r = await fetchWithTimeout(url, {}, 5000);
  const data = await r.json();
  // 문서/응답 버전에 따라 최상위 경로가 다르게 보고되는 사례가 있어 둘 다 대응
  return data?.results?.juso || data?.data?.result || [];
}

async function correctAddress(env, ocrAddress) {
  if (!env.JUSO_API_KEY || !ocrAddress || !ocrAddress.trim()) {
    return { address: ocrAddress || "", verified: false, corrected: false };
  }
  const norm = (s) => (s || "").replace(/\s+/g, "");
  const tokens = ocrAddress.trim().split(/\s+/);
  for (let dropFromEnd = 0; dropFromEnd < tokens.length; dropFromEnd++) {
    const query = tokens.slice(0, tokens.length - dropFromEnd).join(" ");
    if (!query) break;
    try {
      const results = await searchJuso(env, query);
      if (results && results.length > 0) {
        const best = results[0];
        const correctedAddr = best.roadAddr || best.jibunAddr || ocrAddress;
        return {
          address: correctedAddr,
          original: ocrAddress,
          corrected: norm(correctedAddr) !== norm(ocrAddress),
          verified: true,
          confidence: dropFromEnd === 0 ? "high" : "low",
        };
      }
    } catch (e) {
      console.error(`juso search failed (query="${query}"): ${e}`);
      // 이 단계 실패는 다음(더 짧은) 단계로 계속 폴백
    }
  }
  return { address: ocrAddress, original: ocrAddress, verified: false, corrected: false };
}

async function runReceiptExtraction(env, imageBase64) {
  const ocrResult = await runOcr(env, imageBase64); // 1단계: 기존 검증된 OCR 그대로 재사용
  let structured;
  try {
    structured = await structureReceipt(env, ocrResult.text, { temperature: 0, num_predict: 1500 });
  } catch (e) {
    console.error(`structure attempt 1 failed: ${e}`);
    // JSON 파싱 실패·반복 폭주 등으로 실패하면 penalty를 걸어 한 번 더 시도
    // (일반 OCR의 감지-후-재시도 패턴과 동일한 사고방식 — 항상 걸지 않고 실패 시에만).
    try {
      structured = await structureReceipt(env, ocrResult.text, {
        temperature: 0,
        num_predict: 1500,
        repeat_penalty: 1.3,
        repeat_last_n: 256,
      });
    } catch (e2) {
      console.error(`structure retry failed: ${e2}`);
      structured = null;
    }
  }

  const regexCheck = regexFallback(ocrResult.text);

  // LLM 구조화가 JSON 파싱은 성공했지만 필드를 골고루 못 채우는 경우(실측 확인,
  // 2026-07-24) — 라벨이 뚜렷해 정규식으로도 뽑히는 필드는 LLM이 비워둔 자리를
  // 정규식 결과로 메운다. total은 기존처럼 대조용(regex_check)으로만 두고 자동
  // 교체하지 않음 — 금액 필드는 잘못 채우면 신뢰도에 영향이 커서 보수적으로 접근한다.
  //
  // business_reg_no는 2026-07-24 실측(엑셀 출력에서 빈칸)으로 여기 포함시킴 — 영수증에
  // "사업자등록번호" 대신 "사업자번호"로만 표기된 경우 LLM이 프롬프트 설명(사업자등록번호)
  // 문구에 매여 못 찾는 사례 확인. regexFallback의 라벨 정규식은 "(등록)?"을 옵셔널로 두어
  // 두 표기를 모두 잡고, 값 형식도 3-2-5 자리 숫자로 고정돼 있어 total 같은 자유 숫자 필드
  // 보다 오탐 위험이 낮다 — 그래서 total과 달리 자동 백필 대상에 포함한다.
  if (structured) {
    if (!structured.phone && regexCheck.phone) structured.phone = regexCheck.phone;
    if (!structured.date && regexCheck.date) structured.date = regexCheck.date;
    if (!structured.address && regexCheck.address) structured.address = regexCheck.address;
    if (!structured.business_reg_no && regexCheck.business_reg_no) structured.business_reg_no = regexCheck.business_reg_no;
  }

  let addressCheck = null;
  if (structured?.address) {
    try {
      addressCheck = await correctAddress(env, structured.address);
      if (addressCheck.corrected) structured.address = addressCheck.address;
    } catch (e) {
      console.error(`address correction failed: ${e}`);
    }
  }
  return {
    rawText: ocrResult.text,
    lowConfidence: ocrResult.lowConfidence || !structured,
    structured,
    regexCheck,
    addressCheck,
  };
}

// 지금은 로그인만 되어 있으면 전원 사용 가능(테스트 단계) — 나중에 유료 등급 전용으로
// 제한할 계획이라 게이트를 이 함수 하나로 분리해 뒀다. 실제 결제 등급 체크(예:
// profiles.plan === 'pro' 같은 컬럼 조회)를 추가할 때 이 함수 안만 고치면 된다.
async function canUseDetectFeature(env, accessToken, userId) {
  return true;
}

// EasyOCR 감지 전용 로컬 서버 호출 — Ollama(PC_AI_URL)와는 별개 프로세스/포트.
// 텍스트는 신뢰하지 않고 박스 좌표만 쓴다(detect_server.py 주석 참고).
async function runDetect(env, imageBase64) {
  const r = await fetchWithTimeout(
    `${env.PC_DETECT_URL}/detect`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "CF-Access-Client-Id": env.CF_ACCESS_CLIENT_ID,
        "CF-Access-Client-Secret": env.CF_ACCESS_CLIENT_SECRET,
      },
      body: JSON.stringify({ image_base64: imageBase64 }),
    },
    OCR_TIMEOUT_MS
  );
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    console.error(`detect failed: status=${r.status} body=${detail.slice(0, 500)}`);
    throw new Error(`detect failed: ${r.status}`);
  }
  const data = await r.json();
  return data.boxes || [];
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }
    const KNOWN_PATHS = new Set(["/ocr", "/receipt", "/detect"]);
    if (request.method !== "POST" || !KNOWN_PATHS.has(url.pathname)) {
      return json({ error: "not_found" }, 404, origin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400, origin);
    }

    const { access_token, image_base64 } = body || {};
    if (!access_token || typeof access_token !== "string") {
      return json({ error: "unauthenticated" }, 401, origin);
    }
    if (!image_base64 || typeof image_base64 !== "string") {
      return json({ error: "no_image" }, 400, origin);
    }
    if (image_base64.length > MAX_IMAGE_B64_CHARS) {
      return json({ error: "image_too_large" }, 400, origin);
    }

    const user = await verifyUser(access_token);
    if (!user) return json({ error: "invalid_session" }, 401, origin);

    // /detect는 별도 로컬 서버(PC_DETECT_URL)를 쓰고 GPU/Ollama 비용이 없어 일일 횟수
    // 제한 대상이 아니다 — 대신 canUseDetectFeature()로 별도 게이트(지금은 로그인만 요구).
    if (url.pathname === "/detect") {
      const allowed = await canUseDetectFeature(env, access_token, user.id);
      if (!allowed) return json({ error: "plan_required" }, 403, origin);
      if (!env.PC_DETECT_URL || !env.CF_ACCESS_CLIENT_ID || !env.CF_ACCESS_CLIENT_SECRET) {
        return json({ error: "server_misconfigured" }, 500, origin);
      }
      try {
        const boxes = await runDetect(env, image_base64);
        return json({ ok: true, boxes }, 200, origin);
      } catch (e) {
        return json({ error: "pc_offline", detail: String(e) }, 503, origin);
      }
    }

    const admin = await isAdmin(access_token, user.id);
    let rate = { ok: true, remaining: null, unlimited: true };
    if (!admin) {
      rate = await checkAndBumpRateLimit(env, user.id);
      if (!rate.ok) return json({ error: "rate_limited", limit: DAILY_LIMIT }, 429, origin);
    }

    if (!env.PC_AI_URL || !env.CF_ACCESS_CLIENT_ID || !env.CF_ACCESS_CLIENT_SECRET) {
      return json({ error: "server_misconfigured" }, 500, origin);
    }

    if (url.pathname === "/receipt") {
      let result;
      try {
        result = await runReceiptExtraction(env, image_base64);
      } catch (e) {
        return json({ error: "pc_offline", detail: String(e) }, 503, origin);
      }
      return json(
        {
          ok: true,
          text: result.rawText,
          structured: result.structured,
          regex_check: result.regexCheck,
          address_check: result.addressCheck,
          low_confidence: result.lowConfidence,
          remaining_today: rate.remaining,
          unlimited: !!rate.unlimited,
        },
        200,
        origin
      );
    }

    let result;
    try {
      result = await runOcr(env, image_base64);
    } catch (e) {
      return json({ error: "pc_offline", detail: String(e) }, 503, origin);
    }

    return json(
      {
        ok: true,
        text: result.text,
        low_confidence: result.lowConfidence,
        remaining_today: rate.remaining,
        unlimited: !!rate.unlimited,
      },
      200,
      origin
    );
  },
};
