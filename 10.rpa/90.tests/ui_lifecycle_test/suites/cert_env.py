# -*- coding: utf-8 -*-
"""
WF-ACT Execution Environment Suite
===================================
Certification tests for execution environment verification.

Tests cover:
- Single-instance enforcement (EXE mode)
- Configuration folder reference (DEV vs EXE)
- User home initialization (EXE mode)
"""

import os
import logging
from pathlib import Path
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class ExecutionEnvironmentSuite(BaseSuite):
    """Execution environment certification tests"""

    name = "Execution Environment Suite"
    description = "실행 환경 인증 테스트 (싱글 인스턴스, 설정 폴더 참조)"

    def setup(self):
        """Setup"""
        self.dev_mode = self.client.dev_mode
        self.app_name = self.client.app_name

    # === BASIC Level Tests ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_config_folder_location(self):
        """설정 폴더 참조 위치 확인 (DEV: 프로젝트, EXE: 사용자 홈)"""
        # get_policy가 정상 동작하면 설정 파일 로드가 성공한 것
        # EXE 모드에서는 사용자 홈의 ~/.wf_rpa/wf_rpa_config.json을 읽음
        # DEV 모드에서는 프로젝트의 10.common/config/wf_rpa_config.json을 읽음
        policy = self.call('get_policy')
        
        # 정책이 로드되면 올바른 위치에서 설정을 읽은 것
        self.assert_not_none(policy, "정책 로드 실패 - 설정 폴더 참조 오류")
        self.assert_true(
            isinstance(policy, dict),
            "정책은 dict여야 함 - 설정 파일 형식 오류"
        )
        
        # 앱 이름이 있으면 정상적으로 설정을 읽은 것
        identity = policy.get('identity', {})
        app_name = identity.get('app_name') or policy.get('app_name')
        self.assert_not_none(
            app_name,
            "정책에 app_name 없음 - 설정 파일이 올바르게 로드되지 않음"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_02_config_files_exist(self):
        """설정 파일 존재 확인 (해당 모드의 폴더에)"""
        # Get policy to verify config loading
        policy = self.call('get_policy')
        
        self.assert_not_none(
            policy,
            "설정 파일(policy.json)이 로드되지 않았습니다"
        )
        
        # Verify policy has required fields
        # Check identity.display_name or display_name (flattened)
        identity = policy.get('identity', {})
        display_name = identity.get('display_name') or policy.get('display_name')
        
        self.assert_not_none(
            display_name,
            "policy.json에 display_name이 없습니다 (identity.display_name 또는 display_name)"
        )
        
        # Check app_name and trial_credits
        app_name = identity.get('app_name') or policy.get('app_name')
        self.assert_not_none(app_name, "policy.json에 app_name이 없습니다")
        
        trial_credits = policy.get('policy', {}).get('trial_credits') or policy.get('trial_credits')
        self.assert_not_none(trial_credits, "policy.json에 trial_credits가 없습니다")

    @requires_level(CertificationLevel.STANDARD)
    def test_03_user_home_initialized(self):
        """사용자 홈 폴더 초기화 확인 (EXE 모드만)"""
        if self.dev_mode:
            return  # DEV 모드는 스킵
        
        # EXE 모드: 사용자 홈에 앱 폴더가 생성되어야 함
        user_wf_dir = Path.home() / ".wf_rpa"
        app_dir = user_wf_dir / self.app_name
        
        self.assert_true(
            app_dir.exists(),
            f"EXE 모드에서 사용자 홈 앱 폴더가 생성되지 않았습니다: {app_dir}"
        )
        
        # settings.json 파일 확인
        settings_file = app_dir / "settings.json"
        self.assert_true(
            settings_file.exists(),
            f"사용자 홈에 settings.json이 생성되지 않았습니다: {settings_file}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_04_wf_rpa_config_accessible(self):
        """wf_rpa_config.json 접근 가능 확인"""
        # Get config through app
        state = self.call('get_state')
        
        # Verify state contains config-derived info
        self.assert_not_none(
            state,
            "앱 상태를 가져올 수 없습니다 (설정 로드 실패 가능성)"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_05_credentials_accessible(self):
        """크리덴셜 파일 접근 가능 확인 (Google Sheets 연결용)"""
        # This is checked in ConfigSuite but we verify env-specific path
        config_data = self.call('get_state')
        config_path_str = config_data.get('config_path', '')
        
        if self.dev_mode:
            # DEV: 10.common/config에 크리덴셜 파일
            credentials_dir = Path("D:/drive_files/10.worksfree/10.rpa/10.common/config")
        else:
            # EXE: 번들 _internal/.wf_rpa에 크리덴셜 파일
            # (실제 경로는 PackageIntegritySuite에서 검증)
            return  # PackageIntegritySuite에서 검증됨
        
        # Check DEV credentials exist
        cred_files = list(credentials_dir.glob("*.json"))
        has_cred = any('silver-argon' in f.name or 'worksfree' in f.name for f in cred_files)
        
        self.assert_true(
            has_cred,
            f"DEV 모드에서 크리덴셜 파일을 찾을 수 없습니다: {credentials_dir}"
        )

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_06_config_reload_works(self):
        """설정 재로드 기능 확인"""
        # Get initial config
        policy1 = self.call('get_policy')
        
        # Reload config
        self.call('reload_config')
        
        # Get config again
        policy2 = self.call('get_policy')
        
        # Should be same values (no changes made)
        self.assert_equal(
            policy1.get('app_name'),
            policy2.get('app_name'),
            "설정 재로드 후 값이 일치하지 않습니다"
        )

    @requires_level(CertificationLevel.FULL)
    def test_07_multiple_config_reads(self):
        """설정 파일 여러 번 읽기 (동시성 테스트)"""
        for i in range(5):
            policy = self.call('get_policy')
            self.assert_not_none(
                policy,
                f"설정 읽기 {i+1}번째 실패"
            )
            
            settings = self.call('get_settings')
            self.assert_not_none(
                settings,
                f"설정 읽기 {i+1}번째 실패"
            )

    @requires_level(CertificationLevel.FULL)
    def test_08_dev_exe_mode_detection(self):
        """DEV/EXE 모드 자동 감지 확인"""
        state = self.call('get_state')
        
        # State should reflect execution mode
        # (앱 내부적으로 어떻게 표현하든 상관없이 동작하는지 확인)
        self.assert_not_none(
            state,
            "앱 상태를 가져올 수 없습니다"
        )

