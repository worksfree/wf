"""
local_server.py — 잡코리아 자동화 로컬 제어 서버

실행: python local_server.py
포트: 8765

WorksFree Hub의 잡코리아 관리 페이지에서 이 서버로 명령을 전송합니다.
Hub (브라우저) → localhost:8765 → jobkorea_auto.py 실행

의존성 (pip install):
  flask flask-cors
"""

import os
import sys
import json
import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app    = Flask(__name__)
CORS(app, origins=['*'])  # Hub 도메인 허용

BASE_DIR      = Path(__file__).parent
LOG_FILE      = BASE_DIR / 'jobkorea_run.log'
PID_FILE      = BASE_DIR / 'jobkorea.pid'
STATE_FILE    = BASE_DIR / 'jobkorea_state.json'
HISTORY_FILE  = BASE_DIR / 'recruit_history.json'

_proc: subprocess.Popen | None = None
_lock = threading.Lock()


# ── 상태 관리 ─────────────────────────────────────────────────────────
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {'status': 'idle', 'started_at': None, 'config': {}, 'log_lines': 0}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

def is_running() -> bool:
    global _proc
    if _proc and _proc.poll() is None:
        return True
    _proc = None
    return False


# ── API 엔드포인트 ───────────────────────────────────────────────────
@app.route('/status', methods=['GET'])
def status():
    state = load_state()
    running = is_running()
    return jsonify({
        'running': running,
        'status':  'running' if running else state.get('status', 'idle'),
        'started_at': state.get('started_at'),
        'config': state.get('config', {}),
        'server': 'online',
    })

@app.route('/run', methods=['POST'])
def run():
    global _proc
    with _lock:
        if is_running():
            return jsonify({'ok': False, 'error': '이미 실행 중입니다'}), 400

        data       = request.get_json(silent=True) or {}
        limit      = int(data.get('limit', 0))
        dry_run    = bool(data.get('dry_run', False))
        keywords   = data.get('keywords', '')

        cmd = [sys.executable, str(BASE_DIR / 'jobkorea_auto.py')]
        if dry_run:
            cmd.append('--dry-run')
        if limit:
            cmd += ['--limit', str(limit)]

        env = os.environ.copy()
        if keywords:
            env['SEARCH_KEYWORDS'] = keywords

        LOG_FILE.write_text(
            f'[{datetime.now():%Y-%m-%d %H:%M:%S}] 실행 시작\n'
            f'명령: {" ".join(cmd)}\n'
            f'키워드: {keywords or "기본값"}\n'
            f'{"[DRY-RUN] 실제 발송 없음" if dry_run else f"최대 {limit}건" if limit else "전체"}\n'
            '─' * 40 + '\n',
            encoding='utf-8'
        )

        _proc = subprocess.Popen(
            cmd, env=env,
            stdout=open(LOG_FILE, 'a', encoding='utf-8'),
            stderr=subprocess.STDOUT,
        )

        state = {
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'config': {'limit': limit, 'dry_run': dry_run, 'keywords': keywords},
        }
        save_state(state)

    return jsonify({'ok': True, 'pid': _proc.pid})

@app.route('/stop', methods=['POST'])
def stop():
    global _proc
    with _lock:
        if not is_running():
            return jsonify({'ok': False, 'error': '실행 중이 아닙니다'})
        try:
            _proc.terminate()
            _proc.wait(timeout=5)
        except Exception:
            try:
                _proc.kill()
            except Exception:
                pass
        _proc = None
        state = load_state()
        state['status'] = 'stopped'
        save_state(state)
    return jsonify({'ok': True})

@app.route('/log', methods=['GET'])
def log():
    try:
        lines = LOG_FILE.read_text(encoding='utf-8', errors='replace').splitlines()
        n     = int(request.args.get('n', 50))
        return jsonify({'lines': lines[-n:], 'total': len(lines)})
    except FileNotFoundError:
        return jsonify({'lines': [], 'total': 0})

@app.route('/clear-log', methods=['POST'])
def clear_log():
    LOG_FILE.write_text('', encoding='utf-8')
    return jsonify({'ok': True})

@app.route('/history', methods=['GET'])
def history():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        return jsonify({'ok': True, 'data': data, 'total': len(data)})
    except FileNotFoundError:
        return jsonify({'ok': True, 'data': [], 'total': 0})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print('═' * 50)
    print('  WorksFree 잡코리아 로컬 서버')
    print('  URL: http://localhost:8765')
    print('  종료: Ctrl+C')
    print('═' * 50)
    app.run(host='127.0.0.1', port=8765, debug=False)
