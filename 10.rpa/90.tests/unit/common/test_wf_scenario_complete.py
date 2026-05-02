#!/usr/bin/env python3
"""
크레딧 시스템 종합 테스트
- 사용자 등록부터 크레딧 사용까지 전체 플로우 테스트
"""

import sys
import os
import json
import shutil
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "10.common"))

from wf_credit_manager import CreditManager
from wf_register import WorksFreeManager


class CreditSystemTester:
    def __init__(self):
        self.test_results = []
        self.backup_dir = None
        self.test_user_email = "test.user@worksfree.co.kr"

    def log_test(self, test_name, result, details=""):
        """테스트 결과 로깅"""
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append(
            {
                "test": test_name,
                "result": result,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )
        print()

    def backup_current_state(self):
        """현재 상태 백업"""
        try:
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = f"backup_credit_test_{backup_timestamp}"
            os.makedirs(self.backup_dir, exist_ok=True)

            # .wf_rpa 디렉토리 백업
            wf_rpa_dir = os.path.expanduser("~/.wf_rpa")
            if os.path.exists(wf_rpa_dir):
                shutil.copytree(wf_rpa_dir, os.path.join(self.backup_dir, ".wf_rpa"))

            print(f"📦 현재 상태가 {self.backup_dir}에 백업되었습니다.")
            return True
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return False

    def restore_backup(self):
        """백업 상태 복원"""
        try:
            if not self.backup_dir or not os.path.exists(self.backup_dir):
                return False

            wf_rpa_dir = os.path.expanduser("~/.wf_rpa")
            backup_wf_rpa = os.path.join(self.backup_dir, ".wf_rpa")

            if os.path.exists(wf_rpa_dir):
                shutil.rmtree(wf_rpa_dir)

            if os.path.exists(backup_wf_rpa):
                shutil.copytree(backup_wf_rpa, wf_rpa_dir)

            print(f"🔄 백업 상태가 복원되었습니다.")
            return True
        except Exception as e:
            print(f"❌ 복원 실패: {e}")
            return False

    def cleanup_test_data(self):
        """테스트 데이터 정리"""
        try:
            wf_rpa_dir = os.path.expanduser("~/.wf_rpa")
            if os.path.exists(wf_rpa_dir):
                shutil.rmtree(wf_rpa_dir)
            print("🧹 테스트 데이터가 정리되었습니다.")
            return True
        except Exception as e:
            print(f"❌ 정리 실패: {e}")
            return False

    def test_1_new_user_registration(self):
        """테스트 1: 신규 사용자 등록"""
        print("🧪 테스트 1: 신규 사용자 등록")

        try:
            # 기존 데이터 정리
            self.cleanup_test_data()

            # 새 사용자 등록
            wf_manager = WorksFreeManager()

            # 등록 전 상태 확인
            user_info = wf_manager.get_user_info()
            is_registered_before = user_info.get("is_registered", False)

            # 사용자 등록 시뮬레이션 (실제로는 UI에서 수행)
            registration_data = {
                "user_email": self.test_user_email,
                "is_registered": True,
                "registration_date": datetime.now().isoformat(),
                "hardware_fingerprint": "test_hardware_fingerprint_12345",
            }

            # 등록 정보 저장
            config = wf_manager.load_config()
            config["user_info"] = registration_data
            wf_manager.save_config(config)

            # 등록 후 상태 확인
            user_info_after = wf_manager.get_user_info()
            is_registered_after = user_info_after.get("is_registered", False)

            success = not is_registered_before and is_registered_after
            details = f"등록 전: {is_registered_before}, 등록 후: {is_registered_after}, 이메일: {user_info_after.get('user_email', 'N/A')}"

            self.log_test("신규 사용자 등록", success, details)
            return success

        except Exception as e:
            self.log_test("신규 사용자 등록", False, f"오류: {e}")
            return False

    def test_2_trial_credit_allocation(self):
        """테스트 2: 체험판 크레딧 할당"""
        print("🧪 테스트 2: 체험판 크레딧 할당")

        try:
            # bom_exporter 앱의 크레딧 매니저 초기화
            credit_manager = CreditManager(app_name="bom_exporter")

            # 초기 크레딧 상태 확인
            initial_status = credit_manager.get_credit_status()
            trial_credits = initial_status.get("trial_credits", 0)

            # bom_exporter 앱의 정책 확인
            policy_info = credit_manager.get_policy_info()
            expected_trial = policy_info.get("policy", {}).get("trial_credits", 0)

            success = trial_credits == expected_trial and trial_credits > 0
            details = f"할당된 체험 크레딧: {trial_credits}, 정책상 체험 크레딧: {expected_trial}"

            self.log_test("체험판 크레딧 할당", success, details)
            return success, credit_manager

        except Exception as e:
            self.log_test("체험판 크레딧 할당", False, f"오류: {e}")
            return False, None

    def test_3_trial_credit_usage(self, credit_manager):
        """테스트 3: 체험판 크레딧 사용"""
        print("🧪 테스트 3: 체험판 크레딧 사용")

        try:
            # 사용 전 상태
            before_status = credit_manager.get_credit_status()
            trial_before = before_status.get("trial_credits", 0)
            purchased_before = before_status.get("purchased_credits", 0)

            # 크레딧 차감 시뮬레이션 (파일 1개 처리)
            deduct_result = credit_manager.deduct_credits_by_policy(1, "테스트 파일 처리")

            # 사용 후 상태
            after_status = credit_manager.get_credit_status()
            trial_after = after_status.get("trial_credits", 0)
            purchased_after = after_status.get("purchased_credits", 0)

            # 체험 크레딧에서 차감되었는지 확인
            per_item_cost = credit_manager.get_per_item_cost()
            expected_trial_after = max(0, trial_before - per_item_cost)

            success = (
                deduct_result.get("success", False)
                and trial_after == expected_trial_after
                and purchased_after == purchased_before
            )

            details = f"체험 크레딧: {trial_before}→{trial_after}, 구매 크레딧: {purchased_before}→{purchased_after}, 파일당 비용: {per_item_cost}"

            self.log_test("체험판 크레딧 사용", success, details)
            return success

        except Exception as e:
            self.log_test("체험판 크레딧 사용", False, f"오류: {e}")
            return False

    def test_4_purchase_credit_addition(self, credit_manager):
        """테스트 4: 유상 크레딧 구매 시뮬레이션"""
        print("🧪 테스트 4: 유상 크레딧 구매")

        try:
            # 구매 전 상태
            before_status = credit_manager.get_credit_status()
            purchased_before = before_status.get("purchased_credits", 0)

            # 구매 크레딧 추가 (5000 크레딧 구매)
            purchase_amount = 5000
            add_result = credit_manager.add_purchased_credits(
                purchase_amount,
                {
                    "transaction_id": f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                    "amount": purchase_amount,
                    "payment_method": "test",
                },
            )

            # 구매 후 상태
            after_status = credit_manager.get_credit_status()
            purchased_after = after_status.get("purchased_credits", 0)

            success = (
                add_result.get("success", False)
                and purchased_after == purchased_before + purchase_amount
            )

            details = (
                f"구매 크레딧: {purchased_before}→{purchased_after}, 추가량: {purchase_amount}"
            )

            self.log_test("유상 크레딧 구매", success, details)
            return success

        except Exception as e:
            self.log_test("유상 크레딧 구매", False, f"오류: {e}")
            return False

    def test_5_trial_exhaustion_and_paid_usage(self, credit_manager):
        """테스트 5: 체험 크레딧 소진 후 유상 크레딧 사용"""
        print("🧪 테스트 5: 체험 크레딧 소진 후 유상 크레딧 사용")

        try:
            # 현재 상태 확인
            current_status = credit_manager.get_credit_status()
            trial_credits = current_status.get("trial_credits", 0)
            purchased_credits = current_status.get("purchased_credits", 0)
            per_item_cost = credit_manager.get_per_item_cost()

            # 체험 크레딧을 모두 소진할 때까지 사용
            trial_usage_count = 0
            while trial_credits > 0:
                deduct_result = credit_manager.deduct_credits_by_policy(
                    1, f"체험 크레딧 소진 테스트 {trial_usage_count + 1}"
                )
                if not deduct_result.get("success", False):
                    break
                trial_usage_count += 1
                current_status = credit_manager.get_credit_status()
                trial_credits = current_status.get("trial_credits", 0)

                # 무한 루프 방지
                if trial_usage_count > 100:
                    break

            # 체험 크레딧 소진 확인
            after_trial_status = credit_manager.get_credit_status()
            trial_after_exhaustion = after_trial_status.get("trial_credits", 0)
            purchased_before_usage = after_trial_status.get("purchased_credits", 0)

            # 이제 유상 크레딧 사용
            paid_deduct_result = credit_manager.deduct_credits_by_policy(
                1, "유상 크레딧 사용 테스트"
            )

            # 유상 크레딧 사용 후 상태
            final_status = credit_manager.get_credit_status()
            purchased_after_usage = final_status.get("purchased_credits", 0)

            success = (
                trial_after_exhaustion == 0
                and paid_deduct_result.get("success", False)
                and purchased_after_usage == purchased_before_usage - per_item_cost
            )

            details = f"체험 크레딧 사용 횟수: {trial_usage_count}, 체험 소진 후: {trial_after_exhaustion}, 유상 크레딧: {purchased_before_usage}→{purchased_after_usage}"

            self.log_test("체험 크레딧 소진 후 유상 크레딧 사용", success, details)
            return success

        except Exception as e:
            self.log_test("체험 크레딧 소진 후 유상 크레딧 사용", False, f"오류: {e}")
            return False

    def test_6_usage_logging(self, credit_manager):
        """테스트 6: 크레딧 사용 로깅"""
        print("🧪 테스트 6: 크레딧 사용 로깅")

        try:
            # 크레딧 데이터에서 사용 히스토리 확인
            credit_data = credit_manager._load_credit_data()
            usage_history = credit_data.get("usage_history", [])

            # 최근 사용 기록이 있는지 확인
            has_recent_usage = len(usage_history) > 0

            if has_recent_usage:
                latest_usage = usage_history[0]  # 최신 사용 기록
                has_required_fields = all(
                    field in latest_usage for field in ["timestamp", "amount", "description"]
                )
            else:
                has_required_fields = False

            # 동기화 기능 테스트 (Google Sheets 연동)
            sync_result = credit_manager.check_and_sync_credits()
            sync_success = sync_result.get("success", False)

            success = has_recent_usage and has_required_fields and sync_success
            details = f"사용 기록 수: {len(usage_history)}, 필수 필드 포함: {has_required_fields}, 동기화: {sync_success}"

            self.log_test("크레딧 사용 로깅", success, details)
            return success

        except Exception as e:
            self.log_test("크레딧 사용 로깅", False, f"오류: {e}")
            return False

    def test_7_different_app_policies(self):
        """테스트 7: 앱별 다른 크레딧 정책"""
        print("🧪 테스트 7: 앱별 다른 크레딧 정책")

        try:
            # 다른 앱들의 크레딧 매니저 생성
            apps_to_test = ["bom_exporter", "test_app_1", "test_app_2"]
            app_policies = {}

            for app_name in apps_to_test:
                try:
                    manager = CreditManager(app_name=app_name)
                    policy_info = manager.get_policy_info()
                    app_policies[app_name] = {
                        "per_item_cost": manager.get_per_item_cost(),
                        "trial_credits": policy_info.get("policy", {}).get("trial_credits", 0),
                        "policy": policy_info.get("policy", {}),
                    }
                except Exception as e:
                    app_policies[app_name] = {"error": str(e)}

            # bom_exporter 앱은 정책이 있어야 함
            bom_exporter_has_policy = (
                "bom_exporter" in app_policies and "error" not in app_policies["bom_exporter"]
            )
            bom_exporter_cost = app_policies.get("bom_exporter", {}).get("per_item_cost", 0)

            success = bom_exporter_has_policy and bom_exporter_cost > 0
            details = f"bom_exporter 정책: {app_policies.get('bom_exporter', {})}"

            self.log_test("앱별 다른 크레딧 정책", success, details)
            return success

        except Exception as e:
            self.log_test("앱별 다른 크레딧 정책", False, f"오류: {e}")
            return False

    def test_8_insufficient_credits(self, credit_manager):
        """테스트 8: 크레딧 부족 시 처리"""
        print("🧪 테스트 8: 크레딧 부족 시 처리")

        try:
            # 현재 크레딧을 모두 소진
            max_attempts = 1000  # 무한 루프 방지
            attempts = 0

            while attempts < max_attempts:
                current_status = credit_manager.get_credit_status()
                remaining = current_status.get("remaining_credits", 0)

                if remaining <= 0:
                    break

                deduct_result = credit_manager.deduct_credits_by_policy(
                    1, f"크레딧 소진 테스트 {attempts + 1}"
                )
                if not deduct_result.get("success", False):
                    break

                attempts += 1

            # 크레딧 부족 상태에서 추가 차감 시도
            final_status = credit_manager.get_credit_status()
            remaining_before = final_status.get("remaining_credits", 0)

            insufficient_result = credit_manager.deduct_credits_by_policy(1, "크레딧 부족 테스트")

            # 부족 시 실패해야 함
            should_fail = remaining_before < credit_manager.get_per_item_cost()
            actually_failed = not insufficient_result.get("success", False)
            error_code = insufficient_result.get("error", "")

            success = should_fail == actually_failed and (
                not should_fail or error_code == "insufficient_credits"
            )
            details = f"남은 크레딧: {remaining_before}, 차감 시도 결과: {actually_failed}, 에러 코드: {error_code}"

            self.log_test("크레딧 부족 시 처리", success, details)
            return success

        except Exception as e:
            self.log_test("크레딧 부족 시 처리", False, f"오류: {e}")
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 크레딧 시스템 종합 테스트 시작")
        print("=" * 60)

        # 백업
        if not self.backup_current_state():
            print("❌ 백업 실패로 테스트를 중단합니다.")
            return

        try:
            # 테스트 실행
            test1_success = self.test_1_new_user_registration()

            test2_success, credit_manager = self.test_2_trial_credit_allocation()
            if not credit_manager:
                print("❌ 크레딧 매니저 초기화 실패로 후속 테스트를 중단합니다.")
                return

            test3_success = self.test_3_trial_credit_usage(credit_manager)
            test4_success = self.test_4_purchase_credit_addition(credit_manager)
            test5_success = self.test_5_trial_exhaustion_and_paid_usage(credit_manager)
            test6_success = self.test_6_usage_logging(credit_manager)
            test7_success = self.test_7_different_app_policies()
            test8_success = self.test_8_insufficient_credits(credit_manager)

            # 결과 요약
            print("=" * 60)
            print("📊 테스트 결과 요약")
            print("=" * 60)

            passed_tests = sum(1 for result in self.test_results if result["result"])
            total_tests = len(self.test_results)

            for result in self.test_results:
                status = "✅ PASS" if result["result"] else "❌ FAIL"
                print(f"{status} {result['test']}")
                if result["details"]:
                    print(f"     └─ {result['details']}")

            print(
                f"\n📈 전체 결과: {passed_tests}/{total_tests} 테스트 통과 ({passed_tests/total_tests*100:.1f}%)"
            )

            if passed_tests == total_tests:
                print("🎉 모든 테스트가 성공적으로 통과했습니다!")
            else:
                print("⚠️  일부 테스트가 실패했습니다. 세부 내용을 확인해주세요.")

        finally:
            # 백업 복원
            print("\n🔄 원래 상태로 복원 중...")
            self.restore_backup()

            # 백업 파일 정리
            if self.backup_dir and os.path.exists(self.backup_dir):
                try:
                    shutil.rmtree(self.backup_dir)
                    print("🗑️  백업 파일이 정리되었습니다.")
                except:
                    print(f"⚠️  백업 파일 정리 실패: {self.backup_dir}")


def main():
    """메인 함수"""
    tester = CreditSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
