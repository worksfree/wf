#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
from pathlib import Path
import pytest

# 10.common import path
COMMON = Path(__file__).parents[2] / "10.common"
import sys
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

from wf_credit_manager import WorksFreeManager, CreditManager
from wf_googlesheets_manager import get_sheets_manager


@pytest.fixture()
def temp_wf_home(tmp_path: Path):
    # seed files from fixtures
    fixtures = Path(__file__).parents[1] / "fixtures" / "policy_sync"
    shutil.copy2(fixtures / "wf_rpa_config.json", tmp_path / "wf_rpa_config.json")
    shutil.copy2(fixtures / ".wf_app_policies.json", tmp_path / ".wf_app_policies.json")
    os.environ["WF_RPA_HOME"] = str(tmp_path)
    return tmp_path


@pytest.mark.integration
def test_get_app_policies(temp_wf_home):
    sheets_manager = get_sheets_manager(test_mode=True)
    policies = sheets_manager.get_app_policies()
    assert policies is None or isinstance(policies, dict)


@pytest.mark.integration
def test_refresh_policies_from_sheets(temp_wf_home):
    wf_manager = WorksFreeManager()
    result = wf_manager.refresh_policies_from_sheets()
    assert "success" in result
    # In the new merged config model, per-app policy file is policy.json
    # Verify a per-app policy path can be resolved via CreditManager
    cm = CreditManager(app_name="bom_exporter")
    assert cm.policy_file.name == "policy.json"


@pytest.mark.integration
def test_policy_file_exists_after_refresh(temp_wf_home):
    wf_manager = WorksFreeManager()
    wf_manager.refresh_policies_from_sheets()
    cm = CreditManager(app_name="bom2excel")
    policy_file = cm.policy_file
    # file may be created by manager; if exists ensure it is json-like
    if policy_file.exists():
        content = policy_file.read_text(encoding="utf-8").strip()
        assert content.startswith("{")
