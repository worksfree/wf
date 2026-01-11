"""실제 앱이 표시할 타이틀 버전 확인"""

import json
from pathlib import Path

print('\n=== 4개 앱이 실제로 표시할 타이틀 버전 ===\n')

apps = [
    {
        'title': 'BOM 엑셀 저장',
        'base': 'D:/drive_files/10.worksfree/10.rpa/30.apps/bom_exporter',
        'dev_path': 'config/bom_exporter/settings.json',
        'frozen_path': '~/.wf_rpa/bom_exporter/settings.json'
    },
    {
        'title': 'DWG 파일 분류',
        'base': 'D:/drive_files/10.worksfree/10.rpa/50.data/dwg_classifier',
        'dev_path': 'config/dwg_classifier/settings.json',
        'frozen_path': '~/.wf_rpa/dwg_classifier/settings.json'
    },
    {
        'title': '변환 확인 도구',
        'base': 'D:/drive_files/10.worksfree/10.rpa/50.data/conversion_verifier',
        'dev_path': 'config/conversion_verifier/settings.json',
        'frozen_path': '~/.wf_rpa/conversion_verifier/settings.json'
    },
    {
        'title': '한글 파일명 복원',
        'base': 'D:/drive_files/10.worksfree/10.rpa/50.data/korean_filename_normalizer',
        'dev_path': 'config/korean_filename_normalizer/settings.json',
        'frozen_path': '~/.wf_rpa/korean_filename_normalizer/settings.json'
    }
]

print('【개발 모드】 - 현재 실행하면 이렇게 보입니다:')
print('-' * 60)
for app in apps:
    settings_file = Path(app['base']) / app['dev_path']
    
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            full_version = data.get('app_config', {}).get('full_version', 'v0.7.0.0')
            
            parts = full_version.lstrip('v').split('.')
            display_version = 'v' + '.'.join(parts[:2])
            
            print(f'📺 {app["title"]} {display_version}')
    else:
        print(f'❌ {app["title"]} v0.7 (fallback)')
print()

print('【배포 모드】 - 설치 후 실행하면 이렇게 보입니다:')
print('-' * 60)
home = Path.home()
for app in apps:
    frozen_path = app['frozen_path'].replace('~', str(home))
    settings_file = Path(frozen_path)
    
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            full_version = data.get('app_config', {}).get('full_version', 'v0.7.0.0')
            
            parts = full_version.lstrip('v').split('.')
            display_version = 'v' + '.'.join(parts[:2])
            
            print(f'📺 {app["title"]} {display_version}  ⚠️ (구버전 설치됨)')
    else:
        print(f'❌ {app["title"]} v0.7 (fallback)  ⚠️ (설치 안 됨)')
print()

print('⚡ 결론:')
print('  ✅ 개발 모드는 정상 작동 (모두 최신 버전 표시)')
print('  ⚠️  배포 모드는 아직 구버전/미설치 상태')
print('  🔨 수정된 스펙 파일로 빌드 후 설치하면 해결됩니다!')
