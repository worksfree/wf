"""
빌드된 exe에서 필수 모듈들이 import 가능한지 테스트하는 스크립트
"""
import sys

# 테스트할 모듈 목록
required_modules = [
    'ntplib',
    'keyboard',
    'psutil',
    'tqdm',
    'openpyxl',
    'pyperclip',
    'pyautogui',
    'pywinauto',
    'cpuinfo.cpuinfo',
]

def test_imports():
    """모든 필수 모듈의 import 가능 여부 테스트"""
    print("=" * 60)
    print("Module Import Test")
    print("=" * 60)
    
    failed = []
    passed = []
    
    for module_name in required_modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name:30} - OK")
            passed.append(module_name)
        except ImportError as e:
            print(f"✗ {module_name:30} - FAILED: {e}")
            failed.append((module_name, str(e)))
        except Exception as e:
            print(f"? {module_name:30} - ERROR: {e}")
            failed.append((module_name, str(e)))
    
    print("\n" + "=" * 60)
    print(f"Total: {len(required_modules)}, Passed: {len(passed)}, Failed: {len(failed)}")
    print("=" * 60)
    
    if failed:
        print("\nFailed modules:")
        for mod, err in failed:
            print(f"  - {mod}: {err}")
        return 1
    else:
        print("\n✅ All modules imported successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(test_imports())
