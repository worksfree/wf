# -*- coding: utf-8 -*-
"""
GoogleSheetsManager 설정 로드 테스트
_load_config() 메서드가 wf_rpa_config.json에서 제대로 로드하는지 검증
"""

import sys
from pathlib import Path

# 공통 경로 추가
common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

print("=" * 60)
print("GoogleSheetsManager 설정 로드 테스트")
print("=" * 60)

try:
    from wf_googlesheets_manager import GoogleSheetsManager
    
    # GoogleSheetsManager 인스턴스 생성 (초기화 시 _load_config 호출)
    print("\n📦 GoogleSheetsManager 인스턴스 생성 중...")
    manager = GoogleSheetsManager()
    
    # _load_config() 메서드 직접 호출하여 설정 확인
    config = manager._load_config()
    
    print("\n✅ 설정 로드 성공!\n")
    print(f"📋 SHEET_ID_PROD: {config['SHEET_ID_PROD']}")
    print(f"📋 SHEET_ID_TEST: {config['SHEET_ID_TEST']}")
    print(f"📋 SHEET_NAME_REGISTRATIONS: {config['SHEET_NAME_REGISTRATIONS']}")
    print(f"📋 SCOPE: {config['SCOPE']}")
    print(f"📋 CREDENTIALS_FILE: {config['CREDENTIALS_FILE']}")
    
    # 검증
    assert config['SHEET_ID_PROD'] == "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"
    assert config['SHEET_ID_TEST'] == "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"
    assert config['SHEET_NAME_REGISTRATIONS'] == "registrations"
    assert config['CREDENTIALS_FILE'] == ".silver-argon-445712-a0-4ce021aa64be.json"
    assert len(config['SCOPE']) == 2
    
    print("\n✅ 모든 검증 통과!")
    print("\n💡 GoogleSheetsManager._load_config()가 wf_rpa_config.json에서")
    print("   제대로 설정을 로드하고 있습니다.")
    
except Exception as e:
    print(f"\n❌ 오류 발생:\n{e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
