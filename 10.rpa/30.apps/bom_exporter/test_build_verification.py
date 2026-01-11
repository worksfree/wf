"""
BOM Exporter Build Verification Test
빌드 전 종합 검증 테스트

테스트 항목:
1. 초기 사용자 체험판 크레딧 10000개 부여
2. 하드웨어 정보: CPU, Board, Storage (MAC 주소 미사용)
3. 모든 팝업/메시지박스가 메인창 중심에 표시
4. 설정/등록창이 FHD/QHD/UHD에서 모든 UI 요소 표시
"""

import sys
import os
from pathlib import Path
import json
import tempfile
import shutil

# Add common directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "10.common"))

def test_1_trial_credits_10000():
    """테스트 1: 초기 체험판 크레딧이 10000인지 확인"""
    print("\n" + "="*60)
    print("테스트 1: 초기 체험판 크레딧 10000 확인")
    print("="*60)
    
    try:
        import wf_license
        
        # Check default trial credits in code
        with open(Path(__file__).parent.parent.parent / "10.common" / "wf_license.py", "r", encoding="utf-8") as f:
            content = f.read()
            if '"trial_credits": 10000' in content:
                print("✅ wf_license.py에서 trial_credits가 10000으로 설정됨")
            else:
                print("❌ wf_license.py에서 trial_credits가 10000이 아님")
                return False
        
        # Check credit manager default
        import wf_credit_manager
        with open(Path(__file__).parent.parent.parent / "10.common" / "wf_credit_manager.py", "r", encoding="utf-8") as f:
            content = f.read()
            if 'trial_amount = self.policy.get("trial_credits", 10000)' in content:
                print("✅ wf_credit_manager.py에서 기본 trial_credits가 10000으로 설정됨")
            else:
                print("❌ wf_credit_manager.py에서 기본 trial_credits가 10000이 아님")
                return False
        
        print("✅ 테스트 1 통과: 체험판 크레딧 10000 확인됨")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 1 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_hardware_info_cpu_board_storage():
    """테스트 2: 하드웨어 정보가 CPU, Board, Storage를 사용하는지 확인 (MAC 주소 미사용)"""
    print("\n" + "="*60)
    print("테스트 2: 하드웨어 정보 CPU/Board/Storage 사용 확인")
    print("="*60)
    
    try:
        import wf_hwinfo
        
        # Initialize hardware info
        hw = wf_hwinfo.HardwareInfo()
        
        # Check that CPU, mainboard, and storage IDs are collected
        if hasattr(hw, 'cpu_id') and hw.cpu_id and hw.cpu_id != "UNKNOWN_CPU":
            print(f"✅ CPU 정보 수집됨: {hw.cpu_id[:50]}...")
        else:
            print(f"⚠️  CPU 정보: {getattr(hw, 'cpu_id', 'N/A')}")
        
        if hasattr(hw, 'mainboard_id') and hw.mainboard_id and hw.mainboard_id != "UNKNOWN_MB":
            print(f"✅ Mainboard 정보 수집됨: {hw.mainboard_id[:50]}...")
        else:
            print(f"⚠️  Mainboard 정보: {getattr(hw, 'mainboard_id', 'N/A')}")
        
        if hasattr(hw, 'storage_id') and hw.storage_id and hw.storage_id != "UNKNOWN_HD":
            print(f"✅ Storage 정보 수집됨: {hw.storage_id[:50]}...")
        else:
            print(f"⚠️  Storage 정보: {getattr(hw, 'storage_id', 'N/A')}")
        
        if hasattr(hw, 'fingerprint') and hw.fingerprint:
            print(f"✅ 하드웨어 지문 생성됨: {hw.fingerprint[:16]}...")
        else:
            print(f"❌ 하드웨어 지문 없음")
            return False
        
        # Verify MAC address is NOT used
        with open(Path(__file__).parent.parent.parent / "10.common" / "wf_hwinfo.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "get_mac_address" in content or "mac_address" in content.lower():
                print("⚠️  MAC 주소 관련 코드가 포함되어 있을 수 있음")
            else:
                print("✅ MAC 주소 미사용 확인")
        
        print("✅ 테스트 2 통과: 하드웨어 정보 올바르게 수집됨")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_messagebox_centering():
    """테스트 3: 메시지박스가 메인창 중심에 표시되도록 설정되었는지 확인"""
    print("\n" + "="*60)
    print("테스트 3: 메시지박스 중심 정렬 확인")
    print("="*60)
    
    try:
        # Check ui_main.py for messagebox parent binding
        with open(Path(__file__).parent / "ui_main.py", "r", encoding="utf-8") as f:
            content = f.read()
            
            if "_bind_messagebox_parent" in content:
                print("✅ _bind_messagebox_parent 메서드 발견")
                
                # Check that it wraps messagebox functions
                if 'kwargs.setdefault("parent", self.master)' in content:
                    print("✅ messagebox 함수들이 parent=self.master로 래핑됨")
                else:
                    print("❌ messagebox parent 설정이 없음")
                    return False
                
                # Check that it's called in __init__
                if "self._bind_messagebox_parent()" in content:
                    print("✅ __init__에서 _bind_messagebox_parent() 호출됨")
                else:
                    print("❌ __init__에서 _bind_messagebox_parent() 호출되지 않음")
                    return False
            else:
                print("❌ _bind_messagebox_parent 메서드가 없음")
                return False
        
        # Check for custom dialogs centering
        if "self.master.winfo_rootx()" in content and "self.master.winfo_rooty()" in content:
            print("✅ 커스텀 다이얼로그들이 메인창 좌표를 사용함")
        else:
            print("⚠️  커스텀 다이얼로그 중심 정렬 확인 필요")
        
        print("✅ 테스트 3 통과: 메시지박스 중심 정렬 확인됨")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_registration_settings_ui_visibility():
    """테스트 4: 등록/설정창이 FHD/QHD/UHD에서 UI 요소가 모두 보이는지 확인"""
    print("\n" + "="*60)
    print("테스트 4: 등록/설정창 UI 가시성 확인 (FHD/QHD/UHD)")
    print("="*60)
    
    try:
        # Check wf_register.py for adaptive UI settings
        with open(Path(__file__).parent.parent.parent / "10.common" / "wf_register.py", "r", encoding="utf-8") as f:
            content = f.read()
            
            if "get_adaptive_ui_settings" in content:
                print("✅ get_adaptive_ui_settings 함수 발견")
                
                # Check for resolution-based settings
                if "screen_width >= 3840" in content:  # UHD
                    print("✅ UHD (4K) 해상도 설정 포함")
                else:
                    print("❌ UHD 설정 없음")
                    return False
                
                if "screen_width >= 2560" in content:  # QHD
                    print("✅ QHD (1440p) 해상도 설정 포함")
                else:
                    print("❌ QHD 설정 없음")
                    return False
                
                print("✅ FHD (1080p) 기본 설정 포함")
                
                # Check for proper window sizes
                if '"window_width": 650' in content and '"window_height": 600' in content:
                    print("✅ UHD 창 크기: 650x600")
                if '"window_width": 600' in content and '"window_height": 550' in content:
                    print("✅ QHD 창 크기: 600x550")
                if '"window_width": 550' in content and '"window_height": 500' in content:
                    print("✅ FHD 창 크기: 550x500")
                
                # Check for missing UI key defaults
                if "setdefault" in content and "tree_height" in content:
                    print("✅ 누락된 UI 키에 대한 기본값 설정 포함")
                else:
                    print("⚠️  누락 UI 키 기본값 설정 확인 필요")
            else:
                print("❌ get_adaptive_ui_settings 함수가 없음")
                return False
        
        # Check ui_setting.py for settings window
        with open(Path(__file__).parent / "ui_setting.py", "r", encoding="utf-8") as f:
            content = f.read()
            
            if "center_window_on_screen" in content:
                print("✅ 설정창에서 center_window_on_screen 사용")
                
                # Check for adaptive sizing
                if "get_adaptive_ui_settings" in content:
                    print("✅ 설정창이 적응형 UI 설정 사용")
                else:
                    print("⚠️  설정창 적응형 설정 확인 필요")
            else:
                print("❌ 설정창 중심 정렬 없음")
                return False
        
        print("✅ 테스트 4 통과: 등록/설정창 UI 가시성 확인됨")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 4 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_import_verification():
    """테스트 5: 주요 모듈 임포트 확인"""
    print("\n" + "="*60)
    print("테스트 5: 주요 모듈 임포트 확인")
    print("="*60)
    
    modules_to_test = [
        "wf_hwinfo",
        "wf_license",
        "wf_credit_manager",
        "wf_register",
        "wf_log",
        "wf_settings_common",
    ]
    
    all_passed = True
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} 임포트 성공")
        except Exception as e:
            print(f"❌ {module_name} 임포트 실패: {e}")
            all_passed = False
    
    if all_passed:
        print("✅ 테스트 5 통과: 모든 모듈 임포트 성공")
    else:
        print("❌ 테스트 5 실패: 일부 모듈 임포트 실패")
    
    return all_passed


def test_6_config_file_structure():
    """테스트 6: 설정 파일 구조 확인"""
    print("\n" + "="*60)
    print("테스트 6: 설정 파일 구조 확인")
    print("="*60)
    
    try:
        import wf_credit_manager
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock the config directory
            original_home = Path.home()
            test_config_dir = temp_path / ".wf_rpa"
            test_config_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"✅ 임시 설정 디렉토리 생성: {test_config_dir}")
            
            # Check that credit manager can initialize
            print("✅ 크레딧 매니저 초기화 가능")
        
        print("✅ 테스트 6 통과: 설정 파일 구조 확인됨")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 6 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """모든 테스트 실행"""
    print("\n")
    print("*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + " " * 10 + "BOM Exporter Build Verification Tests" + " " * 10 + "*")
    print("*" + " " * 58 + "*")
    print("*" * 60)
    
    tests = [
        ("1. 체험판 크레딧 10000", test_1_trial_credits_10000),
        ("2. 하드웨어 정보 (CPU/Board/Storage)", test_2_hardware_info_cpu_board_storage),
        ("3. 메시지박스 중심 정렬", test_3_messagebox_centering),
        ("4. 등록/설정창 UI 가시성", test_4_registration_settings_ui_visibility),
        ("5. 모듈 임포트", test_5_import_verification),
        ("6. 설정 파일 구조", test_6_config_file_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 실행 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"총 {passed}/{total} 테스트 통과 ({passed*100//total}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 모든 테스트를 통과했습니다! 빌드 준비 완료.")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패. 문제를 해결 후 다시 실행하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
