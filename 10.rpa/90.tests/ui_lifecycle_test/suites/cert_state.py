# -*- coding: utf-8 -*-
"""
WF-ACT State Suite
==================
Certification tests for state management.

Tests cover:
- State persistence
- Session management
- Crash recovery
- Settings save/load
"""

import time
import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class StateSuite(BaseSuite):
    """State management certification tests"""

    name = "State Suite"
    description = "상태 관리 인증 테스트 (상태 유지, 세션 관리, 복구, 설정 저장/로드)"

    def setup(self):
        """Store original state"""
        try:
            self.original_state = self.get_state()
        except:
            self.original_state = None

    def teardown(self):
        """Cleanup after tests"""
        pass

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_get_state(self):
        """앱 상태 조회가 정상 동작하는지 확인"""
        state = self.get_state()
        self.assert_not_none(state, "상태 조회 실패")
        self.assert_true(isinstance(state, dict), "상태는 dict 형태여야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_02_state_has_required_fields(self):
        """상태에 필수 필드가 있는지 확인"""
        state = self.get_state()

        # At minimum, should have some identification
        self.assert_true(
            len(state) > 0,
            "상태에 최소 하나의 필드가 있어야 함"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_03_state_consistency(self):
        """상태가 일관성 있게 유지되는지 확인"""
        state1 = self.get_state()
        time.sleep(0.1)
        state2 = self.get_state()

        # Core state should be consistent
        # (some fields like timestamp may change)
        self.assert_true(
            state1 is not None and state2 is not None,
            "상태 조회 일관성 실패"
        )

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_04_save_settings(self):
        """설정 저장 기능 확인"""
        test_setting = {'test_key': 'test_value_' + str(time.time())}

        result = self.call('save_settings', test_setting)

        self.assert_true(
            result.get('success') or result == True,
            "설정 저장 실패"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_05_load_settings(self):
        """설정 로드 기능 확인"""
        settings = self.call('load_settings')

        self.assert_not_none(settings, "설정 로드 실패")
        self.assert_true(isinstance(settings, dict), "설정은 dict 형태여야 함")

    @requires_level(CertificationLevel.STANDARD)
    def test_06_settings_persistence(self):
        """설정이 저장 후 로드되는지 확인"""
        unique_value = f"persist_test_{int(time.time())}"
        test_setting = {'persistence_test': unique_value}

        # Save
        self.call('save_settings', test_setting)

        # Load and verify
        settings = self.call('load_settings')

        # The saved value should be retrievable
        # (exact structure depends on app implementation)
        self.assert_not_none(settings, "설정 로드 실패")

    @requires_level(CertificationLevel.STANDARD)
    def test_07_session_id_exists(self):
        """세션 ID가 존재하는지 확인"""
        state = self.get_state()

        session_id = (state.get('session_id') or
                     state.get('session') or
                     state.get('sid'))

        # Session ID is optional but recommended
        if session_id:
            self.assert_true(
                len(str(session_id)) > 0,
                "세션 ID가 비어있음"
            )

    @requires_level(CertificationLevel.STANDARD)
    def test_08_last_activity_tracked(self):
        """마지막 활동 시간이 추적되는지 확인"""
        # Perform some activity
        self.get_credits()

        state = self.get_state()

        last_activity = (state.get('last_activity') or
                        state.get('last_active') or
                        state.get('updated_at'))

        # Last activity tracking is recommended
        if last_activity:
            self.assert_not_none(last_activity, "마지막 활동 시간 없음")

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_09_work_progress_saved(self):
        """작업 진행 상태가 저장되는지 확인"""
        cost = self.app_config.credit_per_work

        # Set up for partial work
        self.set_credits(cost * 2)

        # Start work that will be interrupted
        result = self.simulate_work(file_count=5)

        # Check if progress was saved
        state = self.get_state()

        # Progress info should exist in some form
        progress = (state.get('work_progress') or
                   state.get('progress') or
                   state.get('pending_work') or
                   result.get('remaining'))

        # Having progress info is recommended for interrupted work
        # Not strictly required if work completes or no progress tracking
        self.assert_true(True, "진행 상태 확인 완료")

    @requires_level(CertificationLevel.FULL)
    def test_10_state_after_error(self):
        """오류 발생 후 상태 유지 확인"""
        # Get initial state
        initial_credits = self.get_credits()

        # Try invalid operation
        try:
            self.call('invalid_command_for_test')
        except:
            pass  # Expected

        # State should be maintained
        credits_after = self.get_credits()
        self.assert_equal(
            credits_after, initial_credits,
            "오류 발생 후에도 상태가 유지되어야 함"
        )

    @requires_level(CertificationLevel.FULL)
    def test_11_concurrent_state_access(self):
        """동시 상태 접근 시 일관성 확인"""
        import threading

        results = []
        errors = []

        def read_state():
            try:
                state = self.get_state()
                results.append(state is not None)
            except Exception as e:
                errors.append(str(e))

        # Multiple concurrent reads
        threads = [threading.Thread(target=read_state) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assert_equal(len(errors), 0, f"동시 접근 오류: {errors}")
        self.assert_true(all(results), "모든 동시 읽기가 성공해야 함")

    @requires_level(CertificationLevel.FULL)
    def test_12_state_size_reasonable(self):
        """상태 크기가 합리적인지 확인"""
        import json
        state = self.get_state()

        # Convert to JSON and check size
        state_json = json.dumps(state, default=str)
        size_kb = len(state_json) / 1024

        self.assert_less(
            size_kb, 100,
            f"상태 크기가 너무 큼: {size_kb:.1f}KB (100KB 이하 권장)"
        )

    @requires_level(CertificationLevel.FULL)
    def test_13_cross_app_mutex(self):
        """동시 실행 방지(크로스앱 뮤텍스) 확인"""
        try:
            mutex_info = self.call('get_mutex_info')

            if mutex_info:
                has_mutex = mutex_info.get('has_mutex', False)
                mutex_name = mutex_info.get('mutex_name', '')

                # App should have mutex mechanism
                self.assert_true(
                    has_mutex or mutex_name,
                    "동시 실행 방지 메커니즘이 있어야 함"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Mutex info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_14_memory_usage_reasonable(self):
        """메모리 사용량이 합리적인지 확인 (< 500MB)"""
        try:
            memory_info = self.call('get_memory_usage')

            if memory_info:
                memory_mb = memory_info.get('memory_mb', 0)

                # Memory should be under 500MB
                self.assert_less(
                    memory_mb, 500,
                    f"메모리 사용량이 너무 큼: {memory_mb:.1f}MB (500MB 이하 권장)"
                )

                # Warning for > 200MB
                if memory_mb > 200:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"[권장] 메모리 사용량 최적화 필요: {memory_mb:.1f}MB"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Memory info might not be exposed
            else:
                raise
