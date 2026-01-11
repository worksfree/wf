"""
폴더 선택 시 크래시 디버깅용 스크립트
"""
import sys
import traceback
from pathlib import Path

def test_imports():
    """모듈 import 테스트"""
    error_log = []
    
    print("="*60)
    print("Module Import Test")
    print("="*60)
    
    modules_to_test = [
        'tkinter',
        'ntplib',
        'keyboard',
        'psutil',
        'tqdm',
        'openpyxl',
        'pyperclip',
        'pyautogui',
        'pywinauto',
        'cpuinfo.cpuinfo',
        'wmi',
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            msg = f"✗ {module}: {str(e)}"
            print(msg)
            error_log.append(msg)
    
    return error_log

def test_hwinfo():
    """HardwareInfo 초기화 테스트"""
    print("\n" + "="*60)
    print("HardwareInfo Test")
    print("="*60)
    
    try:
        import wf_hwinfo
        hw = wf_hwinfo.HardwareInfo()
        print(f"✓ CPU: {hw.cpu_id[:50]}...")
        print(f"✓ MB: {hw.mainboard_id}")
        print(f"✓ Fingerprint: {hw.fingerprint[:32]}...")
        return []
    except Exception as e:
        msg = f"✗ HardwareInfo failed: {str(e)}\n{traceback.format_exc()}"
        print(msg)
        return [msg]

def test_automation_import():
    """BomAutomation import 테스트"""
    print("\n" + "="*60)
    print("BomAutomation Import Test")
    print("="*60)
    
    try:
        from automation import BomAutomation
        print("✓ BomAutomation imported successfully")
        return []
    except Exception as e:
        msg = f"✗ BomAutomation import failed: {str(e)}\n{traceback.format_exc()}"
        print(msg)
        return [msg]

def test_automation_init():
    """BomAutomation 초기화 테스트 (폴더 없이)"""
    print("\n" + "="*60)
    print("BomAutomation Init Test (without folder)")
    print("="*60)
    
    try:
        from automation import BomAutomation
        auto = BomAutomation(folder_path=None, console_mode=True)
        print("✓ BomAutomation initialized successfully")
        return []
    except Exception as e:
        msg = f"✗ BomAutomation init failed: {str(e)}\n{traceback.format_exc()}"
        print(msg)
        return [msg]

if __name__ == "__main__":
    all_errors = []
    
    print(f"\nPython: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"CWD: {Path.cwd()}\n")
    
    all_errors.extend(test_imports())
    all_errors.extend(test_hwinfo())
    all_errors.extend(test_automation_import())
    all_errors.extend(test_automation_init())
    
    print("\n" + "="*60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} errors found")
        print("="*60)
        for err in all_errors:
            print(err)
        
        # 에러 로그 파일 저장
        log_file = Path("debug_crash.log")
        log_file.write_text("\n\n".join(all_errors), encoding='utf-8')
        print(f"\nError log saved to: {log_file.absolute()}")
    else:
        print("SUCCESS: All tests passed!")
        print("="*60)
    
    input("\nPress Enter to exit...")
