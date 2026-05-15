import pyautogui
import os
import sys

# --- 설정 ---
# 화면에서 찾을 이미지 파일의 전체 경로
IMAGE_TO_FIND = r'D:\drive_files\10.worksfree\10.rpa\70.webs\recruit\btn_pop_close.png'

# 이미지 매칭 시 신뢰도 설정 (0.0 ~ 1.0)
# 이 기능을 사용하려면 'opencv-python' 라이브러리가 필요합니다. (pip install opencv-python)
# 0.9는 90% 일치함을 의미하며, 일반적으로 좋은 시작점입니다.
CONFIDENCE_LEVEL = 0.9

# --- 메인 로직 ---

def find_and_click_image(image_path, confidence):
    """
    화면에서 특정 이미지를 찾아 중앙을 클릭합니다.

    Args:
        image_path (str): 찾을 이미지 파일의 전체 경로.
        confidence (float): 이미지 매칭 신뢰도.

    Returns:
        bool: 이미지를 찾아 클릭했으면 True, 아니면 False.
    """
    print(f"화면에서 '{os.path.basename(image_path)}' 이미지를 찾습니다...")

    # 1. 이미지 파일이 실제로 존재하는지 확인
    if not os.path.exists(image_path):
        print(f"오류: 이미지 파일을 찾을 수 없습니다: {image_path}")
        return False

    # 2. 화면에서 이미지 찾기 시도
    try:
        # locateOnScreen은 이미지를 찾으면 Box(left, top, width, height) 객체를, 못 찾으면 None을 반환합니다.
        # 이 작업은 다소 느릴 수 있습니다.
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        
        if location:
            # 3. 이미지를 찾았으면, 해당 위치의 중앙 좌표를 계산하여 클릭
            print(f"성공: 이미지를 {location} 위치에서 찾았습니다.")
            
            # 찾은 영역의 중앙 좌표를 얻습니다.
            center_point = pyautogui.center(location)
            print(f"이미지의 중앙 좌표인 {center_point}(을)를 클릭합니다.")
            
            # 해당 좌표를 클릭합니다.
            pyautogui.click(center_point)
            
            print("클릭을 완료했습니다.")
            return True
        else:
            # 4. 이미지를 찾지 못한 경우
            print("실패: 화면에서 이미지를 찾지 못했습니다.")
            return False

    except pyautogui.PyAutoGUIException as e:
        # PyAutoGUI 관련 예외 처리 (예: 라이브러리 설치 문제)
        print(f"PyAutoGUI 오류가 발생했습니다: {e}")
        print("참고: 이 기능을 사용하려면 'opencv-python' 라이브러리 설치가 필요합니다 (`pip install opencv-python`).")
        return False
    except Exception as e:
        print(f"알 수 없는 오류가 발생했습니다: {e}")
        return False

# --- 스크립트 실행 ---
if __name__ == "__main__":
    # 필수 라이브러리 설치 여부 확인
    try:
        import pyautogui
    except ImportError:
        print("오류: 'PyAutoGUI' 라이브러리가 설치되지 않았습니다.")
        print("명령 프롬프트(CMD)나 터미널에서 'pip install pyautogui'를 실행하여 설치해주세요.")
        sys.exit(1)
        
    try:
        import cv2
    except ImportError:
        print("경고: 'opencv-python' 라이브러리가 설치되지 않았습니다.")
        print("정확한 이미지 인식을 위해 설치를 권장합니다: 'pip install opencv-python'")
        # OpenCV가 없으면 confidence 기능이 동작하지 않아 정확도가 떨어질 수 있습니다.
    
    find_and_click_image(IMAGE_TO_FIND, CONFIDENCE_LEVEL)
