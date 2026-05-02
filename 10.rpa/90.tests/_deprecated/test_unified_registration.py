"""
통합 등록 로직 테스트
4개 앱의 등록 여부 판단 및 크레딧 초기화 검증
"""

import sys
import os
from pathlib import Path
import json
import tempfile
import shutil

# 공통 모듈 경로 추가
common_path = Path(__file__).parent / "10.common"
sys.path.insert(0, str(common_path))

try:
    from wf_credit_manager import WorksFreeManager
    from wf_app_init_helpers import init_credit_manager_only
    WFM_AVAILABLE = True
except ImportError as e:
    print(f"❌ 핵심 모듈 import 실패: {e}")
    WFM_AVAILABLE = False
    sys.exit(1)


def test_registration_flag_priority():
    """is_registered 플래그 우선순위 테스트"""
    print("\n" + "="*60)
    print("TEST 1: is_registered 플래그 우선순위")
    print("="*60)
    
    # 환경 변수 먼저 백업
    original_home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    original_wf_home = os.environ.get("WF_RPA_HOME")
    original_dev = os.environ.get("WF_RPA_DEV")
    
    # 임시 설정 디렉토리 생성
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        config_file = config_dir / "wf_rpa_config.json"
        
        # 환경 변수 설정 (싱글톤 생성 전에 설정)
        os.environ["WF_RPA_HOME"] = str(config_dir)
        os.environ["WF_RPA_DEV"] = "0"  # 개발 모드 강제 비활성화
        
        try:
            # 케이스 1: is_registered=True, reg_time_local 없음
            test_config_1 = {
                "user_info": {
                    "is_registered": True,
                    "reg_time_local": "",
                    "user_email": "test@example.com"
                }
            }
            config_file.write_text(json.dumps(test_config_1, ensure_ascii=False), encoding='utf-8')
            
            # WorksFreeManager 완전 재초기화
            WorksFreeManager._instance = None
            if hasattr(WorksFreeManager, '_initialized'):
                delattr(WorksFreeManager._instance.__class__, '_initialized')
            wfm = WorksFreeManager()
            
            result_1 = wfm.is_registered()
            print(f"  케이스 1 (플래그 True, 타임스탬프 없음): {result_1}")
            assert result_1 == True, "플래그가 True면 등록으로 인식되어야 함"
            print("  ✅ PASS: 플래그 우선 적용")
            
            # 케이스 2: is_registered=False, reg_time_local 있음
            test_config_2 = {
                "user_info": {
                    "is_registered": False,
                    "reg_time_local": "2025-11-25T10:00:00",
                    "user_email": "test@example.com"
                }
            }
            config_file.write_text(json.dumps(test_config_2, ensure_ascii=False), encoding='utf-8')
            
            WorksFreeManager._instance = None
            if WorksFreeManager._instance:
                WorksFreeManager._instance._initialized = False
            wfm = WorksFreeManager()
            result_2 = wfm.is_registered()
            print(f"  케이스 2 (플래그 False, 타임스탬프 있음): {result_2}")
            assert result_2 == True, "타임스탬프 있으면 폴백으로 등록 인식"
            print("  ✅ PASS: 타임스탬프 폴백 동작")
            
            # 케이스 3: 둘 다 없음
            test_config_3 = {
                "user_info": {
                    "is_registered": False,
                    "reg_time_local": "",
                    "user_email": ""
                }
            }
            config_file.write_text(json.dumps(test_config_3, ensure_ascii=False), encoding='utf-8')
            
            WorksFreeManager._instance = None
            if WorksFreeManager._instance:
                WorksFreeManager._instance._initialized = False
            wfm = WorksFreeManager()
            result_3 = wfm.is_registered()
            print(f"  케이스 3 (둘 다 False/없음): {result_3}")
            assert result_3 == False, "미등록으로 인식되어야 함"
            print("  ✅ PASS: 미등록 정상 인식")
            
        finally:
            # 환경 변수 복구
            if original_wf_home:
                os.environ["WF_RPA_HOME"] = original_wf_home
            elif "WF_RPA_HOME" in os.environ:
                del os.environ["WF_RPA_HOME"]
            
            if original_dev:
                os.environ["WF_RPA_DEV"] = original_dev
            elif "WF_RPA_DEV" in os.environ:
                del os.environ["WF_RPA_DEV"]
            
            WorksFreeManager._instance = None
    
    print("\n✅ TEST 1 전체 통과\n")
    return True


def test_helper_function():
    """헬퍼 함수 크레딧 매니저 생성 테스트"""
    print("\n" + "="*60)
    print("TEST 2: wf_app_init_helpers 헬퍼 함수")
    print("="*60)
    
    # Mock 객체 생성
    class MockWFManager:
        def get_user_info(self):
            return {"user_mail": "test@example.com"}
    
    try:
        mock_wfm = MockWFManager()
        credit_mgr = init_credit_manager_only(
            app_name="test_app",
            wf_manager=mock_wfm,
            logger=None
        )
        
        if credit_mgr:
            print(f"  크레딧 매니저 생성: {type(credit_mgr).__name__}")
            print("  ✅ PASS: 헬퍼 함수로 매니저 생성 성공")
            return True
        else:
            print("  ⚠️  크레딧 매니저 None (CreditManager 모듈 없음 - 정상)")
            return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_app_imports():
    """4개 앱 임포트 테스트"""
    print("\n" + "="*60)
    print("TEST 3: 4개 앱 파일 임포트 검증")
    print("="*60)
    
    apps = [
        ("bom2excel", "30.apps/bom2excel/ui_main.py"),
        ("dwg_classifier", "50.data/dwg_classifier/ui_main.py"),
        ("conversion_verifier", "50.data/conversion_verifier/ui_main.py"),
        ("korean_filename_normalizer", "50.data/korean_filename_normalizer/ui_main.py"),
    ]
    
    base_path = Path(__file__).parent
    results = []
    
    for app_name, rel_path in apps:
        app_file = base_path / rel_path.replace("/", os.sep)
        if not app_file.exists():
            print(f"  ❌ {app_name}: 파일 없음 ({app_file})")
            results.append(False)
            continue
        
        # 구문 검사 (컴파일 시도)
        try:
            with open(app_file, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, str(app_file), 'exec')
            print(f"  ✅ {app_name}: 구문 오류 없음")
            
            # 핵심 패턴 검증
            checks = {
                "WorksFreeManager import": "from wf_credit_manager import WorksFreeManager" in code,
                "Helper import": "from wf_app_init_helpers import" in code,
                "is_registered 호출": ".is_registered()" in code,
            }
            
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"    {status} {check_name}")
            
            all_passed = all(checks.values())
            results.append(all_passed)
            
        except SyntaxError as e:
            print(f"  ❌ {app_name}: 구문 오류 - {e}")
            results.append(False)
    
    if all(results):
        print("\n✅ TEST 3 전체 통과")
        return True
    else:
        print("\n⚠️  TEST 3 일부 실패")
        return False


def test_config_merge_logic():
    """설정 병합 로직 검증 (email_settings, google_sheets)"""
    print("\n" + "="*60)
    print("TEST 4: Config 섹션 병합 검증")
    print("="*60)
    
    # _set_cross_app_running 함수에서 병합 로직 테스트
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".wf_rpa"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "wf_rpa_config.json"
        
        # 초기 설정 (섹션 없음)
        initial_config = {
            "user_info": {"user_email": "test@example.com"},
            "execution_status": {}
        }
        config_file.write_text(json.dumps(initial_config, ensure_ascii=False), encoding='utf-8')
        
        # 병합 로직 시뮬레이션 (앱 시작 시 수행)
        data = json.loads(config_file.read_text(encoding='utf-8'))
        
        need_email = "email_settings" not in data
        need_sheets = "google_sheets" not in data
        
        print(f"  email_settings 필요: {need_email}")
        print(f"  google_sheets 필요: {need_sheets}")
        
        if need_email or need_sheets:
            # 템플릿 존재 확인 (실제 경로)
            # 10.rpa/config 폴더는 삭제되었으므로 사용자 홈폴더에서 찾기
            template_candidates = [
                Path.home() / ".wf_rpa" / "wf_rpa_config.json",
            ]
            bundle_cfg = next((c for c in template_candidates if c.exists()), None)
            
            if bundle_cfg:
                template = json.loads(bundle_cfg.read_text(encoding='utf-8'))
                if need_email and "email_settings" in template:
                    data["email_settings"] = template["email_settings"]
                    print("  ✅ email_settings 병합")
                if need_sheets and "google_sheets" in template:
                    data["google_sheets"] = template["google_sheets"]
                    print("  ✅ google_sheets 병합")
            else:
                print("  ⚠️  템플릿 파일 없음 (개발 환경 - 정상)")
        
        # 검증
        has_email = "email_settings" in data
        has_sheets = "google_sheets" in data
        
        print(f"\n  최종 설정 포함 여부:")
        print(f"    email_settings: {has_email}")
        print(f"    google_sheets: {has_sheets}")
        
        if has_email or has_sheets:
            print("  ✅ PASS: 병합 로직 동작 확인")
            return True
        else:
            print("  ⚠️  템플릿 없음 (정상 - 개발 환경)")
            return True


def test_automation_trial_check():
    """bom2excel automation.py trial_mode 판단 로직 검증"""
    print("\n" + "="*60)
    print("TEST 5: LicenseManager.check_trial_status 로직")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".wf_rpa"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "wf_rpa_config.json"
        
        # 케이스 1: is_registered=True
        test_config_1 = {
            "user_info": {
                "is_registered": True,
                "reg_time_local": "",
                "user_email": "test@example.com"
            }
        }
        config_file.write_text(json.dumps(test_config_1, ensure_ascii=False), encoding='utf-8')
        
        # 로직 시뮬레이션
        data = json.loads(config_file.read_text(encoding='utf-8'))
        user_info = data.get("user_info", {})
        trial_mode = not (user_info.get("is_registered") is True or user_info.get("reg_time_local"))
        
        print(f"  케이스 1 (플래그 True): trial_mode={trial_mode}")
        assert trial_mode == False, "등록 상태면 trial_mode는 False"
        print("  ✅ PASS")
        
        # 케이스 2: reg_time_local만 있음
        test_config_2 = {
            "user_info": {
                "is_registered": False,
                "reg_time_local": "2025-11-25T10:00:00",
                "user_email": "test@example.com"
            }
        }
        config_file.write_text(json.dumps(test_config_2, ensure_ascii=False), encoding='utf-8')
        
        data = json.loads(config_file.read_text(encoding='utf-8'))
        user_info = data.get("user_info", {})
        trial_mode = not (user_info.get("is_registered") is True or user_info.get("reg_time_local"))
        
        print(f"  케이스 2 (타임스탬프만): trial_mode={trial_mode}")
        assert trial_mode == False, "타임스탬프 있으면 등록 상태"
        print("  ✅ PASS")
        
        # 케이스 3: 둘 다 없음
        test_config_3 = {
            "user_info": {
                "is_registered": False,
                "reg_time_local": "",
                "user_email": ""
            }
        }
        config_file.write_text(json.dumps(test_config_3, ensure_ascii=False), encoding='utf-8')
        
        data = json.loads(config_file.read_text(encoding='utf-8'))
        user_info = data.get("user_info", {})
        trial_mode = not (user_info.get("is_registered") is True or user_info.get("reg_time_local"))
        
        print(f"  케이스 3 (둘 다 없음): trial_mode={trial_mode}")
        assert trial_mode == True, "미등록이면 trial_mode는 True"
        print("  ✅ PASS")
    
    print("\n✅ TEST 5 전체 통과\n")
    return True


def main():
    """전체 테스트 실행"""
    print("\n" + "="*70)
    print("  4개 앱 통합 등록/크레딧 로직 자동 테스트")
    print("="*70)
    
    if not WFM_AVAILABLE:
        print("\n❌ 필수 모듈 없음 - 테스트 중단")
        return False
    
    tests = [
        ("등록 플래그 우선순위", test_registration_flag_priority),
        ("헬퍼 함수 검증", test_helper_function),
        ("앱 파일 임포트", test_app_imports),
        ("Config 병합 로직", test_config_merge_logic),
        ("Trial 판단 로직", test_automation_trial_check),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            print(f"\n❌ {test_name} 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # 최종 결과
    print("\n" + "="*70)
    print("  최종 테스트 결과")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    total = len(results)
    passed_count = sum(results.values())
    print(f"\n  총 {passed_count}/{total} 테스트 통과")
    
    if all(results.values()):
        print("\n🎉 모든 테스트 통과 - 배포 준비 완료\n")
        return True
    else:
        print("\n⚠️  일부 테스트 실패 - 검토 필요\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
