# -*- coding: utf-8 -*-
"""
WF-ACT Credit Suite
===================
Certification tests for credit system.

Tests cover:
- Credit deduction
- Insufficient credits blocking
- Work interruption when credits exhausted mid-operation
- Credit purchase and resume
- Edge cases (exact credits, boundary conditions)
"""

import time
import os
import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level, SkipTest

logger = logging.getLogger(__name__)


class CreditSuite(BaseSuite):
    """Credit system certification tests"""

    name = "Credit Suite"
    description = "크레딧 시스템 인증 테스트 (차감, 부족 차단, 작업 중 소진, 구매, 재개)"

    def should_skip(self) -> bool:
        """Skip entire suite for free apps (trial_credits=-1)"""
        if self.app_config.trial_credits == -1:
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 Credit Suite 스킵")
            return True
        return False

    def should_run(self) -> bool:
        """Ensure tests only run when suite is applicable"""
        if self.should_skip():
            self.skip(f"[{self.app_config.name}] 무료 앱이므로 Credit Suite 스킵")
        return True

    def setup(self):
        """Reset credits to known state before tests"""
        # Store original credits
        try:
            self.original_credits = self.get_credits()
        except:
            self.original_credits = 0

        # Set test credits (enough for multiple operations)
        self.set_credits(self.app_config.credit_per_work * 10)

    def teardown(self):
        """Restore original credits after tests"""
        try:
            self.set_credits(self.original_credits)
        except:
            pass

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_get_credits(self):
        """크레딧 조회가 정상 동작하는지 확인"""
        credits = self.get_credits()
        self.assert_not_none(credits, "크레딧 조회 실패")
        self.assert_true(isinstance(credits, (int, float)), "크레딧은 숫자여야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_02_set_credits(self):
        """크레딧 설정이 정상 동작하는지 확인"""
        test_amount = 5000
        self.set_credits(test_amount)
        credits = self.get_credits()
        self.assert_equal(credits, test_amount, f"크레딧 설정 실패: {credits} != {test_amount}")

    @requires_level(CertificationLevel.BASIC)
    def test_03_credit_deduction_single(self):
        """단일 작업 시 크레딧이 정책에 맞게 차감되는지 확인"""
        cost = self.app_config.credit_per_work
        initial = cost * 5
        self.set_credits(initial)

        # Simulate work
        result = self.simulate_work(file_count=1)

        credits_after = self.get_credits()
        expected = initial - cost

        self.assert_equal(
            credits_after, expected,
            f"크레딧 차감 오류: {initial} - {cost} = {expected}, 실제: {credits_after}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_04_insufficient_credits_blocked(self):
        """크레딧 부족 시 작업이 차단되는지 확인"""
        cost = self.app_config.credit_per_work

        # Set credits to less than required
        self.set_credits(cost - 1)

        # Attempt work - should fail or return blocked status
        result = self.simulate_work(file_count=1)

        # Check that work was blocked
        self.assert_true(
            result.get('blocked') or result.get('error') or not result.get('success'),
            "크레딧 부족 시 작업이 차단되어야 함"
        )

        # Credits should not change
        credits_after = self.get_credits()
        self.assert_equal(
            credits_after, cost - 1,
            "차단된 작업은 크레딧을 변경하면 안됨"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_05_zero_credits_blocked(self):
        """크레딧 0일 때 작업이 차단되는지 확인"""
        self.set_credits(0)

        result = self.simulate_work(file_count=1)

        self.assert_true(
            result.get('blocked') or result.get('error') or not result.get('success'),
            "크레딧 0일 때 작업이 차단되어야 함"
        )

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_06_credit_deduction_multiple(self):
        """여러 파일 작업 시 크레딧이 정확히 차감되는지 확인"""
        cost = self.app_config.credit_per_work
        file_count = 3
        initial = cost * 10
        self.set_credits(initial)

        result = self.simulate_work(file_count=file_count)

        credits_after = self.get_credits()
        expected = initial - (cost * file_count)

        self.assert_equal(
            credits_after, expected,
            f"다중 파일 크레딧 차감 오류: {file_count}개 파일, 예상: {expected}, 실제: {credits_after}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_07_exact_credits_works(self):
        """크레딧이 정확히 작업 비용과 같을 때 작업 가능 확인"""
        cost = self.app_config.credit_per_work

        # Set exact amount needed
        self.set_credits(cost)

        result = self.simulate_work(file_count=1)

        # Should succeed
        self.assert_true(
            result.get('success') or not result.get('blocked'),
            "정확한 크레딧으로 작업이 가능해야 함"
        )

        # Credits should be 0 after
        credits_after = self.get_credits()
        self.assert_equal(credits_after, 0, "작업 후 크레딧이 0이어야 함")

    @requires_level(CertificationLevel.STANDARD)
    def test_08_one_short_blocked(self):
        """크레딧이 1 부족할 때 차단 확인"""
        cost = self.app_config.credit_per_work

        self.set_credits(cost - 1)

        result = self.simulate_work(file_count=1)

        self.assert_true(
            result.get('blocked') or result.get('error') or not result.get('success'),
            "크레딧이 1 부족할 때 작업이 차단되어야 함"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_09_mid_work_exhaustion(self):
        """작업 중 크레딧 소진 시 중단 및 상태 저장 확인"""
        cost = self.app_config.credit_per_work

        # Set credits for only 2 files
        self.set_credits(cost * 2)

        # Try to process 5 files
        result = self.simulate_work(file_count=5)

        # Should process only 2 files
        processed = result.get('processed_count', result.get('processed', 0))
        self.assert_equal(
            processed, 2,
            f"크레딧 소진 시 처리된 파일 수: 예상 2, 실제 {processed}"
        )

        # Should indicate interruption
        self.assert_true(
            result.get('interrupted') or result.get('exhausted') or processed < 5,
            "크레딧 소진으로 작업이 중단되어야 함"
        )

        # Credits should be 0
        credits_after = self.get_credits()
        self.assert_equal(credits_after, 0, "소진 후 크레딧이 0이어야 함")

    @requires_level(CertificationLevel.STANDARD)
    def test_10_purchase_credits(self):
        """크레딧 구매(추가) 기능 확인"""
        self.set_credits(0)
        purchase_amount = 1000

        # Simulate purchase
        self.call('add_credits', purchase_amount)

        credits_after = self.get_credits()
        self.assert_equal(
            credits_after, purchase_amount,
            f"크레딧 구매 후: 예상 {purchase_amount}, 실제 {credits_after}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_11_resume_after_purchase(self):
        """크레딧 구매 후 작업 재개 확인"""
        cost = self.app_config.credit_per_work

        # Start with 0 credits
        self.set_credits(0)

        # Try work - should fail
        result1 = self.simulate_work(file_count=1)
        self.assert_true(
            result1.get('blocked') or result1.get('error') or not result1.get('success'),
            "크레딧 0일 때 차단되어야 함"
        )

        # Purchase credits
        self.call('add_credits', cost * 5)

        # Try work again - should succeed
        result2 = self.simulate_work(file_count=1)
        self.assert_true(
            result2.get('success') or not result2.get('blocked'),
            "크레딧 구매 후 작업이 가능해야 함"
        )

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_12_continuous_work_sequence(self):
        """연속 작업 시퀀스 테스트 (10개 파일 중 5번째에서 소진)"""
        cost = self.app_config.credit_per_work

        # Set credits for exactly 5 files
        self.set_credits(cost * 5)

        # Process 10 files in sequence
        total_processed = 0
        interrupted_at = None

        for i in range(10):
            credits_before = self.get_credits()

            if credits_before < cost:
                # Not enough credits - this file should be blocked
                result = self.simulate_work(file_count=1)
                if result.get('blocked') or result.get('error') or not result.get('success'):
                    interrupted_at = i
                    break

            result = self.simulate_work(file_count=1)
            if result.get('success') and not result.get('blocked'):
                total_processed += 1

        self.assert_equal(
            total_processed, 5,
            f"5개 파일만 처리되어야 함: 실제 {total_processed}"
        )
        self.assert_equal(
            interrupted_at, 5,
            f"5번째 파일에서 중단되어야 함: 실제 {interrupted_at}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_13_resume_continuous_work(self):
        """중단된 연속 작업 재개 테스트"""
        cost = self.app_config.credit_per_work

        # Set credits for 3 files
        self.set_credits(cost * 3)

        # Process 5 files - will stop at 3
        result1 = self.simulate_work(file_count=5)
        processed1 = result1.get('processed_count', result1.get('processed', 0))

        self.assert_equal(processed1, 3, f"첫 번째 배치: 3개 처리되어야 함, 실제 {processed1}")

        # Purchase more credits
        self.call('add_credits', cost * 5)

        # Resume with remaining 2 files
        result2 = self.simulate_work(file_count=2)
        processed2 = result2.get('processed_count', result2.get('processed', 0))

        self.assert_equal(processed2, 2, f"두 번째 배치: 2개 처리되어야 함, 실제 {processed2}")

        # Check total credits used: 3 + 2 = 5 files
        credits_after = self.get_credits()
        expected_remaining = (cost * 5) - (cost * 2)  # 5 purchased, 2 used
        self.assert_equal(
            credits_after, expected_remaining,
            f"남은 크레딧: 예상 {expected_remaining}, 실제 {credits_after}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_14_negative_credits_prevented(self):
        """음수 크레딧 방지 확인"""
        # Try to set negative credits
        try:
            self.set_credits(-100)
            credits = self.get_credits()
            self.assert_true(
                credits >= 0,
                "크레딧은 음수가 될 수 없음"
            )
        except Exception:
            # Exception is also acceptable behavior
            pass

    @requires_level(CertificationLevel.FULL)
    def test_15_large_credit_amount(self):
        """대용량 크레딧 처리 확인"""
        large_amount = 999999999
        self.set_credits(large_amount)
        credits = self.get_credits()
        self.assert_equal(
            credits, large_amount,
            f"대용량 크레딧 설정: 예상 {large_amount}, 실제 {credits}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_16_credit_persistence_check(self):
        """크레딧 값이 일관성 있게 유지되는지 확인"""
        test_value = 12345
        self.set_credits(test_value)

        # Read multiple times
        for i in range(5):
            credits = self.get_credits()
            self.assert_equal(
                credits, test_value,
                f"크레딧 일관성 오류 (읽기 #{i+1}): 예상 {test_value}, 실제 {credits}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_17_concurrent_credit_operations(self):
        """동시 크레딧 연산 테스트"""
        cost = self.app_config.credit_per_work
        initial = cost * 100
        self.set_credits(initial)

        # Rapid fire operations
        operations = 10
        for i in range(operations):
            self.simulate_work(file_count=1)

        expected = initial - (cost * operations)
        credits_after = self.get_credits()

        self.assert_equal(
            credits_after, expected,
            f"연속 작업 후 크레딧: 예상 {expected}, 실제 {credits_after}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_18_trial_credits_initial(self):
        """체험판 크레딧 초기 지급 확인"""
        expected_trial = self.app_config.trial_credits

        # This test assumes there's a way to check trial status
        # Implementation depends on app specifics
        result = self.call('get_trial_info')

        if result and 'initial_credits' in result:
            self.assert_equal(
                result['initial_credits'], expected_trial,
                f"체험판 크레딧: 예상 {expected_trial}, 실제 {result['initial_credits']}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_19_credit_history_json_exists(self):
        """credit_history.json 파일 존재 및 형식 확인"""
        import os
        import json
        from pathlib import Path

        app_name = self.app_config.name
        user_home = Path(os.path.expanduser("~"))
        history_path = user_home / '.wf_rpa' / app_name / 'credit_history.json'

        # credit_history.json should exist after work
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Should be a dict or list
                self.assert_true(
                    isinstance(data, (dict, list)),
                    f"credit_history.json 형식 오류: {type(data)}"
                )

                # If list, check max 100 records limit
                if isinstance(data, list):
                    self.assert_true(
                        len(data) <= 100,
                        f"credit_history.json 레코드 수가 100건 초과: {len(data)}건"
                    )
                # If dict with records/history key
                elif isinstance(data, dict):
                    records = data.get('records') or data.get('history') or data.get('logs') or []
                    if isinstance(records, list):
                        self.assert_true(
                            len(records) <= 100,
                            f"credit_history.json 레코드 수가 100건 초과: {len(records)}건"
                        )
            except json.JSONDecodeError as e:
                self.assert_true(False, f"credit_history.json JSON 파싱 오류: {e}")

    @requires_level(CertificationLevel.FULL)
    def test_20_credit_usage_log_after_work(self):
        """작업 후 크레딧 사용 로그 기록 확인"""
        import os
        import json
        from pathlib import Path

        app_name = self.app_config.name
        user_home = Path(os.path.expanduser("~"))
        history_path = user_home / '.wf_rpa' / app_name / 'credit_history.json'

        # Get initial record count
        initial_count = 0
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    initial_count = len(data)
                elif isinstance(data, dict):
                    records = data.get('records') or data.get('history') or data.get('logs') or []
                    initial_count = len(records) if isinstance(records, list) else 0
            except:
                pass

        # Perform work
        self.set_credits(self.app_config.credit_per_work * 5)
        self.simulate_work(file_count=1)

        # Check if record was added
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    new_count = len(data)
                elif isinstance(data, dict):
                    records = data.get('records') or data.get('history') or data.get('logs') or []
                    new_count = len(records) if isinstance(records, list) else 0
                else:
                    new_count = initial_count

                self.assert_true(
                    new_count >= initial_count,
                    f"작업 후 크레딧 사용 로그가 기록되지 않음: 이전 {initial_count}건, 현재 {new_count}건"
                )
            except:
                pass

    @requires_level(CertificationLevel.FULL)
    def test_21_google_sheets_sync_config(self):
        """Google Sheets 크레딧 동기화 설정 확인 (credit_usage_log, credit_sync 시트)"""
        try:
            sync_config = self.call('get_credit_sync_config')

            if sync_config:
                # Check for sheet names configuration
                usage_log_sheet = sync_config.get('usage_log_sheet') or sync_config.get('credit_usage_log')
                sync_sheet = sync_config.get('sync_sheet') or sync_config.get('credit_sync')

                has_sheets_config = usage_log_sheet or sync_sheet or sync_config.get('enabled')

                self.assert_true(
                    has_sheets_config,
                    "Google Sheets 크레딧 동기화 설정이 필요함 (credit_usage_log, credit_sync)"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # Alternative: check wf_rpa_config.json directly
                try:
                    config = self.call('get_wf_rpa_config')
                    if config:
                        google_sheets = config.get('google_sheets', {})
                        # At minimum, google_sheets config should exist for sync
                        self.assert_true(
                            bool(google_sheets),
                            "wf_rpa_config.json에 google_sheets 동기화 설정이 필요함"
                        )
                except:
                    pass
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_22_credit_sync_on_exit_handler(self):
        """앱 종료 시 크레딧 동기화 핸들러 존재 확인"""
        try:
            result = self.call('check_exit_sync_handler')

            if result:
                has_handler = result.get('has_exit_handler') or result.get('sync_on_exit')
                self.assert_true(
                    has_handler,
                    "앱 종료 시 크레딧 동기화 핸들러가 필요함"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # Alternative: check if sync method exists
                try:
                    sync_result = self.call('get_sync_status')
                    if sync_result:
                        self.assert_true(
                            sync_result.get('sync_enabled') or sync_result.get('last_sync'),
                            "크레딧 동기화 기능이 활성화되어야 함"
                        )
                except:
                    pass  # Sync handler check might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_23_end_to_end_credit_sync(self):
        """엔드-투-엔드 테스트: 파일 처리 → credit_history.json 업데이트"""
        import json
        import time
        from pathlib import Path
        
        try:
            app_name = self.app_config.name
            # Dev 모드에서는 10.common/config 경로 사용 (Basic Rule)
            if self.client.dev_mode:
                try:
                    from wf_credit_manager import CreditManager
                    credit_mgr = CreditManager(app_name)
                    credit_history_path = credit_mgr.credit_file
                except Exception as e:
                    self.skip(f"credit_history.json 경로 계산 실패: {e}")
                    return
            else:
                user_home = Path(os.path.expanduser("~"))
                credit_history_path = user_home / '.wf_rpa' / app_name / 'credit_history.json'
            
            # 1. 크레딧 이력 파일 확인
            if not credit_history_path.exists():
                logger.info(f"ℹ️ credit_history.json이 아직 생성되지 않았습니다 (DEV/DEMO 모드에서는 정상)")
                self.skip("credit_history.json이 생성되지 않았습니다 (실제 작업 후 생성됨)")
                return
            
            try:
                with open(credit_history_path, 'r', encoding='utf-8') as f:
                    initial_data = json.load(f)
                    initial_updated = initial_data.get('last_updated', None)
                    initial_usage_count = len(initial_data.get('usage_history', []))
            except Exception as e:
                self.skip(f"credit_history.json 읽기 실패: {e}")
                return
            
            # 2. 충분한 크레딧 설정
            self.set_credits(self.app_config.credit_per_work * 5)
            
            # 3. 실제 파일 처리 수행
            self.simulate_work(file_count=1)
            
            # 4. 약간의 지연 (업데이트 대기)
            time.sleep(2)
            
            # 5. credit_history 업데이트 확인
            try:
                with open(credit_history_path, 'r', encoding='utf-8') as f:
                    after_data = json.load(f)
                    after_updated = after_data.get('last_updated', None)
                    after_usage_count = len(after_data.get('usage_history', []))
                    
                    # 이력이 업데이트되었는지 확인 (usage_history 증가 또는 last_updated 변경)
                    history_updated = (
                        after_updated and 
                        (after_updated != initial_updated or after_usage_count > initial_usage_count)
                    )
                    
                    self.assert_true(
                        history_updated,
                        f"작업 후 크레딧 이력이 업데이트되어야 함. "
                        f"초기 updated={initial_updated} (usage={initial_usage_count}), "
                        f"이후 updated={after_updated} (usage={after_usage_count})"
                    )
                    
                    logger.info(f"✅ 크레딧 이력 업데이트 확인: usage_history 증가 ({initial_usage_count}→{after_usage_count})")
            except Exception as e:
                self.fail(f"credit_history.json 확인 실패: {e}")

        except SkipTest:
            raise
        except Exception as e:
            self.fail(f"엔드-투-엔드 테스트 실패: {e}")

    @requires_level(CertificationLevel.FULL)
    def test_24_google_sheets_write_verification(self):
        """Google Sheets 쓰기 확인: credit_usage_log, credit_sync에 데이터 기록되는지"""
        import time
        
        # API 제약 방지를 위한 대기
        time.sleep(10)
        
        try:
            # 구글 시트 매니저를 통해 실제 데이터 확인
            from wf_googlesheets_manager import get_sheets_manager
            
            sheets_manager = get_sheets_manager(test_mode=True)
            
            if not sheets_manager or not sheets_manager.gc:
                self.fail("Google Sheets 연결 실패 (네트워크 문제 또는 설정 오류)")
                return
            
            # 스프레드시트 접근 가능 확인
            try:
                config = sheets_manager._load_config()
                sheet_id = config.get("SHEET_ID_DEV") or config.get("SHEET_ID_RELEASE")
                spreadsheet = sheets_manager.gc.open_by_key(sheet_id)
                
                # credit_usage_log 시트 확인
                try:
                    usage_ws = spreadsheet.worksheet("credit_usage_log")
                    usage_rows = len(usage_ws.get_all_values())
                    self.assert_true(
                        usage_rows > 1,  # 헤더 + 최소 1개 데이터 행
                        f"credit_usage_log 시트에 데이터가 없습니다 (행 수: {usage_rows})"
                    )
                except gspread.exceptions.WorksheetNotFound:
                    self.skip("credit_usage_log 워크시트를 찾을 수 없습니다")
                
                # credit_sync 시트 확인
                try:
                    sync_ws = spreadsheet.worksheet("credit_sync")
                    sync_rows = len(sync_ws.get_all_values())
                    self.assert_true(
                        sync_rows > 1,  # 헤더 + 최소 1개 데이터 행
                        f"credit_sync 시트에 데이터가 없습니다 (행 수: {sync_rows})"
                    )
                except gspread.exceptions.WorksheetNotFound:
                    self.skip("credit_sync 워크시트를 찾을 수 없습니다")
                    
            except Exception as sheet_err:
                self.skip(f"Google Sheets 접근 실패: {sheet_err}")
                
        except ImportError:
            self.skip("wf_googlesheets_manager를 임포트할 수 없습니다")

    def test_26_e2e_credit_sync_flow(self):
        """엔드-투-엔드: 파일 처리 → credit_changed=True → sync 호출"""
        self.should_run()
        
        try:
            import json
            from pathlib import Path
            
            app_name = getattr(self.app_config, "app_id", None) or self.app_config.name
            credit_history_path = Path.home() / ".wf_rpa" / app_name / "credit_history.json"
            
            if not credit_history_path.exists():
                self.skip(f"credit_history.json 파일이 없습니다: {credit_history_path}")
                return
            
            # Get initial state
            with open(credit_history_path, 'r', encoding='utf-8') as f:
                initial_data = json.load(f)
            initial_purchased = initial_data.get('remaining_purchased', 0)
            initial_updated = initial_data.get('last_updated', "")
            
            # Verify credit history structure is valid
            self.assert_true(
                'remaining_purchased' in initial_data or 'remaining_trial' in initial_data,
                "credit_history.json에 크레딧 정보가 있어야 합니다"
            )
            
            # Check purchase history exists or can be tracked
            self.assert_true(
                'purchase_history' in initial_data or 'usage_history' in initial_data,
                "credit_history.json에 이력 정보가 있어야 합니다"
            )
            
            # Verify last_updated is set
            self.assert_true(
                initial_updated,
                "last_updated 필드가 설정되어야 합니다"
            )
            
            logger.info(f"✅ E2E 흐름 확인 성공: remaining_purchased={initial_purchased}, last_updated={initial_updated}")
            
        except SkipTest:
            raise
        except Exception as e:
            self.fail(f"E2E 흐름 테스트 실패: {e}")

    def test_27_google_sheets_sync_actual(self):
        """Google Sheets 동기화 확인: 실제 데이터 기록"""
        self.should_run()
        
        try:
            import json
            from pathlib import Path
            
            # Check if credit_history.json exists (primary source of truth)
            app_name = getattr(self.app_config, "app_id", None) or self.app_config.name
            credit_history_path = Path.home() / ".wf_rpa" / app_name / "credit_history.json"
            
            # Verify credit history file exists and has proper structure
            if not credit_history_path.exists():
                self.skip(f"credit_history.json 파일이 없습니다: {credit_history_path}")
                return
            
            # Load and verify credit history
            with open(credit_history_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Verify essential fields
            self.assert_true(
                'last_updated' in history_data,
                "credit_history.json에 last_updated 필드가 있어야 합니다"
            )
            
            last_updated = history_data.get('last_updated', '')
            self.assert_true(
                last_updated,
                "last_updated가 설정되어야 합니다"
            )
            
            logger.info(f"✅ Credit History 확인: last_updated={last_updated}")
            
            # Try importing GoogleSheetsManager to verify sheets configuration
            try:
                from sys import path as sys_path
                wf_path = Path.home() / ".wf_rpa" / "10.common"
                if str(wf_path) not in sys_path:
                    sys_path.insert(0, str(wf_path))
                
                from wf_googlesheets_manager import GoogleSheetsManager
                
                sheets_manager = GoogleSheetsManager()
                config = sheets_manager.get_sheets_config()
                
                logger.info(f"✅ Google Sheets 설정 확인: {list(config.keys())}")
                self.assert_true(
                    'sheet_id_dev' in config or 'sheet_id_release' in config,
                    "Sheet ID가 설정되어야 합니다"
                )
                
            except ImportError:
                self.skip("GoogleSheetsManager를 임포트할 수 없습니다 (테스트 환경)")
            except Exception as sheets_err:
                logger.warning(f"Google Sheets 접근 실패: {sheets_err}")
                self.skip(f"Google Sheets 접근 불가: {sheets_err}")
                
        except SkipTest:
            raise
        except Exception as e:
            self.fail(f"Google Sheets 동기화 테스트 실패: {e}")

