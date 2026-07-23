"""
service/ocr 프로덕션 OCR 파이프라인을 그대로 재현하는 공용 평가 라이브러리.
scratchpad/ocr_lab/sweep_contrast_sharnp.py(2026-07-23 로컬 6종 표본 스윕)와
ingest_aihub_samples.py(업종별 AI-Hub 표본 스윕)가 공유한다 — 두 스크립트가
서로 다른 데이터셋에 대해 같은 전처리·채점 기준을 쓰도록 하기 위해 분리.

프로덕션과 동일하게 맞춘 지점(변경 시 이 파일과 workers/ocr-service/index.js,
service/ocr/index.html을 함께 갱신할 것):
  - 모델/프롬프트/옵션: workers/ocr-service/index.js OCR_MODEL·OCR_PROMPT·BASE_OPTIONS
  - 다운스케일 상한: service/ocr/index.html MAX_OCR_DIM
  - 콘트라스트 공식: CSS canvas filter contrast()와 동일한 (v-128)*factor+128
  - 샤프니스: service/ocr/index.html sharpenCanvas()의 3x3 커널 블렌드와 동일
"""
import base64, json, re, time
import urllib.request
import numpy as np
import cv2

OLLAMA_URL = "http://localhost:11434"
OCR_MODEL = "richardyoung/olmocr2:7b-q8"
OCR_PROMPT = (
    "Extract all text from this image exactly as it appears, preserving line breaks and reading order. "
    "Output only the extracted text, no commentary."
)
BASE_OPTIONS = {"temperature": 0, "num_predict": 3000, "num_ctx": 6144}
MAX_OCR_DIM = 1800

_SHARPEN_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)


def cv_read(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        from PIL import Image
        pil = Image.open(path).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return img


def downscale_max_dim(img, max_dim=MAX_OCR_DIM):
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_dim:
        return img
    scale = max_dim / m
    return cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


def apply_contrast_pct(img, pct):
    factor = 1 + pct / 100.0
    f = img.astype(np.float32)
    f = (f - 128.0) * factor + 128.0
    return np.clip(f, 0, 255).astype(np.uint8)


def apply_sharpen_pct(img, pct):
    amount = pct / 100.0
    if amount <= 0:
        return img
    conv = cv2.filter2D(img.astype(np.float32), -1, _SHARPEN_KERNEL, borderType=cv2.BORDER_REPLICATE)
    blended = img.astype(np.float32) * (1 - amount) + conv * amount
    return np.clip(blended, 0, 255).astype(np.uint8)


def encode_png_b64(img):
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG encode failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def strip_markup_artifacts(t):
    s = t
    s = re.sub(r"\\textcircled\{([^{}]*)\}", r"(\1)", s)
    for _ in range(2):
        s = re.sub(r"\\(?:textbf|textit|texttt|textsc|mathrm|mathbf|text)\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


_CIRCLED = {}
for _i in range(20):
    _CIRCLED[chr(0x2460 + _i)] = str(_i + 1)


def normalize(text):
    if not text:
        return ""
    s = text
    for k, v in _CIRCLED.items():
        s = s.replace(k, v)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    return s.strip()


def levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def cer(ref, hyp):
    rn, hn = normalize(ref), normalize(hyp)
    if not rn:
        return None
    return levenshtein(rn, hn) / len(rn)


def ollama_generate(image_b64, timeout=60):
    body = {
        "model": OCR_MODEL, "prompt": OCR_PROMPT, "images": [image_b64],
        "stream": False, "options": BASE_OPTIONS,
    }
    req = urllib.request.Request(
        OLLAMA_URL + "/api/generate", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", ""), time.time() - t0


def run_ocr_with_settings(img, contrast_pct, sharpen_pct, timeout=60):
    """전처리(다운스케일+콘트라스트+샤프니스) -> OCR 호출 -> 후처리까지 한 번에.
    반환: (cleaned_text, elapsed_sec)"""
    proc = downscale_max_dim(img)
    proc = apply_contrast_pct(proc, contrast_pct)
    proc = apply_sharpen_pct(proc, sharpen_pct)
    b64 = encode_png_b64(proc)
    resp, elapsed = ollama_generate(b64, timeout=timeout)
    return strip_markup_artifacts(resp.strip()), elapsed
