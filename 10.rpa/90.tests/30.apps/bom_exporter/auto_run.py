"""
bom_exporter 자동화 스크립트 (마우스 커서 표시)
대상 폴더: D:\\assy_samples\\sample03
"""

import pyautogui
import time
import subprocess
from pathlib import Path
import sys

try:
    import pygetwindow as gw
except ImportError:
    print("⚠️ pygetwindow가 설치되지 않았습니다. pip install pygetwindow")
    gw = None

try:
    from pywinauto import Application
    from pywinauto.findwindows import find_window
except ImportError:
    print("⚠️ pywinauto가 설치되지 않았습니다. pip install pywinauto")
    Application = None

# pyautogui 설정
pyautogui.PAUSE = 0.5  # 각 동작 사이 0.5초 대기
pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단

# 설정
TARGET_FOLDER = r"D:\assy_samples\sample03"
APP_PATH = Path(__file__).parent / "ui_main.py"
PYTHON_EXE = sys.executable


def find_and_activate_window(title_contains):
    """창 제목에 특정 문자열이 포함된 창 찾기 및 활성화"""
    if not gw:
        return None
    windows = gw.getWindowsWithTitle(title_contains)
    if windows:
        window = windows[0]
        window.activate()
        time.sleep(0.5)
        return window
    return None


def click_button_by_text(window_title, button_text):
    """pywinauto를 사용하여 버튼 텍스트로 버튼 찾아서 클릭"""
    if not Application:
        return False

    try:
        app = Application(backend="uia").connect(title=window_title, timeout=5)
        window = app.window(title=window_title)

        # 버튼 찾기
        button = window.child_window(title=button_text, control_type="Button")
        if button.exists():
            # 버튼의 중심 좌표 가져오기
            rect = button.rectangle()
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2

            print(f"   버튼 발견: {button_text} at ({center_x}, {center_y})")

            # 마우스를 버튼으로 이동하고 클릭
            pyautogui.moveTo(center_x, center_y, duration=1.0)
            time.sleep(0.3)
            pyautogui.click()
            return True
    except Exception as e:
        print(f"   ⚠️ pywinauto 버튼 찾기 실패: {e}")

    return False


def main():
    print("=== bom_exporter 자동화 시작 ===")
    print(f"대상 폴더: {TARGET_FOLDER}")
    print(f"마우스 커서가 화면에 표시됩니다.")
    print()

    # 대상 폴더 확인
    if not Path(TARGET_FOLDER).exists():
        print(f"❌ 대상 폴더가 존재하지 않습니다: {TARGET_FOLDER}")
        return

    # bom_exporter 실행
    print("🚀 bom_exporter 실행 중...")
    process = subprocess.Popen([PYTHON_EXE, str(APP_PATH)])

    # 앱 로딩 대기 (5초)
    print("⏳ 앱 로딩 대기 중... (5초)")
    time.sleep(5)

    try:
        # bom_exporter 창 찾기 및 활성화
        print("🔍 bom_exporter 창 찾는 중...")
        window = None
        for attempt in range(10):
            window = find_and_activate_window("BOM 엑셀 저장")
            if window:
                print(f"✅ 창 발견: {window.title}")
                print(
                    f"   위치: ({window.left}, {window.top}), 크기: {window.width}x{window.height}"
                )
                break
            print(f"   시도 {attempt + 1}/10 - 창을 찾지 못함, 1초 후 재시도...")
            time.sleep(1)

        if not window:
            print("❌ bom_exporter 창을 찾을 수 없습니다.")
            process.terminate()
            return

        # 창 내부 좌표 계산 (창 왼쪽 상단 기준)
        window_x = window.left
        window_y = window.top
        window_width = window.width
        window_height = window.height

        # 1. "폴더 선택" 버튼 클릭
        print("\n👆 1단계: '폴더 선택' 버튼 클릭")

        # 먼저 pywinauto로 버튼 찾아서 클릭 시도
        if click_button_by_text("BOM 엑셀 저장", "폴더 선택"):
            print("   ✅ pywinauto로 버튼 클릭 성공")
        else:
            # pywinauto 실패 시 좌표로 클릭
            print("   ⚠️ 좌표 기반 클릭으로 시도...")
            folder_btn_x = window_x + window_width // 2
            folder_btn_y = window_y + 100  # 창 상단에서 100픽셀 아래

            pyautogui.moveTo(folder_btn_x, folder_btn_y, duration=1.0)
            time.sleep(0.5)
            pyautogui.click()

        # 파일 대화상자 로딩 대기
        print("⏳ 파일 대화상자 대기 중... (3초)")
        time.sleep(3)

        # 2. 경로 입력 필드에 대상 폴더 경로 입력
        print(f"\n⌨️ 2단계: 경로 입력 - {TARGET_FOLDER}")

        # Ctrl+L로 주소창 포커스 (파일 탐색기)
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)

        # 기존 경로 지우기
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.3)

        # 대상 경로 입력
        pyautogui.write(TARGET_FOLDER, interval=0.05)
        time.sleep(0.5)

        # Enter로 경로 이동
        pyautogui.press("enter")
        print("✅ 경로 입력 완료")

        # 폴더 선택 확정 대기
        print("⏳ 폴더 선택 대기 중... (2초)")
        time.sleep(2)

        # "폴더 선택" 버튼 클릭 (대화상자 내)
        pyautogui.press("enter")

        # 앱이 폴더 분석하는 시간 대기
        print("⏳ 폴더 분석 대기 중... (10초)")
        time.sleep(10)

        # 3. "실행" 버튼 클릭 (창 중앙)
        print("\n👆 3단계: '실행' 버튼 클릭")

        # 창을 다시 활성화
        window = find_and_activate_window("BOM 엑셀 저장")
        if window:
            window_x = window.left
            window_y = window.top
            window_width = window.width
            window_height = window.height

            run_btn_x = window_x + window_width // 2
            run_btn_y = window_y + window_height // 2 + 100  # 창 중앙보다 조금 아래
        else:
            print("⚠️ 창을 찾을 수 없어 화면 중앙을 클릭합니다.")
            screen_width, screen_height = pyautogui.size()
            run_btn_x = screen_width // 2
            run_btn_y = screen_height // 2

        # 마우스를 천천히 이동
        pyautogui.moveTo(run_btn_x, run_btn_y, duration=1.0)
        time.sleep(0.5)
        pyautogui.click()

        print("\n✅ 자동화 작업 시작됨")
        print("⏳ 작업이 완료될 때까지 대기하세요...")
        print("   (Ctrl+C로 스크립트를 중단할 수 있습니다)")

        # 작업 완료 대기
        process.wait()

        print("\n✅ bom_exporter 작업 완료")

    except pyautogui.FailSafeException:
        print("\n⚠️ 사용자가 마우스를 화면 모서리로 이동하여 중단했습니다.")
        process.terminate()
    except KeyboardInterrupt:
        print("\n⚠️ 사용자가 Ctrl+C로 중단했습니다.")
        process.terminate()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        process.terminate()


if __name__ == "__main__":
    main()
