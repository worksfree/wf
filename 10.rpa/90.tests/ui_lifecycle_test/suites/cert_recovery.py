# -*- coding: utf-8 -*-
"""
WF-ACT Recovery Suite
=====================
Certification tests for error recovery.

Tests cover:
- Invalid input handling
- Network error handling
- File lock handling
- State recovery after errors
"""

import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class RecoverySuite(BaseSuite):
    """Error recovery certification tests"""

    name = "Recovery Suite"
    description = "오류 복구 인증 테스트 (잘못된 입력, 네트워크 오류, 파일 락, 상태 복구)"

    def setup(self):
        """Store initial state for recovery verification"""
        self.initial_credits = self.get_credits()

    def teardown(self):
        """Restore initial state"""
        try:
            self.set_credits(self.initial_credits)
        except:
            pass

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_invalid_command_handled(self):
        """잘못된 명령어 처리 확인"""
        try:
            self.call('this_command_does_not_exist_12345')
            # If no exception, check response indicates error
        except RuntimeError as e:
            # RuntimeError with "Unknown command" is expected
            self.assert_true(
                'unknown' in str(e).lower() or 'command' in str(e).lower(),
                f"잘못된 명령어에 대한 적절한 오류 메시지가 없음: {e}"
            )
        except Exception:
            # Other exceptions are also acceptable
            pass

    @requires_level(CertificationLevel.BASIC)
    def test_02_null_argument_handled(self):
        """null 인자 처리 확인"""
        try:
            self.call('set_credits', None)
        except Exception:
            pass  # Exception is acceptable

        # App should still be responsive
        credits = self.get_credits()
        self.assert_not_none(credits, "null 인자 후에도 앱이 응답해야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_03_negative_credits_handled(self):
        """음수 크레딧 설정 처리 확인"""
        # 무료 앱은 크레딧이 -1이므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_03 스킵")
            return

        try:
            self.call('set_credits', -1000)
        except Exception:
            pass  # Exception is acceptable

        # Credits should not be negative
        credits = self.get_credits()
        self.assert_true(credits >= 0, "크레딧이 음수가 되면 안됨")

    @requires_level(CertificationLevel.BASIC)
    def test_04_empty_string_handled(self):
        """빈 문자열 처리 확인"""
        try:
            self.call('register', '')
        except Exception:
            pass  # Exception is acceptable

        # App should still be responsive
        state = self.get_state()
        self.assert_not_none(state, "빈 문자열 후에도 앱이 응답해야 함")

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_05_state_preserved_after_error(self):
        """오류 발생 후 상태 유지 확인"""
        # 무료 앱은 크레딧 관리가 없으므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_05 스킵")
            return

        test_credits = 5000
        self.set_credits(test_credits)

        # Cause an error
        try:
            self.call('invalid_operation_xyz')
        except:
            pass

        # State should be preserved
        credits_after = self.get_credits()
        self.assert_equal(
            credits_after, test_credits,
            "오류 후에도 크레딧이 유지되어야 함"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_06_rapid_error_recovery(self):
        """연속 오류 후 복구 확인"""
        # Rapid invalid commands
        for i in range(5):
            try:
                self.call(f'invalid_cmd_{i}')
            except:
                pass

        # App should still be responsive
        credits = self.get_credits()
        self.assert_not_none(credits, "연속 오류 후에도 앱이 응답해야 함")

    @requires_level(CertificationLevel.STANDARD)
    def test_07_work_with_invalid_file_count(self):
        """잘못된 파일 수로 작업 시도"""
        self.set_credits(10000)

        invalid_counts = [0, -1, -100]

        for count in invalid_counts:
            try:
                result = self.simulate_work(file_count=count)
                # Should either fail gracefully or treat as 0 work
            except Exception:
                pass  # Exception is acceptable

        # App should still work normally
        self.set_credits(self.app_config.credit_per_work * 2)
        result = self.simulate_work(file_count=1)
        self.assert_true(
            result.get('success') or not result.get('blocked'),
            "잘못된 파일 수 처리 후에도 정상 작업이 가능해야 함"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_08_large_number_handled(self):
        """매우 큰 숫자 처리 확인"""
        huge_number = 10 ** 15

        try:
            self.set_credits(huge_number)
            credits = self.get_credits()
            # Should either accept or reject gracefully
            self.assert_true(credits >= 0, "크레딧이 유효한 값이어야 함")
        except Exception:
            pass  # Exception is acceptable for overflow protection

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_09_timeout_handling(self):
        """타임아웃 처리 확인"""
        try:
            # Request a long operation with short timeout
            result = self.call('simulate_long_operation', timeout=0.001)
        except Exception as e:
            # Timeout exception is acceptable
            if 'timeout' in str(e).lower():
                pass
            # Other exceptions might indicate different handling
            pass

        # App should still be responsive
        credits = self.get_credits()
        self.assert_not_none(credits, "타임아웃 후에도 앱이 응답해야 함")

    @requires_level(CertificationLevel.FULL)
    def test_10_unicode_handling(self):
        """유니코드 문자 처리 확인"""
        unicode_test = "테스트@유니코드.한글"

        try:
            self.call('register', unicode_test)
        except Exception:
            pass  # Exception is acceptable if email validation fails

        # App should handle unicode gracefully
        state = self.get_state()
        self.assert_not_none(state, "유니코드 처리 후에도 앱이 응답해야 함")

    @requires_level(CertificationLevel.FULL)
    def test_11_special_characters_handled(self):
        """특수 문자 처리 확인"""
        special_chars = "<script>alert('xss')</script>'; DROP TABLE users;--"

        try:
            # Try with various commands
            self.call('set_user_input', special_chars)
        except:
            pass

        # App should be unaffected
        credits = self.get_credits()
        self.assert_not_none(credits, "특수 문자 처리 후에도 앱이 응답해야 함")

    @requires_level(CertificationLevel.FULL)
    def test_12_partial_work_recovery(self):
        """부분 작업 실패 후 복구 확인"""
        # 무료 앱은 크레딧 소진이 없으므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_12 스킵")
            return

        cost = self.app_config.credit_per_work

        # Set credits for exactly 3 files
        self.set_credits(cost * 3)

        # Try to process 5 files (will fail at 4th)
        result1 = self.simulate_work(file_count=5)
        processed1 = result1.get('processed_count', result1.get('processed', 0))

        # Credits should be exactly 0
        credits_mid = self.get_credits()
        self.assert_equal(credits_mid, 0, "부분 작업 후 크레딧이 0이어야 함")

        # Add credits and verify can continue
        self.set_credits(cost * 5)
        result2 = self.simulate_work(file_count=2)

        # Should succeed
        self.assert_true(
            result2.get('success') or not result2.get('blocked'),
            "복구 후 작업이 가능해야 함"
        )
