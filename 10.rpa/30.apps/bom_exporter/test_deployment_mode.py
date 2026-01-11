# -*- coding: utf-8 -*-
"""
배포 모드 설정 파일 초기화 테스트
"""

import json
import os
from pathlib import Path

print("=" * 60)
print("배포 모드 설정 파일 테스트")
print("=" * 60)

# 배포 환경 시뮬레이션 (config 폴더가 없는 상황)
# 실제로는 빌드된 exe에서는 config 폴더가 없음
deployment_settings_file = Path.home() / ".wf_rpa" / "bom_exporter" / "settings.json"

print(f"\n📁 배포 설정 파일 경로: {deployment_settings_file}")
print(f"✅ 파일 존재 여부: {deployment_settings_file.exists()}")

if not deployment_settings_file.exists():
    print("\n❌ 배포 설정 파일이 존재하지 않습니다.")
    print("   앱을 처음 실행하면 자동으로 생성됩니다.")
    
    # 수동으로 초기화 시뮬레이션
    deployment_settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    default_settings = {
        "app_info": {
            "last_updated": "2025-11-25 05:47:00"
        },
        "solidworks": {
            "program_path": "C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\SLDWORKS.exe"
        },
        "app_config": {
            "restart_count": 20,
            "topmost": True,
            "auto_restart": True,
            "speed_mode": "normal",
            "base_wait_time": 60,
            "seconds_per_10mb": 60,
            "include_thumbnail": True
        },
        "ui_config": {
            "last_selected_folder": ""
        }
    }
    
    with open(deployment_settings_file, 'w', encoding='utf-8') as f:
        json.dump(default_settings, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ 설정 파일 생성 완료: {deployment_settings_file}")
else:
    print("\n✅ 배포 설정 파일이 존재합니다.")

# 파일 내용 확인
with open(deployment_settings_file, 'r', encoding='utf-8') as f:
    settings = json.load(f)

print(f"\n📋 설정 파일 내용:")
print(json.dumps(settings, indent=2, ensure_ascii=False))

# 구조 검증
print("\n🔍 구조 검증:")
required_sections = ["app_info", "solidworks", "app_config", "ui_config"]
for section in required_sections:
    if section in settings:
        print(f"  - {section}: ✅")
    else:
        print(f"  - {section}: ❌")

# last_selected_folder 확인
last_folder = settings.get("ui_config", {}).get("last_selected_folder", "")
print(f"\n📂 last_selected_folder: {last_folder if last_folder else '(비어있음)'}")

print("\n" + "=" * 60)
print("테스트 완료 ✅")
print("=" * 60)
