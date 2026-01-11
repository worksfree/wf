"""
배포판 JSON 시뮬레이션 스크립트

spec 파일의 prepare_user_configs 로직을 시뮬레이션하여
배포판에 포함될 JSON 파일들을 생성합니다.
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

def simulate_deployment(app_name: str):
    """배포판 JSON 시뮬레이션"""
    
    # 경로 설정
    script_dir = Path(__file__).resolve().parent
    workspace = script_dir.parent
    
    # 앱 디렉토리 찾기
    app_dir = workspace / '30.apps' / app_name
    if not app_dir.exists():
        app_dir = workspace / '50.data' / app_name
    
    if not app_dir.exists():
        print(f"❌ 앱을 찾을 수 없습니다: {app_name}")
        return False
    
    # 시뮬레이션 출력 디렉토리
    sim_dir = app_dir / 'deployment_simulation'
    sim_wf_rpa = sim_dir / '.wf_rpa'
    sim_app_dir = sim_wf_rpa / app_name
    
    # 기존 시뮬레이션 디렉토리 삭제
    if sim_dir.exists():
        shutil.rmtree(sim_dir)
    
    sim_app_dir.mkdir(parents=True)
    
    print(f"\n{'='*60}")
    print(f"📦 배포판 JSON 시뮬레이션: {app_name}")
    print(f"{'='*60}")
    print(f"출력 경로: {sim_dir}")
    
    # 소스 config 경로
    config_dir = app_dir / 'config'
    app_config_dir = config_dir / app_name
    
    # 1. policy.json 처리 (그대로 복사)
    print(f"\n🔵 1. policy.json 처리")
    policy_src = app_config_dir / 'policy.json'
    if policy_src.exists():
        policy_dst = sim_app_dir / 'policy.json'
        shutil.copy2(policy_src, policy_dst)
        print(f"  ✅ policy.json 복사 완료")
        print(f"     소스: {policy_src}")
        print(f"     대상: {policy_dst}")
        
        # 내용 확인
        with open(policy_dst, 'r', encoding='utf-8') as f:
            policy_data = json.load(f)
        print(f"     - trial_credits: {policy_data.get('policy', {}).get('trial_credits')}")
        print(f"     - credit_per_work: {policy_data.get('policy', {}).get('credit_per_work')}")
    else:
        print(f"  ❌ policy.json을 찾을 수 없음: {policy_src}")
        return False
    
    # 2. settings.json 처리 (버전 주입 + 경로 초기화)
    print(f"\n🟢 2. settings.json 처리")
    settings_src = app_config_dir / 'settings.json'
    if settings_src.exists():
        with open(settings_src, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        print(f"  📄 소스 파일 로드 완료: {settings_src}")
        
        # 버전 정보 (시뮬레이션용 더미 값)
        APP_VERSION_FULL = "0.9.2.0"  # 시뮬레이션용
        BUILD_COUNT = 999  # 시뮬레이션용
        
        # runtime_config 처리
        if 'runtime_config' not in settings_data:
            settings_data['runtime_config'] = {}
        
        # 버전 정보 주입
        settings_data['runtime_config']['run_mode'] = 'release'  # 강제 설정
        settings_data['runtime_config']['full_version'] = f"v{APP_VERSION_FULL}"
        settings_data['runtime_config']['build_count'] = BUILD_COUNT
        settings_data['runtime_config']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"  ⚙️  버전 정보 주입:")
        print(f"     - run_mode: {settings_data['runtime_config']['run_mode']}")
        print(f"     - full_version: {settings_data['runtime_config']['full_version']}")
        print(f"     - build_count: {settings_data['runtime_config']['build_count']}")
        print(f"     - last_updated: {settings_data['runtime_config']['last_updated']}")
        
        # ui_config 경로 초기화
        if 'ui_config' not in settings_data:
            settings_data['ui_config'] = {}
        
        old_folder = settings_data['ui_config'].get('last_selected_folder', '')
        old_geom = settings_data['ui_config'].get('window_geometry_override', '')
        
        settings_data['ui_config']['last_selected_folder'] = ""
        settings_data['ui_config']['window_geometry_override'] = ""
        
        print(f"  🧹 사용자 경로 초기화:")
        print(f"     - last_selected_folder: '{old_folder}' → ''")
        print(f"     - window_geometry_override: '{old_geom}' → ''")
        
        # 저장
        settings_dst = sim_app_dir / 'settings.json'
        with open(settings_dst, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ settings.json 생성 완료: {settings_dst}")
    else:
        print(f"  ❌ settings.json을 찾을 수 없음: {settings_src}")
        return False
    
    # 3. credit_history.json 확인 (있으면 안됨)
    print(f"\n🔴 3. credit_history.json 확인")
    credit_file = sim_app_dir / 'credit_history.json'
    if credit_file.exists():
        print(f"  ❌ credit_history.json이 생성되었습니다 (배포 시 포함되면 안됨)")
        return False
    else:
        print(f"  ✅ credit_history.json 미포함 확인 (정상)")
    
    # 4. 생성된 파일 목록
    print(f"\n📁 생성된 파일 목록:")
    for file in sim_app_dir.rglob('*'):
        if file.is_file():
            rel_path = file.relative_to(sim_dir)
            size = file.stat().st_size
            print(f"  - {rel_path} ({size:,} bytes)")
    
    # 5. JSON 내용 출력
    print(f"\n📋 생성된 JSON 내용:")
    
    print(f"\n  ┌─ policy.json ─────────────────────────────────")
    with open(policy_dst, 'r', encoding='utf-8') as f:
        policy_content = f.read()
    for line in policy_content.split('\n')[:20]:  # 처음 20줄만
        print(f"  │ {line}")
    print(f"  └───────────────────────────────────────────────")
    
    print(f"\n  ┌─ settings.json ───────────────────────────────")
    with open(settings_dst, 'r', encoding='utf-8') as f:
        settings_content = f.read()
    for line in settings_content.split('\n')[:30]:  # 처음 30줄만
        print(f"  │ {line}")
    print(f"  └───────────────────────────────────────────────")
    
    print(f"\n{'='*60}")
    print(f"✅ 시뮬레이션 완료!")
    print(f"{'='*60}")
    print(f"\n시뮬레이션 디렉토리: {sim_dir}")
    print(f"검증 명령어:")
    print(f"  python scripts/verify_bundle.py bundle {app_name}")
    print(f"  (단, bundle 대신 시뮬레이션 디렉토리를 직접 지정 필요)\n")
    
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python simulate_deployment.py <app_name>")
        print("Example: python simulate_deployment.py bom_exporter")
        sys.exit(1)
    
    app_name = sys.argv[1]
    success = simulate_deployment(app_name)
    sys.exit(0 if success else 1)
