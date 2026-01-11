"""
데모 화면 캡처 스크립트
Alt+C를 누르면 1920x1040 해상도로 화면 캡처
"""
import keyboard
from PIL import ImageGrab
from datetime import datetime
from pathlib import Path
import time

# 저장 경로
SAVE_DIR = Path(__file__).parent / "demo_captures"
SAVE_DIR.mkdir(exist_ok=True)

# 캡처 카운터
capture_count = 0

def capture_screen():
    """화면 캡처 및 저장"""
    global capture_count
    
    try:
        # 전체 화면 캡처
        screenshot = ImageGrab.grab()
        
        # 1920x1040으로 크롭 (왼쪽 상단 기준)
        cropped = screenshot.crop((0, 0, 1920, 1040))
        
        # 파일명 생성 (타임스탬프 + 카운터)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_count += 1
        filename = f"demo_{timestamp}_{capture_count:03d}.png"
        filepath = SAVE_DIR / filename
        
        # 저장
        cropped.save(filepath, "PNG")
        print(f"✅ 캡처 완료: {filename}")
        
        # 짧은 비프음 (선택사항)
        try:
            import winsound
            winsound.Beep(1000, 100)
        except:
            pass
            
    except Exception as e:
        print(f"❌ 캡처 실패: {e}")

def main():
    """메인 실행"""
    print("=" * 60)
    print("데모 화면 캡처 스크립트 실행 중...")
    print("=" * 60)
    print(f"저장 경로: {SAVE_DIR.absolute()}")
    print("단축키: Alt+C - 화면 캡처 (1920x1040)")
    print("종료: Ctrl+C 또는 ESC")
    print("=" * 60)
    print()
    
    # Alt+C 단축키 등록
    keyboard.add_hotkey('alt+c', capture_screen)
    
    # ESC로 종료
    print("대기 중... (ESC를 누르면 종료)")
    keyboard.wait('esc')
    
    print(f"\n총 {capture_count}개 캡처 완료")
    print("스크립트 종료")

if __name__ == "__main__":
    main()
