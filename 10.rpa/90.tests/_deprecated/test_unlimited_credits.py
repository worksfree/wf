"""
무제한 크레딧 시나리오 테스트 (수정 버전)
- 무료 앱: default_credit = -1, 등록 필수
- 영구 라이선스: purchased_credits = -1
- 일반 앱: 무료 2000 → 충전 크레딧 순차 사용
"""

import sys
import os
import json
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "10.common"))

from wf_credit_manager import CreditManager, WorksFreeManager


class UnlimitedCreditTester:
    def __init__(self):
        self.test_results = []
        self.backup_dir = None
        self.test_user_email = "unlimited.test@worksfree.co.kr"

    def log_test(self, test_name, success, details):
        """테스트 결과를 기록하는 메서드 (로깅 기능 추가)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = "성공" if success else "실패"
        log_entry = f"{timestamp} - {test_name}: {result} - {details}"

        # 콘솔 출력
        print(log_entry)

        # 파일에 기록
        if self.backup_dir:
            log_file = os.path.join(self.backup_dir, "test_results.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")

        # 결과 저장
        self.test_results.append(
            {"test_name": test_name, "success": success, "details": details, "timestamp": timestamp}
        )

    def backup_credit_data(self):
        """크레딧 데이터 백업"""
        try:
            wf_manager = WorksFreeManager()
            config = wf_manager.load_config()

            if "app_policies" not in config:
                config["app_policies"] = {}

            # 모든 앱 정책에 대해 크레딧 데이터 백업
            for app_name in config["app_policies"]:
                credit_manager = CreditManager(app_name=app_name, user_email=self.test_user_email)
                credit_data = credit_manager._load_credit_data()

                # 백업 디렉토리 생성
                if not self.backup_dir:
                    os.makedirs("backup", exist_ok=True)
                    self.backup_dir = "backup"

                # 백업 파일 경로
                backup_file = os.path.join(self.backup_dir, f"{app_name}_credit_backup.json")

                # 백업 파일에 크레딧 데이터 저장
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(credit_data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"백업 오류: {e}")

    def restore_credit_data(self):
        """크레딧 데이터 복원"""
        try:
            if not self.backup_dir:
                print("복원할 백업 데이터가 없습니다.")
                return

            # 백업 디렉토리의 모든 파일에 대해 복원
            for backup_file in os.listdir(self.backup_dir):
                if backup_file.endswith("_credit_backup.json"):
                    app_name = backup_file.split("_")[0]
                    file_path = os.path.join(self.backup_dir, backup_file)

                    # 백업 파일에서 크레딧 데이터 로드
                    with open(file_path, "r", encoding="utf-8") as f:
                        credit_data = json.load(f)

                        # 크레딧 데이터 복원
                        credit_manager = CreditManager(
                            app_name=app_name, user_email=self.test_user_email
                        )
                        credit_manager._save_credit_data(credit_data)

        except Exception as e:
            print(f"복원 오류: {e}")

    def test_1_free_app_registered_user(self):
        """테스트 1: 무료 앱 - 등록된 사용자"""
        print("🧪 테스트 1: 무료 앱 (default_credit = -1, 등록 필수)")

        try:
            # app_policies에 무료 앱 정책 추가
            wf_manager = WorksFreeManager()
            config = wf_manager.load_config()

            if "app_policies" not in config:
                config["app_policies"] = {}

            config["app_policies"]["free_test_app"] = {
                "default_credit": -1,  # 무료 앱
                "credit_per_use": 0,
                "requires_registration": True,
            }
            wf_manager.save_config(config)

            # 기존 크레딧 파일이 있으면 삭제하여 정책을 재적용하도록 함
            try:
                user_home = os.path.expanduser("~")
                app_dir = os.path.join(user_home, ".wf_rpa", "free_test_app")
                credit_file = os.path.join(app_dir, ".free_test_app_credits.json")
                if os.path.exists(credit_file):
                    os.remove(credit_file)
            except Exception:
                pass

            # 크레딧 매니저 생성 (등록된 사용자)
            credit_manager = CreditManager(
                app_name="free_test_app", user_email=self.test_user_email
            )

            # 크레딧 상태 확인
            status = credit_manager.get_credit_status()
            is_unlimited = status.get("remaining_credits") == -1
            credit_type = status.get("credit_type")

            # 대량 사용 테스트 (크레딧 차감 없어야 함)
            usage_count = 50
            deduct_results = []

            with patch.object(credit_manager, "check_and_sync_credits") as mock_sync:
                for i in range(usage_count):
                    result = credit_manager.deduct_credits_by_policy(1, f"무료 앱 사용 {i+1}")
                    deduct_results.append(result.get("success", False))

                # sync가 호출되지 않았는지 확인
                sync_not_called = mock_sync.call_count == 0

            # 사용 후에도 여전히 무제한
            final_status = credit_manager.get_credit_status()
            still_unlimited = final_status.get("remaining_credits") == -1

            # 사용 로그는 기록되었는지 확인
            credit_data_after = credit_manager._load_credit_data()
            usage_history = credit_data_after.get("usage_history", [])
            logs_recorded = len(usage_history) >= usage_count

            success = (
                is_unlimited
                and all(deduct_results)
                and sync_not_called
                and still_unlimited
                and logs_recorded
                and credit_type == "free"
            )

            details = (
                f"무제한: {is_unlimited}, 사용 성공: {sum(deduct_results)}/{usage_count}, "
                f"sync 미호출: {sync_not_called}, 사용 로그: {len(usage_history)}건, 타입: {credit_type}"
            )

            self.log_test("무료 앱 (등록된 사용자)", success, details)
            return success

        except Exception as e:
            self.log_test("무료 앱 (등록된 사용자)", False, f"오류: {e}")
            return False

    def test_2_normal_app_credit_order(self):
        """테스트 2: 일반 앱 - 무료 → 충전 크레딧 순차 사용"""
        print("🧪 테스트 2: 일반 앱 크레딧 차감 순서 (무료 → 충전)")

        try:
            credit_manager = CreditManager(
                app_name="normal_test_app", user_email=self.test_user_email
            )

            # 초기 상태: 무료 100, 충전 200
            credit_data = credit_manager._load_credit_data()
            credit_data["trial_credits"] = 100
            credit_data["purchased_credits"] = 200
            credit_manager._save_credit_data(credit_data)

            initial_status = credit_manager.get_credit_status()
            initial_trial = initial_status.get("trial_credits")
            initial_purchased = initial_status.get("purchased_credits")

            # 50개 사용 (무료 크레딧부터 차감)
            for i in range(50):
                credit_manager.deduct_credits_by_policy(1, f"일반 사용 {i+1}")

            after_50_status = credit_manager.get_credit_status()
            after_50_trial = after_50_status.get("trial_credits")
            after_50_purchased = after_50_status.get("purchased_credits")

            # 무료 크레딧만 50 차감, 충전 크레딧은 그대로
            trial_deducted_correctly = after_50_trial == initial_trial - 50
            purchased_unchanged = after_50_purchased == initial_purchased

            # 추가 60개 사용 (무료 50 소진 후 충전 크레딧 10 사용)
            for i in range(60):
                credit_manager.deduct_credits_by_policy(1, f"추가 사용 {i+1}")

            final_status = credit_manager.get_credit_status()
            final_trial = final_status.get("trial_credits")
            final_purchased = final_status.get("purchased_credits")

            # 무료 크레딧 0, 충전 크레딧 190
            trial_depleted = final_trial == 0
            purchased_correct = final_purchased == initial_purchased - 10

            success = (
                trial_deducted_correctly
                and purchased_unchanged
                and trial_depleted
                and purchased_correct
            )

            details = (
                f"무료 차감: {trial_deducted_correctly} (100→50), "
                f"충전 유지: {purchased_unchanged} (200), "
                f"무료 소진: {trial_depleted} (0), "
                f"충전 차감: {purchased_correct} (200→190)"
            )

            self.log_test("일반 앱 크레딧 차감 순서", success, details)
            return success

        except Exception as e:
            self.log_test("일반 앱 크레딧 차감 순서", False, f"오류: {e}")
            return False

    def test_3_permanent_license(self):
        """테스트 3: 영구 라이선스 (purchased_credits = -1)"""
        print("🧪 테스트 3: 영구 라이선스 (purchased_credits = -1)")

        try:
            credit_manager = CreditManager(
                app_name="permanent_test_app", user_email=self.test_user_email
            )

            # 영구 라이선스 설정
            credit_data = credit_manager._load_credit_data()
            credit_data["trial_credits"] = 0
            credit_data["purchased_credits"] = -1
            credit_manager._save_credit_data(credit_data)

            # 크레딧 상태 확인
            status = credit_manager.get_credit_status()
            is_unlimited = status.get("remaining_credits") == -1
            credit_type = status.get("credit_type")

            # 대량 사용 테스트
            usage_count = 100
            deduct_results = []

            with patch.object(credit_manager, "check_and_sync_credits") as mock_sync:
                for i in range(usage_count):
                    result = credit_manager.deduct_credits_by_policy(1, f"영구 라이선스 사용 {i+1}")
                    deduct_results.append(result.get("success", False))

                # sync가 호출되지 않았는지 확인
                sync_not_called = mock_sync.call_count == 0

            # 여전히 무제한
            final_status = credit_manager.get_credit_status()
            still_unlimited = final_status.get("remaining_credits") == -1

            # 사용 로그 기록 확인
            credit_data_after = credit_manager._load_credit_data()
            usage_history = credit_data_after.get("usage_history", [])
            logs_recorded = len(usage_history) >= usage_count

            success = (
                is_unlimited
                and all(deduct_results)
                and sync_not_called
                and still_unlimited
                and logs_recorded
                and credit_type == "permanent"
            )

            details = (
                f"무제한: {is_unlimited}, 사용 성공: {sum(deduct_results)}/{usage_count}, "
                f"sync 미호출: {sync_not_called}, 사용 로그: {len(usage_history)}건, 타입: {credit_type}"
            )

            self.log_test("영구 라이선스", success, details)
            return success

        except Exception as e:
            self.log_test("영구 라이선스", False, f"오류: {e}")
            return False

    def test_4_upgrade_to_permanent(self):
        """테스트 4: 일반 앱 → 영구 라이선스 업그레이드"""
        print("🧪 테스트 4: 일반 앱에서 영구 라이선스로 업그레이드")

        try:
            credit_manager = CreditManager(
                app_name="upgrade_test_app", user_email=self.test_user_email
            )

            # 초기: 일반 크레딧
            credit_data = credit_manager._load_credit_data()
            credit_data["trial_credits"] = 500
            credit_data["purchased_credits"] = 1000
            credit_manager._save_credit_data(credit_data)

            # 일반 사용
            for i in range(100):
                credit_manager.deduct_credits_by_policy(1, f"업그레이드 전 사용 {i+1}")

            before_upgrade_status = credit_manager.get_credit_status()
            before_trial = before_upgrade_status.get("trial_credits")
            before_purchased = before_upgrade_status.get("purchased_credits")

            # 크레딧 차감 확인
            credits_deducted = before_trial == 400

            # 영구 라이선스로 업그레이드
            credit_data = credit_manager._load_credit_data()
            credit_data["purchased_credits"] = -1
            credit_manager._save_credit_data(credit_data)

            # 업그레이드 후 상태
            after_upgrade_status = credit_manager.get_credit_status()
            is_unlimited = after_upgrade_status.get("remaining_credits") == -1
            credit_type = after_upgrade_status.get("credit_type")

            # 업그레이드 후 사용 (크레딧 차감 없어야 함)
            with patch.object(credit_manager, "check_and_sync_credits") as mock_sync:
                for i in range(50):
                    credit_manager.deduct_credits_by_policy(1, f"업그레이드 후 사용 {i+1}")

                sync_not_called = mock_sync.call_count == 0

            # 여전히 무제한
            final_status = credit_manager.get_credit_status()
            still_unlimited = final_status.get("remaining_credits") == -1

            success = (
                credits_deducted
                and is_unlimited
                and sync_not_called
                and still_unlimited
                and credit_type == "permanent"
            )

            details = (
                f"업그레이드 전 차감: {credits_deducted} (500→400), "
                f"업그레이드 후 무제한: {is_unlimited}, "
                f"sync 미호출: {sync_not_called}, 타입: {credit_type}"
            )

            self.log_test("일반 앱 → 영구 라이선스", success, details)
            return success

        except Exception as e:
            self.log_test("일반 앱 → 영구 라이선스", False, f"오류: {e}")
            return False

    def test_5_usage_log_without_sync(self):
        """테스트 5: 무제한 크레딧 시 usage_log만 기록"""
        print("🧪 테스트 5: 무제한 크레딧 시 usage_log만 기록, sync 없음")

        try:
            credit_manager = CreditManager(app_name="log_test_app", user_email=self.test_user_email)

            # 영구 라이선스 설정
            credit_data = credit_manager._load_credit_data()
            credit_data["trial_credits"] = 0
            credit_data["purchased_credits"] = -1
            credit_manager._save_credit_data(credit_data)

            # flush_usage_log 메서드 모킹
            with patch.object(credit_manager, "_append_to_usage_log_sheet") as mock_log_sheet:
                with patch.object(credit_manager, "check_and_sync_credits") as mock_sync:
                    # 크레딧 사용
                    for i in range(10):
                        credit_manager.deduct_credits_by_policy(1, f"로그 테스트 {i+1}")

                    # usage_log flush 호출
                    flush_result = credit_manager.flush_usage_log()

                    # usage_log 시트에는 기록되어야 함
                    log_called = mock_log_sheet.call_count > 0

                    # credit_sync는 호출되지 않아야 함
                    sync_not_called = mock_sync.call_count == 0

            success = log_called and sync_not_called and flush_result.get("success", False)

            details = (
                f"usage_log 기록: {log_called}, credit_sync 미호출: {sync_not_called}, "
                f"flush 성공: {flush_result.get('success')}"
            )

            self.log_test("무제한 시 usage_log만 기록", success, details)
            return success

        except Exception as e:
            self.log_test("무제한 시 usage_log만 기록", False, f"오류: {e}")
            return False

    def test_6_sync_status_unlimited(self):
        """테스트 6: 무제한 크레딧 시 동기화 불필요"""
        print("🧪 테스트 6: 무제한 크레딧 시 동기화 상태")

        try:
            credit_manager = CreditManager(
                app_name="sync_status_app", user_email=self.test_user_email
            )

            # 영구 라이선스 설정
            credit_data = credit_manager._load_credit_data()
            credit_data["trial_credits"] = 0
            credit_data["purchased_credits"] = -1
            credit_manager._save_credit_data(credit_data)

            # 크레딧 사용
            for i in range(20):
                credit_manager.deduct_credits_by_policy(1, f"동기화 상태 테스트 {i+1}")

            # 동기화 상태 확인
            sync_status = credit_manager.get_sync_status()
            needs_sync = sync_status.get("needs_sync", False)

            # 무제한 크레딧이므로 동기화 불필요
            success = not needs_sync

            details = f"동기화 필요: {needs_sync} (무제한이므로 False여야 함)"

            self.log_test("무제한 크레딧 시 동기화 불필요", success, details)
            return success

        except Exception as e:
            self.log_test("무제한 크레딧 시 동기화 불필요", False, f"오류: {e}")
            return False

    def run_all_tests(self):
        """모든 테스트를 실행하고 결과를 요약"""
        print("모든 테스트를 실행합니다.")

        # 백업 디렉토리 생성
        os.makedirs("backup", exist_ok=True)
        self.backup_dir = "backup"

        # 기존 크레딧 데이터 백업
        self.backup_credit_data()

        # 테스트 실행: callable인 test_ 메서드만 실행 (리스트/데이터 속성 제외)
        test_method_names = [name for name in dir(self) if name.startswith("test_")]
        for name in sorted(test_method_names):
            attr = getattr(self, name)
            if callable(attr):
                attr()

        # 백업 데이터 복원
        self.restore_credit_data()

        print("모든 테스트가 완료되었습니다.")
        self.print_summary()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n테스트 결과 요약:")
        for result in self.test_results:
            print(f"- {result['test_name']}: {'성공' if result['success'] else '실패'}")


def main():
    """테스트 러너 엔트리포인트"""
    tester = UnlimitedCreditTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
