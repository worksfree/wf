"""
Geometry override 자동 테스트 스크립트
"""
import subprocess
import time
import json
import pyautogui
from pathlib import Path
import sys

def test_geometry_override():
    print("=" * 80)
    print("Geometry Override 자동 테스트 시작")
    print("=" * 80)
    
    # 설정 파일 경로 (개발 모드는 config 폴더 사용)
    settings_path_dev = Path(r"D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\config\bom_exporter\settings.json")
    settings_path_release = Path(r"C:\Users\USER\.wf_rpa\bom_exporter\settings.json")
    python_exe = r"C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    app_path = r"D:\drive_files\10.worksfree\10.rpa\30.apps\bom_exporter\ui_main.py"
    
    # 1단계: 설정 파일 삭제 (초기화)
    print("\n[1단계] 설정 파일 초기화...")
    for settings_path in [settings_path_dev, settings_path_release]:
        if settings_path.exists():
            settings_path.unlink()
            print(f"✅ 설정 파일 삭제: {settings_path}")
    
    # 2단계: 앱 실행
    print("\n[2단계] 앱 실행 중...")
    proc = subprocess.Popen([python_exe, app_path], cwd=str(Path(app_path).parent))
    print(f"✅ 프로세스 시작 (PID: {proc.pid})")
    time.sleep(3)  # 앱 로딩 대기
    
    # 3단계: 창 위치 확인 및 이동
    print("\n[3단계] 창 찾기 및 이동...")
    try:
        # 창 찾기 (타이틀에 "BOM 엑셀 저장" 포함)
        windows = pyautogui.getWindowsWithTitle("BOM 엑셀 저장")
        if not windows:
            print("❌ 창을 찾을 수 없습니다!")
            proc.kill()
            return False
        
        window = windows[0]
        print(f"✅ 창 발견: {window.title}")
        print(f"   초기 위치: ({window.left}, {window.top})")
        print(f"   초기 크기: {window.width}x{window.height}")
        
        # 테스트용 위치로 이동
        test_x, test_y = 500, 400
        window.moveTo(test_x, test_y)
        time.sleep(0.5)
        
        actual_pos = (window.left, window.top)
        print(f"   이동 후 위치: {actual_pos}")
        
    except Exception as e:
        print(f"❌ 창 조작 실패: {e}")
        proc.kill()
        return False
    
    # 4단계: Alt+G 전송
    print("\n[4단계] Alt+G 전송...")
    try:
        window.activate()
        time.sleep(0.3)
        pyautogui.hotkey('alt', 'g')
        print("✅ Alt+G 전송 완료")
        time.sleep(1.5)  # 저장 대기
    except Exception as e:
        print(f"❌ 핫키 전송 실패: {e}")
        proc.kill()
        return False
    
    # 5단계: 설정 파일 확인
    print("\n[5단계] 설정 파일 확인...")
    
    # 어느 경로에 저장되었는지 확인
    settings_path = None
    for path in [settings_path_dev, settings_path_release]:
        if path.exists():
            settings_path = path
            print(f"✅ 설정 파일 발견: {settings_path}")
            break
    
    if not settings_path:
        print(f"❌ 설정 파일이 생성되지 않았습니다!")
        print(f"   확인한 경로:")
        print(f"   - {settings_path_dev}")
        print(f"   - {settings_path_release}")
        proc.kill()
        return False
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    saved_geo = settings.get('ui_config', {}).get('window_geometry_override', '')
    print(f"✅ 저장된 geometry: {saved_geo}")
    
    if not saved_geo:
        print("❌ geometry override가 비어있습니다!")
        proc.kill()
        return False
    
    # geometry 파싱
    parts = saved_geo.split('+')
    if len(parts) < 3:
        print(f"❌ geometry 형식 오류: {saved_geo}")
        proc.kill()
        return False
    
    size_part = parts[0]
    saved_x = int(parts[1])
    saved_y = int(parts[2])
    print(f"   파싱된 위치: ({saved_x}, {saved_y})")
    
    # 6단계: 앱 종료
    print("\n[6단계] 앱 종료...")
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except:
        proc.kill()
    print("✅ 앱 종료 완료")
    time.sleep(1)
    
    # 7단계: 앱 재실행
    print("\n[7단계] 앱 재실행...")
    proc2 = subprocess.Popen([python_exe, app_path], cwd=str(Path(app_path).parent))
    print(f"✅ 프로세스 재시작 (PID: {proc2.pid})")
    time.sleep(3)
    
    # 8단계: 창 위치 확인
    print("\n[8단계] 복원된 창 위치 확인...")
    try:
        windows = pyautogui.getWindowsWithTitle("BOM 엑셀 저장")
        if not windows:
            print("❌ 창을 찾을 수 없습니다!")
            proc2.kill()
            return False
        
        window = windows[0]
        restored_pos = (window.left, window.top)
        print(f"   복원된 위치: {restored_pos}")
        print(f"   복원된 크기: {window.width}x{window.height}")
        
        # 위치 비교 (±10 픽셀 허용)
        pos_match = abs(restored_pos[0] - saved_x) <= 10 and abs(restored_pos[1] - saved_y) <= 10
        
        if pos_match:
            print("✅ SUCCESS: 창 위치가 정확히 복원되었습니다!")
            result = True
        else:
            print(f"❌ FAIL: 위치 불일치")
            print(f"   예상: ({saved_x}, {saved_y})")
            print(f"   실제: {restored_pos}")
            print(f"   차이: ({abs(restored_pos[0] - saved_x)}, {abs(restored_pos[1] - saved_y)})")
            result = False
        
    except Exception as e:
        print(f"❌ 창 확인 실패: {e}")
        result = False
    finally:
        try:
            proc2.terminate()
            proc2.wait(timeout=3)
        except:
            proc2.kill()
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 테스트 성공!")
    else:
        print("❌ 테스트 실패 - 추가 디버깅 필요")
    print("=" * 80)
    
    return result

if __name__ == "__main__":
    success = test_geometry_override()
    sys.exit(0 if success else 1)
