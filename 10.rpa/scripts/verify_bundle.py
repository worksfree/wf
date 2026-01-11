"""
배포 번들 JSON 무결성 검증 스크립트

배포 전 자동 검증:
- policy.json: identity + policy만, 버전 정보 없음
- settings.json: 버전 주입됨, 사용자 경로 초기화됨
- credit_history.json: 번들에 없어야 함
"""

import json
import sys
from pathlib import Path


def verify_policy_json(policy_path: Path, app_name: str) -> bool:
    """policy.json 검증"""
    print(f"\n🔍 policy.json 검증 중... ({policy_path})")
    
    if not policy_path.exists():
        print(f"  ❌ policy.json 파일이 없습니다")
        return False
    
    try:
        with open(policy_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ JSON 로드 실패: {e}")
        return False
    
    errors = []
    
    # 필수 섹션 확인
    if 'identity' not in data:
        errors.append("identity 섹션이 없습니다")
    else:
        if data['identity'].get('app_name') != app_name:
            errors.append(f"app_name이 '{app_name}'이 아닙니다: {data['identity'].get('app_name')}")
    
    if 'policy' not in data:
        errors.append("policy 섹션이 없습니다")
    else:
        # 체험판 크레딧 확인
        trial = data['policy'].get('trial_credits')
        if trial != 10000:
            errors.append(f"trial_credits가 10000이 아닙니다: {trial}")
        
        # 작업당 크레딧 확인
        per_work = data['policy'].get('credit_per_work')
        if per_work is None:
            errors.append("credit_per_work가 없습니다")
    
    # 불필요한 섹션 확인
    forbidden = ['app_config', 'runtime_config', 'build_count', 'last_updated', 'full_version']
    for key in forbidden:
        if key in data:
            errors.append(f"불필요한 키가 있습니다: {key}")
    
    if errors:
        print(f"  ❌ policy.json 검증 실패:")
        for err in errors:
            print(f"     - {err}")
        return False
    
    print(f"  ✅ policy.json 검증 통과")
    print(f"     - trial_credits: {data['policy']['trial_credits']}")
    print(f"     - credit_per_work: {data['policy']['credit_per_work']}")
    return True


def verify_settings_json(settings_path: Path, check_version: bool = True) -> bool:
    """settings.json 검증"""
    print(f"\n🔍 settings.json 검증 중... ({settings_path})")
    
    if not settings_path.exists():
        print(f"  ❌ settings.json 파일이 없습니다")
        return False
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ JSON 로드 실패: {e}")
        return False
    
    errors = []
    warnings = []
    
    # runtime_config 섹션 확인
    if 'runtime_config' not in data:
        errors.append("runtime_config 섹션이 없습니다")
    else:
        rc = data['runtime_config']
        
        # run_mode 확인
        if rc.get('run_mode') != 'release':
            errors.append(f"run_mode가 'release'가 아닙니다: {rc.get('run_mode')}")
        
        # 버전 정보 확인 (빌드 후에만)
        if check_version:
            if 'full_version' not in rc:
                warnings.append("full_version이 없습니다 (빌드 시 주입됨)")
            if 'build_count' not in rc:
                warnings.append("build_count가 없습니다 (빌드 시 주입됨)")
            if 'last_updated' not in rc:
                warnings.append("last_updated가 없습니다 (빌드 시 주입됨)")
    
    # ui_config 섹션 확인
    if 'ui_config' not in data:
        errors.append("ui_config 섹션이 없습니다")
    else:
        ui = data['ui_config']
        
        # 사용자 경로 초기화 확인 (빌드 후에만)
        if check_version:
            folder = ui.get('last_selected_folder', None)
            if folder and folder != "":
                errors.append(f"last_selected_folder가 초기화되지 않았습니다: {folder}")
            
            geom = ui.get('window_geometry_override', None)
            if geom and geom != "":
                errors.append(f"window_geometry_override가 초기화되지 않았습니다: {geom}")
    
    # 불필요한 섹션 확인
    forbidden = ['app_info', 'app_config']
    for key in forbidden:
        if key in data:
            errors.append(f"불필요한 섹션이 있습니다: {key}")
    
    if errors:
        print(f"  ❌ settings.json 검증 실패:")
        for err in errors:
            print(f"     - {err}")
        return False
    
    if warnings:
        print(f"  ⚠️ settings.json 경고:")
        for warn in warnings:
            print(f"     - {warn}")
    
    print(f"  ✅ settings.json 검증 통과")
    if 'runtime_config' in data:
        rc = data['runtime_config']
        print(f"     - run_mode: {rc.get('run_mode')}")
        if 'full_version' in rc:
            print(f"     - full_version: {rc.get('full_version')}")
        if 'build_count' in rc:
            print(f"     - build_count: {rc.get('build_count')}")
    return True


def verify_credit_history_json(credit_path: Path) -> bool:
    """credit_history.json은 번들에 없어야 함"""
    print(f"\n🔍 credit_history.json 검증 중...")
    
    if credit_path.exists():
        print(f"  ❌ credit_history.json이 번들에 포함되어 있습니다: {credit_path}")
        print(f"     배포 시 하드웨어 정보가 유출될 수 있습니다!")
        return False
    
    print(f"  ✅ credit_history.json 미포함 확인 (정상)")
    return True


def verify_bundle(bundle_dir: Path, app_name: str, check_version: bool = True) -> bool:
    """전체 번들 검증"""
    print(f"\n{'='*60}")
    print(f"📦 배포 번들 검증 시작: {app_name}")
    print(f"{'='*60}")
    print(f"번들 경로: {bundle_dir}")
    
    wf_rpa = bundle_dir / "_internal" / ".wf_rpa"
    if not wf_rpa.exists():
        print(f"\n❌ .wf_rpa 디렉토리가 없습니다: {wf_rpa}")
        return False
    
    app_dir = wf_rpa / app_name
    if not app_dir.exists():
        print(f"\n❌ 앱 디렉토리가 없습니다: {app_dir}")
        return False
    
    # 검증 수행
    results = []
    results.append(verify_policy_json(app_dir / "policy.json", app_name))
    results.append(verify_settings_json(app_dir / "settings.json", check_version))
    results.append(verify_credit_history_json(app_dir / "credit_history.json"))
    
    # 전역 설정 확인
    print(f"\n🔍 전역 설정 확인...")
    wf_config = wf_rpa / "wf_rpa_config.json"
    if wf_config.exists():
        print(f"  ✅ wf_rpa_config.json 존재")
    else:
        print(f"  ⚠️ wf_rpa_config.json 없음")
    
    # Google credentials 확인
    silver_files = list(wf_rpa.glob('.silver-argon*.json'))
    if silver_files:
        print(f"  ✅ Google credentials 존재: {silver_files[0].name}")
    else:
        print(f"  ⚠️ Google credentials 없음")
    
    # 최종 결과
    print(f"\n{'='*60}")
    if all(results):
        print(f"🎉 배포 번들 검증 성공!")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"❌ 배포 번들 검증 실패!")
        print(f"{'='*60}\n")
        return False


def verify_source_config(config_dir: Path, app_name: str) -> bool:
    """소스 config 디렉토리 검증 (빌드 전)"""
    print(f"\n{'='*60}")
    print(f"📁 소스 설정 검증: {app_name}")
    print(f"{'='*60}")
    print(f"설정 경로: {config_dir}")
    
    app_config = config_dir / app_name
    if not app_config.exists():
        print(f"\n❌ 앱 설정 디렉토리가 없습니다: {app_config}")
        return False
    
    # 검증 수행 (버전 체크 안함)
    results = []
    results.append(verify_policy_json(app_config / "policy.json", app_name))
    results.append(verify_settings_json(app_config / "settings.json", check_version=False))
    
    # 최종 결과
    print(f"\n{'='*60}")
    if all(results):
        print(f"✅ 소스 설정 검증 성공!")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"❌ 소스 설정 검증 실패!")
        print(f"{'='*60}\n")
        return False


if __name__ == '__main__':
    """
    사용법:
    1. 빌드 전 소스 검증:
       python verify_bundle.py source bom_exporter
    
    2. 빌드 후 번들 검증:
       python verify_bundle.py bundle bom_exporter
    """
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python verify_bundle.py source <app_name>")
        print("  python verify_bundle.py bundle <app_name>")
        print("\nExamples:")
        print("  python verify_bundle.py source bom_exporter")
        print("  python verify_bundle.py bundle bom_exporter")
        sys.exit(1)
    
    mode = sys.argv[1]
    app_name = sys.argv[2]
    
    # 현재 스크립트 위치에서 경로 계산
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parent  # 10.rpa
    
    if mode == 'source':
        # 소스 config 검증
        app_dir = workspace / '30.apps' / app_name
        if not app_dir.exists():
            # 50.data 디렉토리 시도
            app_dir = workspace / '50.data' / app_name
        
        config_dir = app_dir / 'config'
        
        success = verify_source_config(config_dir, app_name)
    
    elif mode == 'bundle':
        # 빌드 후 번들 검증
        app_dir = workspace / '30.apps' / app_name
        if not app_dir.exists():
            # 50.data 디렉토리 시도
            app_dir = workspace / '50.data' / app_name
        
        bundle_dir = app_dir / 'dist' / app_name
        
        success = verify_bundle(bundle_dir, app_name, check_version=True)
    
    else:
        print(f"❌ 알 수 없는 모드: {mode}")
        print("   'source' 또는 'bundle'을 사용하세요")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
