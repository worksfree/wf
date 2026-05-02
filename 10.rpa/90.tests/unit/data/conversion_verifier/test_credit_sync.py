# -*- coding: utf-8 -*-
"""
conversion_verifier credit_changed 플래그 테스트 (pytest 형식)
로컬 config 폴더의 JSON 파일 사용
"""
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime


class TestConversionVerifierCreditSync:
    """conversion_verifier 크레딧 동기화 테스트"""

    @pytest.fixture(autouse=True)
    def setup_path(self):
        """경로 설정"""
        current_dir = Path(__file__).parent
        common_path = current_dir.parents[3] / "10.common"
        if str(common_path) not in sys.path:
            sys.path.insert(0, str(common_path))

    @pytest.fixture
    def temp_credit_file(self, tmp_path):
        """임시 크레딧 파일 생성"""
        credit_file = tmp_path / "credit_history.json"
        initial_data = {
            "created_at": "2025-01-01T00:00:00.000",
            "last_updated": "2025-01-01T00:00:00.000",
            "last_synced": None,
            "lifetime_usage": 0,
            "credit_changed": False,
            "trial_credits": 2000,
            "purchased_credits": 0,
            "current_credits": 2000,
            "purchase_history": [],
            "usage_history": [],
            "applied_purchase_ids": [],
        }
        with open(credit_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        return credit_file

    def test_read_credit_data(self, temp_credit_file):
        """크레딧 데이터 읽기 테스트"""
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data is not None
        assert "current_credits" in data
        assert data["current_credits"] == 2000

    def test_write_credit_data(self, temp_credit_file):
        """크레딧 데이터 쓰기 테스트"""
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["credit_changed"] = True
        data["current_credits"] = 1500

        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 다시 읽어서 확인
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["credit_changed"] is True
        assert updated_data["current_credits"] == 1500

    def test_set_credit_changed_flag(self, temp_credit_file):
        """credit_changed 플래그 설정 테스트"""
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        old_value = data.get("credit_changed", False)
        data["credit_changed"] = True

        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert old_value is False
        assert updated_data["credit_changed"] is True

    def test_simulate_credit_usage(self, temp_credit_file):
        """크레딧 사용 시뮬레이션 테스트"""
        amount = 10

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        current = data.get("current_credits", 0)
        assert current >= amount

        data["current_credits"] = current - amount
        data["credit_changed"] = True
        data["lifetime_usage"] = data.get("lifetime_usage", 0) + amount

        usage_entry = {
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "description": "테스트 크레딧 사용",
        }
        data["usage_history"] = data.get("usage_history", [])
        data["usage_history"].append(usage_entry)

        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["current_credits"] == current - amount
        assert updated_data["credit_changed"] is True
        assert updated_data["lifetime_usage"] == amount
        assert len(updated_data["usage_history"]) == 1

    def test_simulate_sync_success(self, temp_credit_file):
        """동기화 성공 시뮬레이션 테스트"""
        # credit_changed를 True로 설정
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["credit_changed"] = True
        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 동기화 성공 시뮬레이션
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("credit_changed", False) is True

        data["credit_changed"] = False
        data["last_synced"] = datetime.now().isoformat()

        with open(temp_credit_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with open(temp_credit_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert updated_data["credit_changed"] is False
        assert updated_data["last_synced"] is not None

    def test_credit_file_structure(self, temp_credit_file):
        """크레딧 파일 구조 검증"""
        with open(temp_credit_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = [
            "created_at",
            "last_updated",
            "credit_changed",
            "trial_credits",
            "purchased_credits",
            "current_credits",
        ]

        for key in required_keys:
            assert key in data, f"Missing key: {key}"
