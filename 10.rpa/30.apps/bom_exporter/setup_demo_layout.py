"""
데모 영상 촬영을 위한 화면 레이아웃 자동 설정
- 왼쪽 1/3: 탐색기 (BOM 폴더)
- 오른쪽 2/3: SolidWorks
- 중앙: 자동화 앱 UI
"""

import time
import win32gui
import win32con
import pyautogui
from pathlib import Path


class DemoLayoutManager:
    def __init__(self):
        # 화면 설정 (작업 표시줄 제외)
        self.screen_width = 1920
        self.screen_height = 1040  # 작업 표시줄 제외
        
        # 영역 분할
        self.explorer_x = 0
        self.explorer_y = 0
        self.explorer_width = 640  # 1/3
        self.explorer_height = 1040
        
        self.solidworks_x = 640
        self.solidworks_y = 0
        self.solidworks_width = 1280  # 2/3
        self.solidworks_height = 1040
        
        # 앱 UI 크기 (settings에서 가져오거나 기본값)
        self.app_width = 580
        self.app_height = 600
        
        # 앱 UI 위치 (SolidWorks 영역 중앙)
        self.app_x = self.solidworks_x + (self.solidworks_width - self.app_width) // 2
        self.app_y = (self.screen_height - self.app_height) // 2
    
    def find_window_by_title(self, title_part: str):
        """윈도우 제목으로 핸들 찾기"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title_part.lower() in window_title.lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        return windows[0] if windows else None
    
    def set_window_position(self, hwnd, x, y, width, height):
        """윈도우 위치 및 크기 설정"""
        if hwnd:
            # 최대화 해제
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            
            # 위치와 크기 설정
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                x, y, width, height,
                win32con.SWP_SHOWWINDOW
            )
            print(f"✅ 창 배치 완료: ({x}, {y}) - {width}x{height}")
        else:
            print("❌ 창을 찾을 수 없습니다.")
    
    def open_explorer(self, folder_path: str):
        """탐색기 열기"""
        import subprocess
        subprocess.Popen(f'explorer /select,"{folder_path}"')
        time.sleep(1)
        return self.find_window_by_title("탐색기")
    
    def setup_explorer(self, bom_folder: str):
        """탐색기 배치 (왼쪽 1/3)"""
        print("\n📂 1. 탐색기 설정 중...")
        
        # BOM 폴더 경로 확인
        bom_path = Path(bom_folder)
        if not bom_path.exists():
            print(f"❌ BOM 폴더를 찾을 수 없습니다: {bom_folder}")
            return False
        
        # 탐색기 열기
        hwnd = self.open_explorer(str(bom_path))
        
        if not hwnd:
            print("⚠️ 탐색기를 찾을 수 없습니다. 수동으로 열어주세요.")
            input("탐색기를 열고 Enter를 누르세요...")
            hwnd = self.find_window_by_title("탐색기")
        
        # 위치 설정
        self.set_window_position(
            hwnd,
            self.explorer_x,
            self.explorer_y,
            self.explorer_width,
            self.explorer_height
        )
        return True
    
    def setup_solidworks(self):
        """SolidWorks 배치 (오른쪽 2/3)"""
        print("\n🔧 2. SolidWorks 설정 중...")
        
        # SolidWorks 찾기
        hwnd = self.find_window_by_title("SOLIDWORKS")
        
        if not hwnd:
            print("⚠️ SolidWorks가 실행되지 않았습니다.")
            print("   SolidWorks를 실행하고 Enter를 누르세요...")
            input()
            hwnd = self.find_window_by_title("SOLIDWORKS")
        
        if not hwnd:
            print("❌ SolidWorks 창을 찾을 수 없습니다.")
            return False
        
        # 위치 설정
        self.set_window_position(
            hwnd,
            self.solidworks_x,
            self.solidworks_y,
            self.solidworks_width,
            self.solidworks_height
        )
        return True
    
    def setup_app_ui(self):
        """자동화 앱 UI 배치 (SolidWorks 영역 중앙)"""
        print("\n🎯 3. 자동화 앱 UI 설정 중...")
        
        # 앱 찾기 (여러 가능한 제목)
        possible_titles = ["BOM 엑셀 저장", "bom_exporter", "Bom Exporter"]
        hwnd = None
        
        for title in possible_titles:
            hwnd = self.find_window_by_title(title)
            if hwnd:
                break
        
        if not hwnd:
            print("⚠️ 자동화 앱이 실행되지 않았습니다.")
            print("   앱을 실행하고 Enter를 누르세요...")
            input()
            
            for title in possible_titles:
                hwnd = self.find_window_by_title(title)
                if hwnd:
                    break
        
        if not hwnd:
            print("❌ 자동화 앱 창을 찾을 수 없습니다.")
            return False
        
        # 위치 설정 (SolidWorks 영역 중앙)
        self.set_window_position(
            hwnd,
            self.app_x,
            self.app_y,
            self.app_width,
            self.app_height
        )
        
        # 항상 위 설정
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            self.app_x, self.app_y,
            self.app_width, self.app_height,
            win32con.SWP_SHOWWINDOW
        )
        
        return True
    
    def run(self, bom_folder: str, skip_solidworks: bool = False, skip_app: bool = False):
        """전체 레이아웃 설정 실행"""
        print("=" * 60)
        print("🎬 데모 영상 촬영 레이아웃 설정")
        print("=" * 60)
        print(f"\n화면 구성:")
        print(f"  - 전체: {self.screen_width}x{self.screen_height}")
        print(f"  - 탐색기: 왼쪽 1/3 ({self.explorer_width}px)")
        print(f"  - SolidWorks: 오른쪽 2/3 ({self.solidworks_width}px)")
        print(f"  - 앱 UI: 중앙 ({self.app_x}, {self.app_y})")
        
        success_count = 0
        total_count = 3
        
        # 1. 탐색기 설정
        if self.setup_explorer(bom_folder):
            success_count += 1
        
        time.sleep(0.5)
        
        # 2. SolidWorks 설정
        if not skip_solidworks:
            if self.setup_solidworks():
                success_count += 1
            else:
                print("⚠️ SolidWorks 설정 건너뜀 (나중에 수동으로 배치 가능)")
        else:
            print("\n🔧 2. SolidWorks 설정 건너뜀 (--skip-solidworks)")
            total_count -= 1
        
        time.sleep(0.5)
        
        # 3. 앱 UI 설정
        if not skip_app:
            if self.setup_app_ui():
                success_count += 1
            else:
                print("⚠️ 앱 UI 설정 건너뜀 (나중에 수동으로 배치 가능)")
        else:
            print("\n🎯 3. 앱 UI 설정 건너뜀 (--skip-app)")
            total_count -= 1
        
        print("\n" + "=" * 60)
        print(f"✅ 레이아웃 설정 완료! ({success_count}/{total_count})")
        print("=" * 60)
        print("\n💡 촬영 팁:")
        print("  1. OBS나 화면 녹화 프로그램 시작")
        print("  2. 녹화 영역: (0, 0) - 1920x1040")
        print("  3. 앱에서 '저장시작' 버튼 클릭")
        print("  4. 탐색기에서 BOM 폴더 새로고침 (F5)")
        
        if success_count < total_count:
            print("\n⚠️ 일부 창을 찾지 못했습니다. 수동으로 배치:")
            if not skip_solidworks:
                print(f"  - SolidWorks: ({self.solidworks_x}, {self.solidworks_y}) - {self.solidworks_width}x{self.solidworks_height}")
            if not skip_app:
                print(f"  - 앱 UI: ({self.app_x}, {self.app_y}) - {self.app_width}x{self.app_height}")
        
        return success_count > 0


def main():
    """메인 실행 함수"""
    import sys
    
    # BOM 폴더 경로 (인자로 받거나 기본값 사용)
    if len(sys.argv) > 1:
        bom_folder = sys.argv[1]
    else:
        # 기본 경로 예시
        bom_folder = r"D:\assy_samples\sample53\bom"
        print(f"⚠️ BOM 폴더 경로를 인자로 전달하지 않았습니다.")
        print(f"   기본 경로 사용: {bom_folder}\n")
        
        # 사용자에게 경로 입력 받기
        user_input = input(f"다른 경로를 사용하시겠습니까? (경로 입력 또는 Enter): ").strip()
        if user_input:
            bom_folder = user_input
    
    # 레이아웃 매니저 실행
    manager = DemoLayoutManager()
    manager.run(bom_folder)


if __name__ == "__main__":
    main()
