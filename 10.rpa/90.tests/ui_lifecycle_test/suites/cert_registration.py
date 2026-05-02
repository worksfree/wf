# -*- coding: utf-8 -*-
"""
WF-ACT Registration Suite
=========================
Certification tests for registration lifecycle.

Tests cover:
- Unregistered state detection
- Registration process
- Duplicate registration prevention
- Registration info persistence
- Registration sync with server
"""

import time
import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class RegistrationSuite(BaseSuite):
    """Registration lifecycle certification tests"""

    name = "Registration Suite"
    description = "등록 라이프사이클 인증 테스트 (미등록 상태, 등록 진행, 중복 방지, 동기화)"

    def setup(self):
        """Store original registration state"""
        try:
            self.original_status = self.get_registration_status()
        except:
            self.original_status = None

    def teardown(self):
        """Restore original registration state if needed"""
        # Registration state restoration is typically handled by the app
        pass

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_get_registration_status(self):
        """등록 상태 조회가 정상 동작하는지 확인"""
        status = self.get_registration_status()
        self.assert_not_none(status, "등록 상태 조회 실패")
        self.assert_true(isinstance(status, dict), "등록 상태는 dict 형태여야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_02_status_has_required_fields(self):
        """등록 상태에 필수 필드가 있는지 확인"""
        status = self.get_registration_status()

        required_fields = ['is_registered']
        for field in required_fields:
            self.assert_in(
                field, status,
                f"등록 상태에 필수 필드 누락: {field}"
            )

    @requires_level(CertificationLevel.BASIC)
    def test_03_unregistered_state_detected(self):
        """미등록 상태가 올바르게 감지되는지 확인"""
        # Clear registration
        self.call('clear_registration')

        status = self.get_registration_status()
        self.assert_false(
            status.get('is_registered', True),
            "등록 해제 후 미등록 상태여야 함"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_04_register_with_email(self):
        """이메일 등록이 정상 동작하는지 확인"""
        # Clear first
        self.call('clear_registration')

        # Register
        test_email = "test@wf-act.local"
        result = self.call('register', test_email)

        self.assert_true(
            result.get('success') or result == True,
            f"등록 실패: {result}"
        )

        # Verify registered
        status = self.get_registration_status()
        self.assert_true(
            status.get('is_registered', False),
            "등록 후 등록 상태여야 함"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_05_registered_email_stored(self):
        """등록된 이메일이 저장되는지 확인"""
        status = self.get_registration_status()

        if status.get('is_registered'):
            email = status.get('email') or status.get('registered_email')
            self.assert_not_none(email, "등록된 이메일이 저장되어야 함")
            self.assert_true(
                '@' in str(email),
                "이메일 형식이 올바르지 않음"
            )

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_06_duplicate_registration_handled(self):
        """중복 등록 시도 처리 확인"""
        # Ensure registered
        test_email = "test@wf-act.local"
        self.call('clear_registration')
        self.call('register', test_email)

        # Try to register again
        result = self.call('register', "another@wf-act.local")

        # Should either succeed (update) or indicate already registered
        # Both behaviors are acceptable
        status = self.get_registration_status()
        self.assert_true(
            status.get('is_registered'),
            "중복 등록 시도 후에도 등록 상태 유지"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_07_invalid_email_rejected(self):
        """잘못된 이메일 형식이 거부되는지 확인"""
        self.call('clear_registration')

        invalid_emails = ['notanemail', '@nodomain', 'no@', '']

        for email in invalid_emails:
            try:
                result = self.call('register', email)
                # If no exception, check it was rejected
                if result:
                    status = self.get_registration_status()
                    if not status.get('is_registered'):
                        continue  # Good - was rejected
                    # If registered, it should not be with invalid email
                    registered_email = status.get('email', '')
                    self.assert_true(
                        registered_email != email,
                        f"잘못된 이메일이 등록됨: {email}"
                    )
            except Exception:
                # Exception is acceptable for invalid input
                pass

    @requires_level(CertificationLevel.STANDARD)
    def test_08_registration_timestamp(self):
        """등록 시간이 기록되는지 확인"""
        self.call('clear_registration')
        self.call('register', "timestamp@wf-act.local")

        status = self.get_registration_status()

        # Check for timestamp field
        timestamp = (status.get('registered_at') or
                    status.get('registration_date') or
                    status.get('timestamp'))

        self.assert_not_none(timestamp, "등록 시간이 기록되어야 함")

    @requires_level(CertificationLevel.STANDARD)
    def test_09_clear_registration(self):
        """등록 해제가 정상 동작하는지 확인"""
        # Ensure registered first
        self.call('register', "clear@wf-act.local")

        status1 = self.get_registration_status()
        self.assert_true(status1.get('is_registered'), "등록되어 있어야 함")

        # Clear
        self.call('clear_registration')

        status2 = self.get_registration_status()
        self.assert_false(
            status2.get('is_registered', True),
            "등록 해제 후 미등록 상태여야 함"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_10_registration_persists(self):
        """등록 상태가 유지되는지 확인 (재시작 없이)"""
        test_email = "persist@wf-act.local"
        self.call('clear_registration')
        self.call('register', test_email)

        # Read multiple times
        for i in range(3):
            status = self.get_registration_status()
            self.assert_true(
                status.get('is_registered'),
                f"등록 상태 유지 실패 (읽기 #{i+1})"
            )

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_11_registration_with_trial_credits(self):
        """등록 시 체험판 크레딧이 부여되는지 확인"""
        self.call('clear_registration')

        # Check credits before (should be 0 or minimal)
        self.set_credits(0)

        # Register
        self.call('register', "trial@wf-act.local")

        # Check if trial credits were given
        credits_after = self.get_credits()
        expected_trial = self.app_config.trial_credits

        # Credits should be trial amount (or more if already had some)
        self.assert_true(
            credits_after >= expected_trial,
            f"체험판 크레딧 부여: 예상 {expected_trial}, 실제 {credits_after}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_12_hardware_id_stored(self):
        """하드웨어 ID가 등록 정보에 포함되는지 확인"""
        self.call('register', "hwid@wf-act.local")

        status = self.get_registration_status()

        hwid = (status.get('hardware_id') or
                status.get('hwid') or
                status.get('machine_id'))

        # Hardware ID is optional but recommended
        if hwid:
            self.assert_true(len(str(hwid)) > 0, "하드웨어 ID가 비어있음")

    @requires_level(CertificationLevel.FULL)
    def test_13_sync_registration_to_server(self):
        """등록 정보 서버 동기화 확인"""
        self.call('register', "sync@wf-act.local")

        try:
            result = self.call('sync_registration')

            # Sync might succeed or fail depending on network
            # We just verify the function exists and returns something
            self.assert_not_none(result, "동기화 결과 없음")

        except Exception as e:
            # Network errors are acceptable in test environment
            if 'network' in str(e).lower() or 'connection' in str(e).lower():
                pass  # Acceptable
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_14_registration_version_tracked(self):
        """등록된 앱 버전이 기록되는지 확인"""
        self.call('register', "version@wf-act.local")

        status = self.get_registration_status()

        version = (status.get('app_version') or
                  status.get('version') or
                  status.get('registered_version'))

        self.assert_not_none(version, "등록 시 앱 버전이 기록되어야 함")

    @requires_level(CertificationLevel.FULL)
    def test_15_unregistered_limited_functionality(self):
        """미등록 상태에서 기능 제한 확인"""
        # 무료 앱은 크레딧 제한이 없으므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_15 스킵")
            return

        self.call('clear_registration')
        self.set_credits(0)

        status = self.get_registration_status()
        self.assert_false(status.get('is_registered'), "미등록 상태여야 함")

        # Try to work without registration and credits
        result = self.simulate_work(file_count=1)

        # Should be blocked due to no credits
        self.assert_true(
            result.get('blocked') or result.get('error') or not result.get('success'),
            "미등록 + 크레딧 없음 상태에서 작업이 차단되어야 함"
        )
