# -*- coding: utf-8 -*-
"""
통합 설정 파일 테스트 스크립트
bom_exporter settings.json 초기화 검증
"""

import json
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# common 경로 추가
common_path = current_dir.parent.parent / "10.common"
if common_path.exists():
    sys.path.insert(0, str(common_path))

from app_setting_data import get_config

def test_settings_initialization():
    """설정 파일 초기화 테스트"""
    print("=" * 60)
    print("통합 설정 파일 테스트 시작")
    print("=" * 60)
    
    # 1. Config 인스턴스 생성 (자동으로 설정 파일 초기화)
    config = get_config()
    
    print(f"\n📁 설정 파일 경로: {config.settings_file}")
    print(f"✅ 파일 존재 여부: {config.settings_file.exists()}")
    
    if config.settings_file.exists():
        with open(config.settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print("\n📋 설정 파일 내용:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        
        # 구조 검증
        print("\n🔍 구조 검증:")
        required_sections = ["app_info", "solidworks", "app_config", "ui_config"]
        for section in required_sections:
            exists = section in data
            print(f"  - {section}: {'✅' if exists else '❌'}")
        
        # ui_config.last_selected_folder 검증
        last_folder = data.get("ui_config", {}).get("last_selected_folder", "")
        print(f"\n📂 last_selected_folder: {last_folder if last_folder else '(비어있음)'}")
    
    # 2. 메서드 테스트
    print("\n" + "=" * 60)
    print("설정 메서드 테스트")
    print("=" * 60)
    
    # last_selected_folder 가져오기
    current_folder = config.get_last_selected_folder()
    print(f"\n📂 현재 last_selected_folder: {current_folder if current_folder else '(비어있음)'}")
    
    # 테스트 폴더 저장
    test_folder = "D:/test_folder_path"
    print(f"\n💾 테스트 폴더 저장 시도: {test_folder}")
    result = config.update_ui_last_folder(test_folder)
    print(f"   결과: {'✅ 성공' if result else '❌ 실패'}")
    
    if result:
        # 다시 읽어서 확인
        updated_folder = config.get_last_selected_folder()
        print(f"   확인: {updated_folder}")
        print(f"   일치: {'✅' if updated_folder == test_folder else '❌'}")
    
    # 3. 앱 설정 값 확인
    print("\n" + "=" * 60)
    print("앱 설정 값 확인")
    print("=" * 60)
    
    print(f"\n⚙️ restart_count: {config.restart_count}")
    print(f"⚙️ base_wait_time: {config.base_wait_time}")
    print(f"⚙️ seconds_per_10mb: {config.seconds_per_10mb}")
    print(f"⚙️ program_path: {config.program_path}")
    
    print("\n" + "=" * 60)
    print("테스트 완료 ✅")
    print("=" * 60)

if __name__ == "__main__":
    test_settings_initialization()
