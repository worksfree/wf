"""
로컬 PC에서 DWG(AutoCAD 도면) 표제란·BOM을 추출하는 소형 HTTP 서버.

핵심 로직은 dwg_extract.py에 있고(실측 검증 완료, 그 파일 상단 주석 참고),
이 파일은 그 로직을 HTTP로 감싸기만 한다 — ocr-detect-pc/detect_server.py와
동일한 패턴(인증 없음, Cloudflare Access가 터널 앞단에서 막아줌).

DWG 자체는 이미지가 아니라 바이너리 CAD 데이터라 브라우저에서 처리할 수
없어서, 이 PC 로컬 서버가 GNU LibreDWG(bin/dwgread.exe, GPL 오픈소스)로
직접 파싱한다 — Ollama/GPU는 전혀 쓰지 않는다(OCR과 무관한 별도 파이프라인).

실행:
    python -m venv venv
    venv\\Scripts\\pip install -r requirements.txt   (표준 라이브러리만 써서 사실 불필요할 수 있음)
    venv\\Scripts\\python dwg_extract_server.py

기본 포트 8767 (8765=pc-ai/Ollama, 8766=detect/EasyOCR와 겹치지 않게 지정).
"""
import base64
import json
import sys
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dwg_extract import extract_dwg
from dwg_thumbnail import build_thumbnail_svg

PORT = 8767
BASE_DIR = Path(__file__).resolve().parent
DWGREAD_EXE = str(BASE_DIR / "bin" / "dwgread.exe")
MAX_DWG_B64_CHARS = 30_000_000  # 대략 원본 DWG 22MB 상당 상한


class ExtractHandler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"ok": True, "engine": "libredwg-dwgread"})
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        if self.path not in ("/extract", "/thumbnail"):
            self._send_json({"error": "not_found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_DWG_B64_CHARS:
                self._send_json({"error": "invalid_length"}, 400)
                return
            raw = self.rfile.read(length)
            body = json.loads(raw)
            dwg_b64 = body.get("dwg_base64", "")
            if not dwg_b64:
                self._send_json({"error": "no_file"}, 400)
                return
            dwg_bytes = base64.b64decode(dwg_b64)
        except Exception as e:
            self._send_json({"error": "bad_request", "detail": str(e)}, 400)
            return

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".dwg", delete=False) as tmp:
                tmp.write(dwg_bytes)
                tmp_path = tmp.name
            if self.path == "/extract":
                result = extract_dwg(tmp_path, DWGREAD_EXE)
                self._send_json({"ok": True, **result})
            else:  # /thumbnail — O&M에서 샘플 DWG를 교체할 때 와이어프레임 SVG 재생성용
                svg = build_thumbnail_svg(tmp_path, DWGREAD_EXE)
                self._send_json({"ok": True, "svg": svg})
        except Exception as e:
            print(f"[dwg_extract_server] {self.path} 실패: {e}", flush=True)
            self._send_json({"error": "extract_failed", "detail": str(e)}, 500)
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"[dwg_extract_server] http://localhost:{PORT} 에서 대기 중 (dwgread={DWGREAD_EXE})", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ExtractHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[dwg_extract_server] 종료", flush=True)
