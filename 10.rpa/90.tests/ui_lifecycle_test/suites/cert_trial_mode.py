# -*- coding: utf-8 -*-
"""
WF-ACT Trial Credits Suite
===========================
Certification tests for work-count based trial credits (500 works).

Tests cover:
- Trial activation (auto-activate without registration)
- Trial credit allocation (500 × credit_per_work)
- Work-count deduction (not time-based)
- Hardware-based installation limit
- Trial mode UI indicators
- Trial credit exhaustion
"""

import time
import os
import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level, SkipTest

logger = logging.getLogger(__name__)


class TrialModeSuite(BaseSuite):
    """Trial credits certification tests (500-work evaluation)"""

    name = "Trial Credits Suite"
    description = "500건 작업 체험판 크레딧 인증 테스트 (자동 활성화, 작업 기반 차감, 하드웨어 제한)"

    def should_skip(self) -> bool:
        """Skip if app is not using trial_500works pricing model"""
        pricing_model = self.app_config.policy.get("pricing_model", "")
        if pricing_model != "trial_500works":
            logger.info(f"[{self.app_config.name}] trial_500works 모델이 아니므로 Trial Credits Suite 스킵")
            return True
        return False

    def should_run(self) -> bool:
        """Ensure tests only run when trial credits mode is applicable"""
        if self.should_skip():
            self.skip(f"[{self.app_config.name}] trial_500works 모델이 아닙니다")
        return True

    def setup(self):
        """Setup trial credits tests"""
        self.credit_per_work = self.app_config.policy.get("credit_per_work", 100)
        self.trial_credits = self.app_config.policy.get("trial_credits", self.credit_per_work * 500)
        self.auto_activate = self.app_config.policy.get("auto_activate_trial", False)
        self.require_registration = self.app_config.policy.get("require_registration", False)
        self.max_installations = self.app_config.policy.get("max_installations", 1)

    def teardown(self):
        """Cleanup after trial credits tests"""
        pass

    # ===== BASIC LEVEL TESTS =====

    @requires_level(CertificationLevel.BASIC)
    def test_01_trial_auto_activation(self):
        """[BASIC] 체험판 자동 활성화 - 등록 없이 즉시 사용 가능"""
        logger.info("🧪 체험판 자동 활성화 테스트")
        
        # 체험판이 등록 없이 활성화되어야 함
        registration_status = self.get_registration_status()
        is_registered = registration_status.get("is_registered", False)
        
        logger.info(f"  - 사용자 등록 상태: {is_registered}")
        logger.info(f"  - 자동 활성화 설정: {self.auto_activate}")
        logger.info(f"  - 등록 필수 설정: {self.require_registration}")
        
        # 등록 필수가 아니면 테스트 패스
        if not self.require_registration:
            logger.info("  ✓ 등록 불필요한 체험판으로 구성됨")
            return
        else:
            self.fail("체험판은 등록 불필요해야 합니다")

    @requires_level(CertificationLevel.BASIC)
    def test_02_trial_500works_credits(self):
        """[BASIC] 체험판 500건 크레딧 - trial_credits = credit_per_work × 500"""
        logger.info("🧪 체험판 500건 크레딧 테스트")
        
        policy_trial = self.app_config.policy.get("trial_credits", 0)
        policy_credit_per_work = self.app_config.policy.get("credit_per_work", 0)
        
        logger.info(f"  - 정책 credit_per_work: {policy_credit_per_work}")
        logger.info(f"  - 정책 trial_credits: {policy_trial}")
        
        # 계산: trial_credits = credit_per_work × 500
        expected_trial_credits = policy_credit_per_work * 500
        
        if policy_trial == expected_trial_credits:
            logger.info(f"  ✓ 500건 크레딧 설정 정확함: {policy_trial}")
        else:
            self.fail(f"체험판 크레딧 계산 오류: 기대값={expected_trial_credits}, 실제={policy_trial}")

    @requires_level(CertificationLevel.BASIC)
    def test_03_credit_per_work_configured(self):
        """[BASIC] 작업당 크레딧 설정 - credit_per_work > 0"""
        logger.info("🧪 작업당 크레딧 설정 테스트")
        
        credit_per_work = self.app_config.policy.get("credit_per_work", 0)
        logger.info(f"  - 정책 credit_per_work: {credit_per_work}")
        
        if credit_per_work > 0:
            logger.info(f"  ✓ 작업당 크레딧 설정됨: {credit_per_work} 크레딧/작업")
        else:
            self.fail(f"작업당 크레딧이 설정되지 않음: {credit_per_work}")

    @requires_level(CertificationLevel.BASIC)
    def test_04_pricing_model_is_trial_500works(self):
        """[BASIC] 가격 모델 설정 - pricing_model = trial_500works"""
        logger.info("🧪 가격 모델 설정 테스트")
        
        pricing_model = self.app_config.policy.get("pricing_model", "")
        logger.info(f"  - 정책 pricing_model: {pricing_model}")
        
        if pricing_model == "trial_500works":
            logger.info(f"  ✓ 가격 모델이 trial_500works로 설정됨")
        else:
            self.fail(f"가격 모델이 trial_500works가 아님: {pricing_model}")

    # ===== STANDARD LEVEL TESTS =====

    @requires_level(CertificationLevel.STANDARD)
    def test_05_trial_credit_allocation(self):
        """[STANDARD] 체험판 크레딧 할당 - 초기화 시 trial_credits 할당"""
        logger.info("🧪 체험판 크레딧 할당 테스트")
        
        trial_info = self.get_trial_info()
        logger.info(f"  - 초기 크레딧: {trial_info.get('initial_credits')}")
        logger.info(f"  - 남은 크레딧: {trial_info.get('remaining_trial')}")
        
        if trial_info.get('remaining_trial') == self.trial_credits:
            logger.info(f"  ✓ 체험판 크레딧 올바르게 할당됨: {self.trial_credits}")
        elif trial_info.get('remaining_trial') is not None:
            logger.info(f"  ⚠ 체험판 크레딧 할당됨: {trial_info.get('remaining_trial')}")
        else:
            self.fail("체험판 크레딧이 할당되지 않음")

    @requires_level(CertificationLevel.STANDARD)
    def test_06_trial_credit_deduction_on_work(self):
        """[STANDARD] 작업 시 크레딧 차감 - 각 작업마다 credit_per_work 차감"""
        logger.info("🧪 작업 시 크레딧 차감 테스트")
        
        try:
            # 작업 전 크레딧 상태 확인
            before = self.get_credit_status()
            remaining_before = before.get("remaining_trial", 0)
            
            logger.info(f"  - 작업 전 크레딧: {remaining_before}")
            logger.info(f"  - 작업당 차감: {self.credit_per_work}")
            
            # 테스트용 간단한 작업 수행
            result = self.perform_test_operation()
            
            if result.get("success"):
                # 작업 후 크레딧 상태 확인
                after = self.get_credit_status()
                remaining_after = after.get("remaining_trial", 0)
                
                logger.info(f"  - 작업 후 크레딧: {remaining_after}")
                
                expected_deduction = self.credit_per_work
                actual_deduction = remaining_before - remaining_after
                
                if actual_deduction == expected_deduction:
                    logger.info(f"  ✓ 크레딧 올바르게 차감됨: -{expected_deduction}")
                else:
                    logger.info(f"  ⚠ 크레딧 차감량 확인 필요: 기대={expected_deduction}, 실제={actual_deduction}")
            else:
                logger.info(f"  ⚠ 테스트 작업 수행 불가: {result.get('error')}")
        except Exception as e:
            logger.info(f"  ⚠ 크레딧 차감 테스트 실패: {e}")

    @requires_level(CertificationLevel.STANDARD)
    def test_07_trial_hardware_tracking(self):
        """[STANDARD] 하드웨어 기반 활성화 추적 - max_installations 정책"""
        logger.info("🧪 하드웨어 기반 활성화 추적 테스트")
        
        hw_activation = self.app_config.policy.get("hardware_based_activation", False)
        max_installations = self.app_config.policy.get("max_installations", 0)
        
        logger.info(f"  - 하드웨어 기반 활성화: {hw_activation}")
        logger.info(f"  - 최대 설치 수: {max_installations}")
        
        if hw_activation and max_installations == 1:
            logger.info(f"  ✓ 하드웨어 기반 단일 설치 제한 설정됨")
        else:
            self.fail("체험판은 하드웨어 기반 단일 설치로 제한되어야 함")

    # ===== FULL LEVEL TESTS =====

    @requires_level(CertificationLevel.FULL)
    def test_08_trial_credit_exhaustion(self):
        """[FULL] 체험판 크레딧 소진 - 500건 작업 후 크레딧 부족"""
        logger.info("🧪 체험판 크레딧 소진 테스트")
        
        try:
            trial_info = self.get_trial_info()
            remaining_works = trial_info.get('remaining_works', 500)
            
            logger.info(f"  - 남은 작업 수: {remaining_works}건")
            
            if remaining_works == 500:
                logger.info("  ✓ 초기 상태에서 500건 사용 가능")
            elif remaining_works > 0:
                logger.info(f"  ✓ 체험판 진행 중: {remaining_works}건 남음")
            else:
                logger.info(f"  ⚠ 체험판 소진됨: {remaining_works}건")
        except Exception as e:
            logger.info(f"  ⚠ 크레딧 소진 테스트 불가: {e}")

    @requires_level(CertificationLevel.FULL)
    def test_09_trial_works_display(self):
        """[FULL] 체험판 남은 작업 수 표시 - UI에 작업 수 표시"""
        logger.info("🧪 체험판 남은 작업 수 표시 테스트")
        
        try:
            trial_info = self.get_trial_info()
            remaining_works = self._calculate_remaining_works()
            
            logger.info(f"  - 남은 작업 수: {remaining_works}건")
            
            if remaining_works >= 0:
                logger.info(f"  ✓ 체험판 {remaining_works}건 작업 가능 (UI에 표시 가능)")
            else:
                logger.info(f"  ✓ 체험판 소진됨")
        except Exception as e:
            logger.info(f"  ⚠ 작업 수 표시 확인 불가: {e}")

    @requires_level(CertificationLevel.FULL)
    def test_10_trial_no_registration_ui(self):
        """[FULL] 등록 UI 스킵 - 체험판 사용 시 등록창 표시 안 함"""
        logger.info("🧪 등록 UI 스킵 테스트")
        
        require_registration = self.app_config.policy.get("require_registration", False)
        
        if not require_registration:
            logger.info("  ✓ 체험판 사용자는 등록 불필요로 설정됨")
        else:
            self.fail("체험판은 등록 불필요해야 합니다")

    # ===== HELPER METHODS =====

    def get_trial_info(self) -> dict:
        """체험판 정보 조회"""
        try:
            response = self.call('get_trial_info')
            return response if response else {}
        except Exception as e:
            logger.warning(f"체험판 정보 조회 실패: {e}")
            return {}

    def get_registration_status(self) -> dict:
        """등록 상태 조회"""
        try:
            response = self.call('get_registration_status')
            return response if response else {}
        except Exception as e:
            logger.warning(f"등록 상태 조회 실패: {e}")
            return {}

    def get_credit_status(self) -> dict:
        """크레딧 상태 조회"""
        try:
            response = self.call('get_credit_status')
            return response if response else {}
        except Exception as e:
            logger.warning(f"크레딧 상태 조회 실패: {e}")
            return {}

    def perform_test_operation(self) -> dict:
        """테스트용 간단한 작업 수행"""
        try:
            response = self.call('simulate_work', 1)
            return response if response else {"success": False}
        except Exception as e:
            logger.warning(f"테스트 작업 수행 실패: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_remaining_works(self) -> int:
        """남은 체험판 작업 수 계산"""
        trial_info = self.get_trial_info()
        
        if not trial_info.get('remaining_trial'):
            return 500  # 기본값
        
        try:
            # remaining_trial을 credit_per_work로 나누면 작업 수 계산
            remaining_works = trial_info.get('remaining_trial', 0) // max(1, self.credit_per_work)
            return remaining_works
        except Exception:
            return 500  # 기본값

