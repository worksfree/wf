"""
로컬 PC에서 EasyOCR로 텍스트 "위치"만 감지하는 소형 HTTP 서버.

이 서버가 하는 일은 딱 하나 — 어디에 글자가 있는지(바운딩 박스) 찾는 것뿐이다.
실제 텍스트 인식은 하지 않는다(EasyOCR 자체 인식 텍스트는 신뢰도가 낮음을
2026-07-24 실측 확인 — hint_text/hint_confidence로 참고용만 같이 반환하고,
실제 재인식은 워커가 이 박스로 원본 이미지를 크롭해 이미 검증된 올mOCR-2
(/ocr)로 다시 호출하는 구조). PaddleOCR은 이 PC(RTX 5090, Windows)에서
PaddlePaddle 실행기 버그로 완전히 막혀 있어(기본 텍스트 탐지조차 크래시,
2026-07-24 확인) EasyOCR을 씀. Tesseract.js(브라우저 내장형)는 한국어 박스
자체가 글자 단위로 깨져 나와 제외.

실행:
    python -m venv venv
    venv\\Scripts\\pip install -r requirements.txt
    venv\\Scripts\\python detect_server.py

기본 포트 8766 — Cloudflare Tunnel의 detect.worksfree.kr → localhost:8766
Public Hostname 설정과 Access(Service Token) 앱이 이미 구성되어 있어야
외부(워커)에서 도달 가능하다(2026-07-24 설정 완료).

인증은 이 서버 자체에는 없다 — Ollama(port 11434)와 동일한 패턴으로,
Cloudflare Access가 터널 앞단에서 막아주므로 로컬 서버는 신뢰된 요청만
받는다고 가정한다.
"""
import base64
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Windows에서 stdout이 콘솔 코드페이지(cp949)로 인코딩을 시도해 죽는 문제 방지
# (이 세션에서 여러 번 재발한 버그 — 원인 동일, 매번 재발 방지 처리 필요).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import easyocr
import numpy as np
from PIL import Image

PORT = 8766
MAX_IMAGE_B64_CHARS = 12_000_000  # 워커(ocr-service)와 동일한 상한

print("[detect_server] EasyOCR 리더 초기화 중(ko+en, CPU)...", flush=True)
reader = easyocr.Reader(["ko", "en"], gpu=False)
print(f"[detect_server] 준비 완료 — http://localhost:{PORT} 에서 대기 중", flush=True)


class DetectHandler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"ok": True, "model": "easyocr-ko-en"})
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        if self.path != "/detect":
            self._send_json({"error": "not_found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_IMAGE_B64_CHARS:
                self._send_json({"error": "invalid_length"}, 400)
                return
            raw = self.rfile.read(length)
            body = json.loads(raw)
            image_b64 = body.get("image_base64", "")
            if not image_b64:
                self._send_json({"error": "no_image"}, 400)
                return
            img_bytes = base64.b64decode(image_b64)
            img = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        except Exception as e:
            self._send_json({"error": "bad_request", "detail": str(e)}, 400)
            return

        try:
            results = reader.readtext(img)
        except Exception as e:
            print(f"[detect_server] 감지 실패: {e}", flush=True)
            self._send_json({"error": "detect_failed", "detail": str(e)}, 500)
            return

        boxes = []
        for box, text, conf in results:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            boxes.append({
                "x0": float(min(xs)), "y0": float(min(ys)),
                "x1": float(max(xs)), "y1": float(max(ys)),
                "hint_text": text, "hint_confidence": float(conf),
            })
        self._send_json({"ok": True, "boxes": boxes})

    def log_message(self, format, *args):
        pass  # 요청마다 콘솔 스팸 방지 — 필요 시 여기서 파일 로깅으로 교체


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DetectHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[detect_server] 종료", flush=True)
