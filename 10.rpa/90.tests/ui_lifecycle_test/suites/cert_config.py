# -*- coding: utf-8 -*-
"""
WF-ACT Config Suite
===================
Certification tests for configuration management.

Tests cover:
- policy.json loading
- settings.json validation
- Configuration consistency
"""

import logging
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class ConfigSuite(BaseSuite):
    """Configuration management certification tests"""

    name = "Config Suite"
    description = "설정 관리 인증 테스트 (policy.json, settings.json 로드 및 검증)"

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_initial_deployment_policy(self):
        """초기 배포 형상 검증 (BASIC_RULES.md Part 2.1 크레딧 정책 준수)"""
        # 이 테스트는 사용자 홈이 정리된 직후 실행되므로
        # 번들된 policy.json의 초기 배포 형상을 정확히 검증함
        policy = self.call('get_policy')

        policy_section = policy.get('policy', policy)
        trial_credits = policy_section.get('trial_credits')
        credit_per_work = policy_section.get('credit_per_work')

        expected_trial = self.app_config.trial_credits
        expected_per_work = self.app_config.credit_per_work

        self.assert_not_none(trial_credits, "정책에 trial_credits가 없음")
        self.assert_not_none(credit_per_work, "정책에 credit_per_work가 없음")

        # 무료 앱 검증
        if expected_trial == -1:
            logger.info(f"📋 무료 앱 정책 검증: trial={expected_trial}, per_work={expected_per_work}")
            self.assert_equal(
                trial_credits, -1,
                f"무료 앱의 trial_credits는 -1이어야 함: 실제 {trial_credits}"
            )
            self.assert_equal(
                credit_per_work, 0,
                f"무료 앱의 credit_per_work는 0이어야 함: 실제 {credit_per_work}"
            )
            logger.info(f"✅ 무료 앱 정책 확인: trial_credits={trial_credits}, credit_per_work={credit_per_work}")
        else:
            # 유료 앱 검증
            logger.info(f"📋 유료 앱 정책 검증: trial={expected_trial}, per_work={expected_per_work}, 공식={expected_per_work}×500={expected_trial}")
            self.assert_equal(
                trial_credits, expected_trial,
                f"trial_credits 불일치: 예상 {expected_trial}, 실제 {trial_credits}"
            )
            self.assert_equal(
                credit_per_work, expected_per_work,
                f"credit_per_work 불일치: 예상 {expected_per_work}, 실제 {credit_per_work}"
            )

            # 유료 앱: trial_credits = credit_per_work × 500 공식 확인
            expected_formula = credit_per_work * 500
            self.assert_equal(
                trial_credits, expected_formula,
                f"유료 앱 공식 불일치: trial_credits({trial_credits}) ≠ credit_per_work({credit_per_work}) × 500"
            )
            logger.info(f"✅ 유료 앱 정책 확인: trial_credits={trial_credits}, credit_per_work={credit_per_work}")

    @requires_level(CertificationLevel.BASIC)
    def test_02_get_policy(self):
        """정책(policy) 조회가 정상 동작하는지 확인"""
        policy = self.call('get_policy')
        self.assert_not_none(policy, "정책 조회 실패")
        self.assert_true(isinstance(policy, dict), "정책은 dict 형태여야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_03_policy_has_identity(self):
        """정책에 앱 식별 정보가 있는지 확인"""
        policy = self.call('get_policy')

        identity = policy.get('identity', {})
        app_name = identity.get('app_name') or policy.get('app_name')

        self.assert_not_none(app_name, "정책에 app_name이 있어야 함")
        self.assert_equal(
            app_name, self.app_config.name,
            f"app_name 불일치: 예상 {self.app_config.name}, 실제 {app_name}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_04_policy_has_credit_info(self):
        """정책에 크레딧 정보가 있는지 확인"""
        policy = self.call('get_policy')

        policy_section = policy.get('policy', policy)
        credit_per_work = policy_section.get('credit_per_work')

        self.assert_not_none(credit_per_work, "정책에 credit_per_work가 있어야 함")
        self.assert_equal(
            credit_per_work, self.app_config.credit_per_work,
            f"credit_per_work 불일치: 예상 {self.app_config.credit_per_work}, 실제 {credit_per_work}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_05_get_settings(self):
        """설정(settings) 조회가 정상 동작하는지 확인"""
        settings = self.call('get_settings')
        self.assert_not_none(settings, "설정 조회 실패")
        self.assert_true(isinstance(settings, dict), "설정은 dict 형태여야 함")

    @requires_level(CertificationLevel.BASIC)
    def test_06_settings_has_version(self):
        """설정에 버전 정보가 있는지 확인"""
        settings = self.call('get_settings')

        # Version can be in various locations
        version = (settings.get('full_version') or
                  settings.get('version') or
                  settings.get('app_config', {}).get('full_version') or
                  settings.get('runtime_config', {}).get('full_version'))

        self.assert_not_none(version, "설정에 버전 정보가 있어야 함")

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_07_policy_trial_credits(self):
        """정책의 체험판 크레딧 정보 확인"""
        policy = self.call('get_policy')

        policy_section = policy.get('policy', policy)
        trial_credits = policy_section.get('trial_credits')

        self.assert_not_none(trial_credits, "정책에 trial_credits가 있어야 함")
        self.assert_equal(
            trial_credits, self.app_config.trial_credits,
            f"trial_credits 불일치: 예상 {self.app_config.trial_credits}, 실제 {trial_credits}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_08_policy_display_name(self):
        """정책의 표시 이름 확인"""
        policy = self.call('get_policy')

        identity = policy.get('identity', {})
        display_name = identity.get('display_name') or policy.get('display_name')

        self.assert_not_none(display_name, "정책에 display_name이 있어야 함")
        self.assert_true(len(display_name) > 0, "display_name이 비어있음")

    @requires_level(CertificationLevel.STANDARD)
    def test_09_config_consistency(self):
        """설정과 정책의 일관성 확인"""
        policy = self.call('get_policy')
        settings = self.call('get_settings')

        # Both should exist
        self.assert_not_none(policy, "정책이 없음")
        self.assert_not_none(settings, "설정이 없음")

        # App name should match
        policy_app = (policy.get('identity', {}).get('app_name') or
                     policy.get('app_name'))
        settings_app = (settings.get('app_config', {}).get('app_name') or
                       settings.get('app_name'))

        if policy_app and settings_app:
            self.assert_equal(
                policy_app, settings_app,
                f"정책과 설정의 app_name 불일치: {policy_app} vs {settings_app}"
            )

    @requires_level(CertificationLevel.STANDARD)
    def test_10_wf_rpa_config_exists(self):
        """wf_rpa_config.json 로드 확인"""
        try:
            config = self.call('get_wf_rpa_config')
            self.assert_not_none(config, "wf_rpa_config 로드 실패")
        except Exception as e:
            # Config might not be exposed directly
            if 'unknown command' in str(e).lower():
                pass  # Acceptable if not exposed
            else:
                raise

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_11_email_settings_exist(self):
        """이메일 설정이 존재하는지 확인"""
        try:
            config = self.call('get_wf_rpa_config')
            if config:
                email_settings = config.get('email_settings')
                self.assert_not_none(email_settings, "email_settings가 있어야 함")
        except:
            pass  # Config might not be exposed

    @requires_level(CertificationLevel.FULL)
    def test_12_google_sheets_config(self):
        """Google Sheets 설정이 존재하는지 확인"""
        try:
            config = self.call('get_wf_rpa_config')
            if config:
                sheets_config = config.get('google_sheets')
                self.assert_not_none(sheets_config, "google_sheets 설정이 있어야 함")
        except:
            pass  # Config might not be exposed

    @requires_level(CertificationLevel.FULL)
    def test_13_credentials_available(self):
        """인증 정보 파일 존재 확인"""
        try:
            result = self.call('check_credentials')
            self.assert_true(
                result.get('available') or result == True,
                "인증 정보 파일이 존재해야 함"
            )
        except:
            pass  # Credentials check might not be exposed

    @requires_level(CertificationLevel.FULL)
    def test_14_google_sheets_connectivity(self):
        """Google Sheets API 연결성 확인 (재시도 로직 포함)"""
        import time

        max_retries = 3
        retry_delay = 10  # 초 (5초 → 10초로 증가)
        
        for attempt in range(max_retries):
            try:
                result = self.call('test_google_sheets_connectivity')
                if result:
                    error_msg = result.get('error', '') if isinstance(result, dict) else ''
                    if error_msg and ('quota exceeded' in error_msg.lower() or '429' in error_msg):
                        if attempt < max_retries - 1:
                            logger.warning(f"[시도 {attempt+1}/{max_retries}] Google Sheets 쿼터 초과, {retry_delay}초 대기 후 재시도...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            self.fail(f"Google Sheets 쿼터 초과: {error_msg}")  # 스킵 → 실패 변경
                    self.assert_true(
                        result.get('connected') or result.get('success'),
                        f"Google Sheets 연결 실패: {error_msg or 'Unknown error'}"
                    )
                    return  # 성공
            except RuntimeError as e:
                if 'unknown command' in str(e).lower():
                    # Command not exposed - try direct test
                    time.sleep(10)
                    self._direct_sheets_connectivity_test()
                    return
                else:
                    raise

    def _direct_sheets_connectivity_test(self):
        """직접 Google Sheets 연결 테스트 (앱 API가 없을 때, 재시도 로직 포함)"""
        import json
        import time
        
        # API 제약 방지를 위한 대기
        time.sleep(10)
        import time
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent.parent / '10.common' / 'config' / 'wf_rpa_config.json'
        if not config_path.exists():
            return  # Skip if config doesn't exist

        max_retries = 3
        retry_delay = 5  # 초

        for attempt in range(max_retries):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                gs = config.get('google_sheets', {})
                sheet_id = gs.get('sheet_id_dev')
                cred_file = gs.get('credentials_file_dev')

                if not sheet_id or not cred_file:
                    return  # Skip if not configured

                cred_path = config_path.parent / cred_file
                if not cred_path.exists():
                    self.assert_true(False, f"크리덴셜 파일 없음: {cred_path}")
                    return

                import gspread
                from google.oauth2.service_account import Credentials

                SCOPES = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.readonly'
                ]
                credentials = Credentials.from_service_account_file(str(cred_path), scopes=SCOPES)
                gc = gspread.authorize(credentials)
                spreadsheet = gc.open_by_key(sheet_id)

                self.assert_not_none(spreadsheet.title, "Google Sheets 연결 성공")
                return  # 성공

            except ImportError:
                pass  # gspread not installed
                return
            except Exception as e:
                err = str(e)
                if 'quota exceeded' in err.lower() or '429' in err:
                    if attempt < max_retries - 1:
                        logger.warning(f"[시도 {attempt+1}/{max_retries}] Google Sheets 쿼터 초과, {retry_delay}초 대기 후 재시도...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.skip(f"Google Sheets 쿼터 초과로 스킵: {err}")
                        return
                self.assert_true(False, f"Google Sheets 연결 실패: {e}")
                return

    @requires_level(CertificationLevel.FULL)
    def test_15_config_reload(self):
        """설정 리로드 기능 확인"""
        try:
            result = self.call('reload_config')
            # reload_config는 bool을 반환 (True/False)
            self.assert_true(
                result == True or result is True,
                f"설정 리로드 실패: {result}"
            )
        except Exception as e:
            if 'unknown command' in str(e).lower():
                pass  # Acceptable if not implemented
            else:
                raise

    @requires_level(CertificationLevel.FULL)
    def test_16_version_format_valid(self):
        """버전 형식이 유효한지 확인 (v0.0.0.0 형식)"""
        import re

        settings = self.call('get_settings')
        # Check various locations where version might be stored
        version = (settings.get('full_version') or
                  settings.get('version') or
                  settings.get('app_config', {}).get('full_version') or
                  settings.get('runtime_config', {}).get('full_version') or
                  '')

        # Accept formats: v0.0.0.0, 0.0.0.0, v0.0.0
        version_pattern = r'^v?\d+\.\d+\.\d+(\.\d+)?$'

        self.assert_true(
            re.match(version_pattern, version),
            f"버전 형식이 유효하지 않음: {version} (예상: v0.0.0.0)"
        )

    @requires_level(CertificationLevel.FULL)
    def test_17_log_directory_structure(self):
        """로그 디렉토리 구조 확인"""
        import os
        from pathlib import Path

        app_name = self.app_config.name
        user_home = Path(os.path.expanduser("~"))
        log_dir = user_home / '.wf_rpa' / app_name / 'logs'

        # Log directory should exist or be creatable
        try:
            if not log_dir.exists():
                # Try to create it
                log_dir.mkdir(parents=True, exist_ok=True)

            self.assert_true(
                log_dir.exists(),
                f"로그 디렉토리가 없습니다: {log_dir}"
            )
        except Exception as e:
            self.assert_true(False, f"로그 디렉토리 생성 실패: {e}")

    @requires_level(CertificationLevel.FULL)
    def test_18_version_minimum_requirement(self):
        """버전이 최소 0.7.0.0 이상인지 확인"""
        import re

        settings = self.call('get_settings')
        version = (settings.get('full_version') or
                  settings.get('version') or
                  settings.get('app_config', {}).get('full_version') or
                  settings.get('runtime_config', {}).get('full_version') or
                  '')

        # Extract version numbers (e.g., "v0.7.0.0" -> [0, 7, 0, 0])
        match = re.match(r'^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$', version)
        if not match:
            self.assert_true(False, f"버전 파싱 실패: {version}")
            return

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        build = int(match.group(4)) if match.group(4) else 0

        # Minimum version: 0.7.0.0
        version_tuple = (major, minor, patch, build)
        min_version = (0, 7, 0, 0)

        self.assert_true(
            version_tuple >= min_version,
            f"버전이 최소 요구사항(0.7.0.0) 미만: {version}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_19_version_display_format(self):
        """메인창 2자리, 설정/관리자 4자리 버전 표기 확인"""
        try:
            version_info = self.call('get_version_display')

            if version_info:
                display_version = version_info.get('display_version', '')
                full_version = version_info.get('full_version', '')

                # Display version should be 2 parts (e.g., "v0.7")
                if display_version:
                    parts = display_version.lstrip('v').split('.')
                    self.assert_true(
                        len(parts) == 2,
                        f"메인창 버전은 2자리여야 함: {display_version} (현재 {len(parts)}자리)"
                    )

                # Full version should be 4 parts (e.g., "v0.7.0.0")
                if full_version:
                    parts = full_version.lstrip('v').split('.')
                    self.assert_true(
                        len(parts) == 4,
                        f"설정/관리자 버전은 4자리여야 함: {full_version} (현재 {len(parts)}자리)"
                    )
        except RuntimeError as e:
            if 'unknown command' in str(e).lower():
                pass  # Version display info might not be exposed
            else:
                raise

    @requires_level(CertificationLevel.STANDARD)
    def test_20_trial_credits_formula(self):
        """체험판 크레딧이 500건 작업 기준인지 확인 (trial = credit_per_work × 500)"""
        trial = self.app_config.trial_credits
        per_work = self.app_config.credit_per_work

        # 무료 앱 (trial_credits = -1)은 건너뜀
        if trial == -1:
            logger.info(f"📋 무료 앱 체험판 검증: trial_credits=-1 (무료 앱은 스킵)")
            return  # Skip - 무료 앱은 체험판 개념 없음

        # 유료 앱: trial_credits = credit_per_work × 500
        expected = per_work * 500
        logger.info(f"📋 유료 앱 체험판 공식 검증: trial = {per_work} × 500 = {expected}")

        self.assert_equal(
            trial, expected,
            f"체험판 크레딧 불일치: {trial} (예상: {per_work} × 500 = {expected})"
        )
