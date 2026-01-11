#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spec 파일의 번들링 내용을 미리 확인하는 스크립트"""

import sys
import json
import shutil
from pathlib import Path

# spec 파일의 경로 설정 부분만 복사
SPEC_DIR = Path('D:/drive_files/10.worksfree/10.rpa/30.apps/Bom_Exporter')
APP_NAME = 'bom_exporter'

# prepare_user_configs 함수 로직 실행
home_dir = SPEC_DIR / 'build' / 'user_home_bundle'
home_dir.mkdir(parents=True, exist_ok=True)

wf_rpa_dir = home_dir / '.wf_rpa'
app_dir = wf_rpa_dir / APP_NAME

for directory in [wf_rpa_dir, app_dir]:
    directory.mkdir(parents=True, exist_ok=True)

# 1. wf_rpa_config.json 복사
app_config_dir = SPEC_DIR / 'config'
source_config = app_config_dir / 'wf_rpa_config.json'

if source_config.exists():
    shutil.copy2(source_config, wf_rpa_dir / 'wf_rpa_config.json')
    print('✓ wf_rpa_config.json 복사 완료')
    
    # 내용 확인
    with open(wf_rpa_dir / 'wf_rpa_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    has_email = 'email_settings' in config
    print(f'\n📧 email_settings 포함 여부: {has_email}')
    if has_email:
        email = config['email_settings']
        print(f'   - email_from: {email.get("email_from", "없음")}')
        print(f'   - smtp_server: {email.get("smtp_server", "없음")}')
        print(f'   - smtp_port: {email.get("smtp_port", "없음")}')
        print(f'   - enabled: {email.get("enabled", "없음")}')
    
    has_sheets = 'google_sheets' in config
    print(f'\n📊 google_sheets 포함 여부: {has_sheets}')
    if has_sheets:
        sheets = config['google_sheets']
        print(f'   - sheet_id_prod: {sheets.get("sheet_id_prod", "없음")[:20]}...')
        print(f'   - sheet_name_registrations: {sheets.get("sheet_name_registrations", "없음")}')
        print(f'   - scope 개수: {len(sheets.get("scope", []))}')
else:
    print(f'❌ wf_rpa_config.json을 찾을 수 없음: {source_config}')

# 2. settings.json 복사
source_settings = app_config_dir / APP_NAME / 'settings.json'
if source_settings.exists():
    shutil.copy2(source_settings, app_dir / 'settings.json')
    print(f'\n✓ settings.json 복사 완료 (.wf_rpa/{APP_NAME}/settings.json)')
    
    # settings.json 내용 확인
    with open(app_dir / 'settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
    
    if 'runtime_config' in settings:
        app_cfg = settings['runtime_config']
        print(f'   - 버전: {app_cfg.get("full_version", "없음")}')
        print(f'   - 빌드 카운트: {app_cfg.get("build_count", "없음")}')
else:
    print(f'\n❌ settings.json을 찾을 수 없음: {source_settings}')

# 3. Google Credentials 확인
actual_key = app_config_dir / '.silver-argon-445712-a0-4ce021aa64be.json'
if actual_key.exists():
    shutil.copy2(actual_key, wf_rpa_dir / actual_key.name)
    size_kb = actual_key.stat().st_size / 1024
    print(f'\n✓ Google credentials 포함: {actual_key.name} ({size_kb:.1f} KB)')
else:
    print(f'\n❌ Google credentials를 찾을 수 없음: {actual_key}')
    # fallback 체크
    silver_files = list(app_config_dir.glob('.silver-argon*.json'))
    if silver_files:
        print(f'   대신 찾은 파일: {silver_files[0].name}')
        shutil.copy2(silver_files[0], wf_rpa_dir / silver_files[0].name)

# 최종 구조 확인
print(f'\n\n📁 번들링될 파일 구조 (_internal/.wf_rpa/):')
for item in sorted(home_dir.rglob('*')):
    if item.is_file():
        rel_path = item.relative_to(home_dir)
        size_kb = item.stat().st_size / 1024
        print(f'   {rel_path} ({size_kb:.1f} KB)')

print(f'\n✅ 이 구조가 exe 실행 시 사용자 홈 폴더로 복사됩니다.')
print(f'   위치: %USERPROFILE%\\.wf_rpa\\')
