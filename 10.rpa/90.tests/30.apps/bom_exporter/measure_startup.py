"""
앱 시작 시간 측정 스크립트 (UI 나타나는 시간 기준)
"""

import subprocess
import time
from pathlib import Path
import sys

try:
    import pygetwindow as gw
except ImportError:
    print("⚠️ pygetwindow 설치 필요: pip install pygetwindow")
    sys.exit(1)

# 측정 대상: 소스 실행
script_path = Path(__file__).parent / "ui_main.py"
python_exe = sys.executable

print(f"📊 시작 시간 측정: {script_path.name}")
print(f"Python: {python_exe}")
print()

# 5번 측정
times = []
for i in range(5):
    print(f"측정 {i+1}/5...", end=" ", flush=True)

    start = time.perf_counter()

    # 프로세스 시작
    proc = subprocess.Popen([python_exe, str(script_path)])

    # 창이 나타날 때까지 대기 (최대 10초)
    window_found = False
    for _ in range(100):  # 10초 = 100 * 0.1초
        time.sleep(0.1)
        windows = gw.getWindowsWithTitle("BOM 엑셀 저장")
        if windows:
            window_found = True
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            print(f"{elapsed:.2f}초")
            break

    if not window_found:
        print("타임아웃 (10초)")
        proc.terminate()
        continue

    # 프로세스 종료
    time.sleep(0.5)
    proc.terminate()
    time.sleep(1)

print()
print("=" * 50)
if times:
    print(f"평균 시작 시간: {sum(times)/len(times):.2f}초")
    print(f"최소: {min(times):.2f}초, 최대: {max(times):.2f}초")
    print()
    if sum(times) / len(times) < 3.0:
        print("✅ 목표 달성! (3초 이내)")
    else:
        print("⚠️ 목표 미달성 (3초 초과)")
else:
    print("❌ 측정 실패")
print("=" * 50)
