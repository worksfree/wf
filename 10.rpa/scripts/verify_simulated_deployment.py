"""
시뮬레이션된 배포판 검증 스크립트
"""

import json
import sys
from pathlib import Path

def verify_simulated_deployment(app_name: str):
    """시뮬레이션된 배포판 검증"""
    
    # 경로 설정
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parent
    
    # 앱 디렉토리 찾기
    app_dir = workspace / '30.apps' / app_name
    if not app_dir.exists():
        app_dir = workspace / '50.data' / app_name
    
    sim_dir = app_dir / 'deployment_simulation'
    sim_wf_rpa = sim_dir / '.wf_rpa'
    sim_app_dir = sim_wf_rpa / app_name
    
    if not sim_app_dir.exists():
        print(f"❌ 시뮬레이션 디렉토리가 없습니다: {sim_app_dir}")
        print(f"먼저 'python scripts/simulate_deployment.py {app_name}'를 실행하세요.")
        return False
    
    print(f"\n{'='*60}")
    print(f"🔍 배포판 JSON 검증: {app_name}")
    print(f"{'='*60}")
    print(f"검증 경로: {sim_app_dir}\n")
    
    all_passed = True
    
    # 1. policy.json 검증
    print("🔵 1. policy.json 검증")
    policy_file = sim_app_dir / 'policy.json'
    
    if not policy_file.exists():
        print("  ❌ policy.json 파일이 없습니다")
        all_passed = False
    else:
        with open(policy_file, 'r', encoding='utf-8') as f:
            policy = json.load(f)
        
        errors = []
        
        # 필수 섹션 확인
        if 'identity' not in policy:
            errors.append("identity 섹션이 없습니다")
        if 'policy' not in policy:
            errors.append("policy 섹션이 없습니다")
        
        # 불필요한 키 확인
        forbidden = ['app_config', 'build_count', 'last_updated', 'full_version', 'version']
        for key in forbidden:
            if key in policy:
                errors.append(f"불필요한 키가 있습니다: {key}")
        
        # policy 내용 확인
        if 'policy' in policy:
            if 'trial_credits' not in policy['policy']:
                errors.append("trial_credits가 없습니다")
            if 'credit_per_work' not in policy['policy']:
                errors.append("credit_per_work가 없습니다")
        
        if errors:
            print("  ❌ 검증 실패:")
            for err in errors:
                print(f"     - {err}")
            all_passed = False
        else:
            print("  ✅ 검증 통과")
            print(f"     - trial_credits: {policy['policy']['trial_credits']}")
            print(f"     - credit_per_work: {policy['policy']['credit_per_work']}")
    
    # 2. settings.json 검증
    print("\n🟢 2. settings.json 검증")
    settings_file = sim_app_dir / 'settings.json'
    
    if not settings_file.exists():
        print("  ❌ settings.json 파일이 없습니다")
        all_passed = False
    else:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        errors = []
        
        # runtime_config 확인
        if 'runtime_config' not in settings:
            errors.append("runtime_config 섹션이 없습니다")
        else:
            rc = settings['runtime_config']
            
            # run_mode 확인
            if rc.get('run_mode') != 'release':
                errors.append(f"run_mode가 'release'가 아닙니다: {rc.get('run_mode')}")
            
            # 버전 정보 확인
            if 'full_version' not in rc:
                errors.append("full_version이 없습니다")
            if 'build_count' not in rc:
                errors.append("build_count가 없습니다")
            if 'last_updated' not in rc:
                errors.append("last_updated가 없습니다")
        
        # ui_config 확인
        if 'ui_config' not in settings:
            errors.append("ui_config 섹션이 없습니다")
        else:
            ui = settings['ui_config']
            
            # 경로 초기화 확인
            folder = ui.get('last_selected_folder', None)
            if folder != "":
                errors.append(f"last_selected_folder가 초기화되지 않았습니다: '{folder}'")
            
            geom = ui.get('window_geometry_override', None)
            if geom != "":
                errors.append(f"window_geometry_override가 초기화되지 않았습니다: '{geom}'")
        
        # 불필요한 섹션 확인
        forbidden = ['app_info', 'app_config']
        for key in forbidden:
            if key in settings:
                errors.append(f"불필요한 섹션이 있습니다: {key}")
        
        if errors:
            print("  ❌ 검증 실패:")
            for err in errors:
                print(f"     - {err}")
            all_passed = False
        else:
            print("  ✅ 검증 통과")
            if 'runtime_config' in settings:
                rc = settings['runtime_config']
                print(f"     - run_mode: {rc.get('run_mode')}")
                print(f"     - full_version: {rc.get('full_version')}")
                print(f"     - build_count: {rc.get('build_count')}")
                print(f"     - last_updated: {rc.get('last_updated')}")
            if 'ui_config' in settings:
                ui = settings['ui_config']
                print(f"     - last_selected_folder: '{ui.get('last_selected_folder')}'")
                print(f"     - window_geometry_override: '{ui.get('window_geometry_override')}'")
    
    # 3. credit_history.json 확인
    print("\n🔴 3. credit_history.json 확인")
    credit_file = sim_app_dir / 'credit_history.json'
    
    if credit_file.exists():
        print("  ❌ credit_history.json이 있습니다 (배포 시 포함되면 안됨)")
        all_passed = False
    else:
        print("  ✅ credit_history.json 미포함 확인 (정상)")
    
    # 4. 파일 크기 확인
    print("\n📊 4. 파일 크기 확인")
    for file in sim_app_dir.rglob('*.json'):
        size = file.stat().st_size
        rel_path = file.relative_to(sim_app_dir)
        print(f"  - {rel_path}: {size:,} bytes")
        
        # 비정상적으로 큰 파일 체크
        if size > 100_000:  # 100KB
            print(f"    ⚠️ 파일이 비정상적으로 큽니다")
    
    # 최종 결과
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 배포판 JSON 검증 성공!")
        print("{'='*60}\n")
        
        print("✅ 모든 검증 항목 통과:")
        print("  - policy.json: identity + policy만 포함")
        print("  - settings.json: run_mode=release, 버전 주입됨, 경로 초기화됨")
        print("  - credit_history.json: 미포함")
        print("  - 불필요한 키/섹션: 없음")
        
        print("\n📦 배포 준비 완료!")
        print(f"시뮬레이션 디렉토리: {sim_dir}")
        
        return True
    else:
        print("❌ 배포판 JSON 검증 실패!")
        print(f"{'='*60}\n")
        print("위의 오류를 수정해야 합니다.")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_simulated_deployment.py <app_name>")
        print("Example: python verify_simulated_deployment.py bom_exporter")
        sys.exit(1)
    
    app_name = sys.argv[1]
    success = verify_simulated_deployment(app_name)
    sys.exit(0 if success else 1)
