# -*- coding: utf-8 -*-
"""
구글 시트 설정 테스트
wf_rpa_config.json에서 구글 시트 ID 로드 검증
"""

import sys
from pathlib import Path

# 공통 경로 추가
common_path = Path(__file__).resolve().parents[2] / "10.common"
if str(common_path) not in sys.path:
    sys.path.insert(0, str(common_path))

from wf_googlesheets_manager import get_sheets_config

print("=" * 60)
print("구글 시트 설정 로드 테스트")
print("=" * 60)

try:
    # wf_rpa_config.json에서 설정 로드
    config = get_sheets_config()
    
    print("\n✅ 설정 로드 성공!\n")
    print(f"📋 SHEET_ID_PROD: {config['SHEET_ID_PROD']}")
    print(f"📋 SHEET_ID_TEST: {config['SHEET_ID_TEST']}")
    print(f"📋 SHEET_NAME_REGISTRATIONS: {config['SHEET_NAME_REGISTRATIONS']}")
    print(f"📋 SCOPE: {config['SCOPE']}")
    
    # 검증
    assert config['SHEET_ID_PROD'] == "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"
    assert config['SHEET_ID_TEST'] == "1bUqpV1vSGwsVeWav-6enZUzaKBTJdxX5eZ737lNh6Ww"
    assert config['SHEET_NAME_REGISTRATIONS'] == "registrations"
    assert len(config['SCOPE']) == 2
    
    print("\n✅ 모든 검증 통과!")
    
except FileNotFoundError as e:
    print(f"\n❌ 파일을 찾을 수 없습니다:\n{e}")
except KeyError as e:
    print(f"\n❌ 필수 설정이 없습니다:\n{e}")
except Exception as e:
    print(f"\n❌ 오류 발생:\n{e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
