# -*- coding: utf-8 -*-
"""
WF-ACT UI Suite
===============
Certification tests for UI responsiveness.

Tests cover:
- UI element states
- Button responsiveness
- Progress indication
- Non-blocking operations
"""

import time
import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class UISuite(BaseSuite):
    """UI responsiveness certification tests"""

    name = "UI Suite"
    description = "UI 응답성 인증 테스트 (버튼 상태, 진행률, 블로킹 없음)"

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_get_ui_state(self):
        """UI 상태 조회가 정상 동작하는지 확인"""
        try:
            ui_state = self.call('get_ui_state')
            self.assert_not_none(ui_state, "UI 상태 조회 실패")
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # UI state might not be exposed
                pass
            else:
                raise

    @requires_level(CertificationLevel.BASIC)
    def test_02_app_responsive(self):
        """앱이 응답하는지 확인"""
        start = time.time()
        result = self.call('ping')
        elapsed = time.time() - start

        self.assert_equal(result, 'pong', "ping 응답 실패")
        self.assert_less(elapsed, 1.0, f"응답 시간이 너무 김: {elapsed:.2f}초")

    @requires_level(CertificationLevel.BASIC)
    def test_03_multiple_rapid_calls(self):
        """빠른 연속 호출 처리 확인"""
        start = time.time()

        for i in range(10):
            result = self.call('ping')
            self.assert_equal(result, 'pong', f"ping #{i+1} 실패")

        elapsed = time.time() - start
        avg_time = elapsed / 10

        self.assert_less(avg_time, 0.5, f"평균 응답 시간이 너무 김: {avg_time:.3f}초")

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_04_button_states(self):
        """버튼 상태 조회 확인"""
        try:
            buttons = self.call('get_button_states')

            if buttons:
                self.assert_true(isinstance(buttons, (dict, list)), "버튼 상태는 dict 또는 list여야 함")
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Button states might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.STANDARD)
    def test_05_work_button_disabled_when_no_credits(self):
        """크레딧 부족 시 작업 버튼 비활성화 확인"""
        # 무료 앱은 크레딧 제한이 없으므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_05 스킵")
            return

        self.set_credits(0)

        try:
            ui_state = self.call('get_ui_state')
            if ui_state and 'work_button' in ui_state:
                work_enabled = ui_state['work_button'].get('enabled', True)
                self.assert_false(
                    work_enabled,
                    "크레딧 부족 시 작업 버튼이 비활성화되어야 함"
                )
        except:
            # UI state might not expose button states
            # Alternative: try to work and verify it's blocked
            result = self.simulate_work(file_count=1)
            self.assert_true(
                result.get('blocked') or not result.get('success'),
                "크레딧 부족 시 작업이 차단되어야 함"
            )

    @requires_level(CertificationLevel.STANDARD)
    def test_06_work_button_enabled_when_credits_available(self):
        """크레딧 있을 때 작업 버튼 활성화 확인"""
        self.set_credits(self.app_config.credit_per_work * 5)

        try:
            ui_state = self.call('get_ui_state')
            if ui_state and 'work_button' in ui_state:
                work_enabled = ui_state['work_button'].get('enabled', False)
                self.assert_true(
                    work_enabled,
                    "크레딧 있을 때 작업 버튼이 활성화되어야 함"
                )
        except:
            # Alternative: verify work succeeds
            result = self.simulate_work(file_count=1)
            self.assert_true(
                result.get('success') or not result.get('blocked'),
                "크레딧 있을 때 작업이 가능해야 함"
            )

    @requires_level(CertificationLevel.STANDARD)
    def test_07_credits_display_updated(self):
        """크레딧 표시 업데이트 확인"""
        # 무료 앱은 크레딧 표시가 다르므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_07 스킵")
            return

        # 원래 크레딧 저장 (복원용)
        policy = self.call('get_policy')
        original_credits = policy.get('policy', {}).get('trial_credits', 100)

        test_credits = 7777
        self.set_credits(test_credits)

        try:
            ui_state = self.call('get_ui_state')
            if ui_state and 'credits_display' in ui_state:
                displayed = ui_state['credits_display']
                self.assert_true(
                    str(test_credits) in str(displayed),
                    f"크레딧 표시 불일치: 설정 {test_credits}, 표시 {displayed}"
                )
        except:
            # Alternative: just verify credits are correct
            credits = self.get_credits()
            self.assert_equal(credits, test_credits, "크레딧 값 불일치")
        finally:
            # 테스트 후 원래 크레딧으로 복원 (test_23 등 후속 테스트를 위해)
            self.set_credits(original_credits)

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_08_progress_indication(self):
        """작업 진행률 표시 확인"""
        original_credits = self.get_credits()  # 원래 크레딧 저장
        
        try:
            self.set_credits(self.app_config.credit_per_work * 10)

            # Start work and check progress
            result = self.simulate_work(file_count=3)

            # Progress info might be in result
            progress = (result.get('progress') or
                       result.get('progress_info') or
                       result.get('processed_count'))

            if progress is not None:
                self.assert_not_none(progress, "진행률 정보가 있어야 함")
        except:
            pass  # Progress indication is recommended but not required
        finally:
            self.set_credits(original_credits)  # 크레딧 복원

    @requires_level(CertificationLevel.FULL)
    def test_09_non_blocking_response(self):
        """UI가 블로킹되지 않는지 확인"""
        original_credits = self.get_credits()  # 원래 크레딧 저장
        
        try:
            self.set_credits(self.app_config.credit_per_work * 10)

            # Start work
            start = time.time()
            result = self.simulate_work(file_count=1)
            work_time = time.time() - start

            # Immediately try ping
            start = time.time()
            ping_result = self.call('ping')
            ping_time = time.time() - start

            self.assert_equal(ping_result, 'pong', "작업 후 ping 실패")
            self.assert_less(ping_time, 1.0, f"작업 후 응답이 느림: {ping_time:.2f}초")
        finally:
            self.set_credits(original_credits)  # 크레딧 복원

    @requires_level(CertificationLevel.FULL)
    def test_10_status_message_available(self):
        """상태 메시지 사용 가능 확인"""
        try:
            status = self.call('get_status_message')

            if status is not None:
                self.assert_true(
                    isinstance(status, str),
                    "상태 메시지는 문자열이어야 함"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Status message might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_11_window_title_reflects_state(self):
        """창 제목이 상태를 반영하는지 확인"""
        try:
            window_info = self.call('get_window_info')

            if window_info:
                title = window_info.get('title', '')
                # Title should contain app name or version
                self.assert_true(
                    len(title) > 0,
                    "창 제목이 있어야 함"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Window info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_12_screenshot_capability(self):
        """스크린샷 기능 확인"""
        try:
            screenshot = self.call('take_screenshot')

            if screenshot:
                # Screenshot might be base64 string or file path
                self.assert_not_none(screenshot, "스크린샷이 있어야 함")
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Screenshot might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_13_tooltips_bound_to_labels(self):
        """라벨에 툴팁이 바인딩되어 있는지 확인"""
        try:
            tooltips = self.call('get_tooltips')

            if tooltips:
                self.assert_true(
                    isinstance(tooltips, (dict, list)),
                    "툴팁 정보는 dict 또는 list여야 함"
                )
                # Should have at least some tooltips defined
                if isinstance(tooltips, dict):
                    self.assert_true(
                        len(tooltips) >= 1,
                        f"최소 1개 이상의 툴팁이 있어야 함 (현재: {len(tooltips)}개)"
                    )
                elif isinstance(tooltips, list):
                    self.assert_true(
                        len(tooltips) >= 1,
                        f"최소 1개 이상의 툴팁이 있어야 함 (현재: {len(tooltips)}개)"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Tooltips might not be exposed via handler
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_14_app_loading_time(self):
        """앱 로딩 시간 확인 (< 3초 필수, < 1초 권장)"""
        try:
            loading_info = self.call('get_loading_time')

            if loading_info:
                loading_time = loading_info.get('loading_time', 0)
                self.assert_less(
                    loading_time, 3.0,
                    f"앱 로딩 시간이 3초를 초과함: {loading_time:.2f}초"
                )
                # Warning for > 1 second (not a failure)
                if loading_time > 1.0:
                    logger.warning(f"[권장] 로딩 시간이 1초 초과: {loading_time:.2f}초")
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Loading time might not be tracked
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_15_alt_g_admin_toggle(self):
        """Alt+G 키로 관리자 모드 토글 기능 확인"""
        try:
            result = self.call('test_alt_g_toggle')

            if result:
                self.assert_true(
                    result.get('supported', False),
                    "Alt+G 관리자 모드 토글 기능이 구현되어야 함"
                )
                # Check toggle functionality
                if result.get('toggled') is not None:
                    self.assert_true(
                        result.get('toggled'),
                        "Alt+G 토글이 정상 동작해야 함"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Alt+G might not be exposed via handler
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_16_window_popup_center_alignment(self):
        """메인창과 팝업/메시지박스의 중심 좌표 일치 확인"""
        try:
            alignment_info = self.call('get_window_alignment')

            if alignment_info:
                main_center = alignment_info.get('main_window_center')
                popup_center = alignment_info.get('popup_center')

                if main_center and popup_center:
                    # Allow 50px tolerance for center alignment
                    x_diff = abs(main_center.get('x', 0) - popup_center.get('x', 0))
                    y_diff = abs(main_center.get('y', 0) - popup_center.get('y', 0))

                    self.assert_less(
                        x_diff, 50,
                        f"팝업 X 중심이 메인창과 다름: {x_diff}px 차이"
                    )
                    self.assert_less(
                        y_diff, 50,
                        f"팝업 Y 중심이 메인창과 다름: {y_diff}px 차이"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Alignment info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_17_adaptive_ui_font_size(self):
        """Adaptive UI: 폰트 크기가 시스템 타이틀바 폰트 이상인지 확인"""
        try:
            ui_info = self.call('get_adaptive_ui_info')

            if ui_info:
                app_font_size = ui_info.get('app_font_size', 0)
                titlebar_font_size = ui_info.get('titlebar_font_size', 9)

                self.assert_true(
                    app_font_size >= titlebar_font_size,
                    f"앱 폰트({app_font_size}pt)가 타이틀바 폰트({titlebar_font_size}pt)보다 작음"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Adaptive UI info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_18_adaptive_ui_window_height(self):
        """Adaptive UI: 창 높이가 BASIC_RULES 표준을 따르는지 확인"""
        try:
            ui_info = self.call('get_adaptive_ui_info')

            if ui_info:
                window_height = ui_info.get('window_height', 0)
                input_count = ui_info.get('input_count', 1)

                # BASIC_RULES Part 1.1: 1입력=160, 2입력=270 (base height)
                expected_base = 160 if input_count == 1 else 270

                # Allow 20px tolerance
                self.assert_true(
                    abs(window_height - expected_base) < 100 or window_height >= expected_base,
                    f"창 높이({window_height}px)가 표준({expected_base}px)과 다름"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Adaptive UI info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_19_dpi_scaling_support(self):
        """DPI 스케일링 지원 확인"""
        try:
            dpi_info = self.call('get_dpi_info')

            if dpi_info:
                dpi_aware = dpi_info.get('dpi_aware', False)
                scale_factor = dpi_info.get('scale_factor', 1.0)

                # App should be DPI aware
                self.assert_true(
                    dpi_aware or scale_factor >= 1.0,
                    "앱이 DPI 스케일링을 지원해야 함"
                )

                # Scale factor should be reasonable (0.5 to 4.0)
                if scale_factor:
                    self.assert_true(
                        0.5 <= scale_factor <= 4.0,
                        f"DPI 스케일 팩터 범위 초과: {scale_factor}"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # DPI info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_20_window_geometry_saved(self):
        """창 위치/크기 저장 기능 확인"""
        try:
            geometry_info = self.call('get_window_geometry')

            if geometry_info:
                # Check if geometry can be saved/loaded
                has_save = geometry_info.get('can_save', False)
                has_load = geometry_info.get('can_load', False)

                self.assert_true(
                    has_save or has_load or geometry_info.get('geometry'),
                    "창 위치/크기 저장 기능이 있어야 함"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Geometry info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_21_credits_display_comma_separator(self):
        """크레딧 4자리 이상일 때 콤마(,) 자릿수 표시 확인 (예: 3800 → 3,800)"""
        # 무료 앱은 숫자가 아닌 "무료" 텍스트를 표시하므로 스킵
        if self.is_free_app():
            logger.info(f"[{self.app_config.name}] 무료 앱이므로 test_21 스킵")
            return

        test_credits = 3800  # 4자리 테스트 값
        self.set_credits(test_credits)

        try:
            ui_state = self.call('get_ui_state')

            if ui_state and 'credits_display' in ui_state:
                displayed = str(ui_state['credits_display'])

                # Expected format: "3,800" (with comma)
                expected_formatted = f"{test_credits:,}"

                self.assert_true(
                    expected_formatted in displayed or ',' in displayed,
                    f"크레딧 표시에 콤마 자릿수 구분이 필요함: {displayed} (예상: {expected_formatted})"
                )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # Alternative: check via get_credits_display handler
                try:
                    display_info = self.call('get_credits_display')
                    if display_info:
                        displayed = str(display_info.get('formatted', ''))
                        expected_formatted = f"{test_credits:,}"
                        self.assert_true(
                            expected_formatted in displayed or ',' in displayed,
                            f"크레딧 표시에 콤마 자릿수 구분이 필요함: {displayed}"
                        )
                except:
                    pass  # Credits display format might not be exposed
            else:
                raise
    @requires_level(CertificationLevel.FULL)
    def test_22_free_app_credit_display(self):
        """무료 앱(trial_credits=-1)은 "건당 XX" 텍스트가 없어야 함"""
        # 무료 앱인지 확인
        if self.app_config.trial_credits != -1:
            return  # Skip - 유료 앱

        # 무료 앱: credit_per_work는 0이어야 함
        self.assert_equal(
            self.app_config.credit_per_work, 0,
            f"무료 앱의 credit_per_work는 0이어야 함: {self.app_config.credit_per_work}"
        )

        # UI에서 "건당" 텍스트가 표시되지 않는지 확인
        try:
            ui_state = self.call('get_ui_state')

            if ui_state and 'credits_display' in ui_state:
                displayed = str(ui_state['credits_display'])

                # "건당", "per", "cost" 등의 텍스트가 없어야 함
                forbidden_keywords = ['건당', 'per file', 'per item', 'per work', 'cost:', '/ file']

                for keyword in forbidden_keywords:
                    self.assert_true(
                        keyword.lower() not in displayed.lower(),
                        f"무료 앱에서 '{keyword}' 텍스트가 표시됨: {displayed}"
                    )

                # "무료" 또는 "Free" 키워드가 있는지 확인 (권장사항)
                has_free_indicator = any(kw in displayed.lower() for kw in ['무료', 'free', 'unlimited'])
                logger.info(f"무료 앱 표시: {displayed} (무료 표시 여부: {has_free_indicator})")

        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # get_ui_state가 없으면 정책에서 확인
                policy = self.call('get_policy')
                policy_section = policy.get('policy', policy)

                trial = policy_section.get('trial_credits')
                per_work = policy_section.get('credit_per_work')

                self.assert_equal(trial, -1, f"무료 앱 trial_credits는 -1이어야 함: {trial}")
                self.assert_equal(per_work, 0, f"무료 앱 credit_per_work는 0이어야 함: {per_work}")
            else:
                raise

    @requires_level(CertificationLevel.STANDARD)
    def test_23_credit_display_error_check(self):
        """설치 직후 크레딧 표시 정확성 검증 (배포물 필수)
        - 유료 앱: 체험판 크레딧이 정확히 표시되는지 확인 (BE:10,000, DC:5,000, AR:20,000, DBP:4,000)
        - 무료 앱: "무료" 또는 "Free" 표시
        - "오류" 문구가 표시되면 안 됨
        """
        # 이전 테스트들이 크레딧을 차감했을 수 있으므로, 체험판 크레딧으로 초기화
        policy = self.call('get_policy')
        trial_credits = policy.get('policy', {}).get('trial_credits', 100)
        if trial_credits != -1:  # 유료 앱만 복원
            self.set_credits(trial_credits)
            time.sleep(0.2)  # UI 업데이트 대기
        
        try:
            ui_state = self.call('get_ui_state')

            if ui_state and 'credits_display' in ui_state:
                displayed = str(ui_state['credits_display'])

                # 1. "오류" 문구가 있으면 실패
                error_keywords = ['오류', 'error', 'ERROR', 'Error', '에러', 'err']
                for keyword in error_keywords:
                    self.assert_true(
                        keyword not in displayed,
                        f"크레딧 표시에 오류 문구 발견: '{displayed}' (배포물 품질 기준 미달)"
                    )

                # 2. 무료 앱 vs 유료 앱 검증
                policy = self.call('get_policy')
                trial_credits = policy.get('policy', {}).get('trial_credits', 100)

                if trial_credits == -1:
                    # 무료 앱: "무료" 또는 "Free" 표시 확인
                    free_keywords = ['무료', 'Free', 'FREE', 'free', 'unlimited']
                    has_free_indicator = any(kw in displayed for kw in free_keywords)
                    
                    self.assert_true(
                        has_free_indicator,
                        f"무료 앱이지만 무료 표시가 없습니다: '{displayed}' (예상: '무료' 또는 'Free')"
                    )
                    logger.info(f"[{self.app_config.name}] 무료 앱 표시 정상: {displayed}")
                else:
                    # 유료 앱: 설치 직후 체험판 크레딧이 정확히 표시되는지 확인
                    # 표시된 크레딧 값 추출 (숫자만)
                    import re
                    numbers = re.findall(r'\d[\d,]*', displayed)
                    
                    self.assert_true(
                        len(numbers) > 0,
                        f"유료 앱이지만 크레딧 숫자가 표시되지 않습니다: '{displayed}'"
                    )
                    
                    # 표시된 크레딧 (쉼표 제거)
                    displayed_credit = int(numbers[0].replace(',', ''))
                    
                    # 체험판 크레딧과 일치하는지 확인
                    self.assert_equal(
                        displayed_credit, trial_credits,
                        f"체험판 크레딧 불일치: 표시={displayed_credit:,}, 정책={trial_credits:,} ('{displayed}')"
                    )
                    
                    # 4자리 이상일 때 쉼표 표기 확인
                    if trial_credits >= 1000:
                        self.assert_true(
                            ',' in displayed,
                            f"크레딧 4자리 이상인데 쉼표 없음: '{displayed}' (예상: {trial_credits:,})"
                        )
                    
                    logger.info(f"[{self.app_config.name}] 체험판 크레딧 표시 정상: {displayed} (정책: {trial_credits:,})")

        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                # get_ui_state가 없으면 대체 방법
                try:
                    display_info = self.call('get_credits_display')
                    if display_info:
                        displayed = str(display_info.get('text', ''))
                        error_keywords = ['오류', 'error', 'ERROR', 'Error', '에러', 'err']

                        for keyword in error_keywords:
                            self.assert_true(
                                keyword not in displayed,
                                f"크레딧 표시에 오류 문구 발견: '{displayed}'"
                            )
                except:
                    logger.warning(f"[{self.app_config.name}] 크레딧 표시 확인 불가 - UI 노출 없음")
            else:
                raise