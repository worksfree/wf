#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""save_policies 디버그 테스트"""

import os
import sys
from pathlib import Path

# 10.common을 sys.path에 추가
common_path = Path(__file__).parent / "10.common"
sys.path.insert(0, str(common_path))

from wf_credit_manager import WorksFreeManager, set_logger
import logging

# 로거 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("wf_creditmanager_simple")
set_logger(logger)

# 테스트
wf_manager = WorksFreeManager()

print(f"manager: {wf_manager}")
print(f"is_dev_mode: {wf_manager.is_dev_mode}")

# 테스트 정책
test_policies = {
    "test_app": {"default_credit": 1000, "credit_per_work": 50, "requires_registration": True}
}

print("\n정책 저장 시도...")
result = wf_manager.save_policies(test_policies, source="test")
print(f"저장 결과: {result}")

if result:
    print("\n저장된 정책 로드...")
    loaded = wf_manager.load_policies()
    print(f"로드된 정책: {loaded}")
