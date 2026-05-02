# -*- coding: utf-8 -*-
"""
WF-ACT Package Integrity Suite
===============================
Certification tests for packaged exe integrity verification.

Tests cover:
- Bundled credentials file existence (RELEASE/DEV)
- _internal directory structure
- Bundle settings.json version accuracy
- Google Sheets actual connectivity
- NSIS installer existence
"""

import os
import json
import logging
from pathlib import Path
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class PackageIntegritySuite(BaseSuite):
    """Package integrity certification tests (EXE mode only)"""

    name = "Package Integrity Suite"
    description = "배포 패키지 완전성 인증 테스트 (exe 내부 파일, 크리덴셜, 버전 정보)"

    def fail(self, msg):
        """Fail test with message"""
        raise AssertionError(msg)

    def setup(self):
        """Setup - EXE mode only"""
        if self.client.dev_mode:
            logger.warning("[PackageIntegrity] Skipping - only runs in EXE mode")
            self.skip_all = True
            return

        self.skip_all = False

        # Get exe directory from client
        exe_path = self.client.config.exe_path
        if not exe_path or not exe_path.exists():
            logger.error(f"[PackageIntegrity] EXE not found: {exe_path}")
            self.skip_all = True
            return

        self.exe_dir = exe_path.parent
        self.internal_dir = self.exe_dir / "_internal"
        self.app_name = self.client.app_name

        logger.info(f"[PackageIntegrity] Testing package: {self.exe_dir}")

    # === BASIC Level Tests - Critical Files ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_internal_directory_exists(self):
        """_internal 디렉토리 존재 확인 (PyInstaller 번들)"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        self.assert_true(
            self.internal_dir.exists(),
            f"_internal 디렉토리가 없습니다: {self.internal_dir}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_02_wf_rpa_bundle_dir_exists(self):
        """_internal/.wf_rpa 번들 설정 디렉토리 존재 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        self.assert_true(
            wf_rpa_dir.exists(),
            f"번들 설정 디렉토리가 없습니다: {wf_rpa_dir}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_03_bundle_settings_json_exists(self):
        """_internal/.wf_rpa/{app}/settings.json 존재 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        settings_path = self.internal_dir / ".wf_rpa" / self.app_name / "settings.json"
        self.assert_true(
            settings_path.exists(),
            f"번들 settings.json이 없습니다: {settings_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_04_bundle_version_info_exists(self):
        """번들 settings.json에 full_version 정보 존재 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        settings_path = self.internal_dir / ".wf_rpa" / self.app_name / "settings.json"
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        runtime_config = settings.get('runtime_config', {})
        full_version = runtime_config.get('full_version')

        self.assert_not_none(
            full_version,
            "번들 settings.json에 full_version이 없습니다"
        )
        
        # Version format: vX.Y.Z.B
        self.assert_true(
            full_version.startswith('v') and len(full_version.split('.')) == 4,
            f"full_version 형식이 잘못되었습니다: {full_version} (예상: v1.0.0.1)"
        )

    # === STANDARD Level Tests - Credentials ===

    @requires_level(CertificationLevel.STANDARD)
    def test_05_release_credential_file_exists(self):
        """RELEASE 크리덴셜 파일 번들 포함 확인 (worksfree-*.json, 숨김 파일)"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        # Find worksfree-*.json in _internal/.wf_rpa (including hidden files)
        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        cred_files = list(wf_rpa_dir.glob("worksfree-*.json"))
        
        self.assert_true(
            len(cred_files) > 0,
            f"RELEASE 크리덴셜 파일이 번들에 포함되지 않았습니다: {wf_rpa_dir}"
        )

        # Verify file size (should be > 1KB for valid JSON)
        cred_file = cred_files[0]
        file_size = cred_file.stat().st_size
        self.assert_true(
            file_size > 1024,
            f"크리덴셜 파일이 너무 작습니다 (손상 가능성): {file_size} bytes"
        )
        
        # Verify file is hidden (Windows security best practice)
        import stat
        if hasattr(stat, 'FILE_ATTRIBUTE_HIDDEN'):
            is_hidden = bool(cred_file.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            if not is_hidden:
                logger.warning(f"보안 권장사항: 크리덴셜 파일을 숨김 처리하세요: {cred_file.name}")

    @requires_level(CertificationLevel.STANDARD)
    def test_06_dev_credential_file_exists(self):
        """DEV 크리덴셜 파일 번들 포함 확인 (silver-argon-*.json, 권장: 숨김)"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        # Find silver-argon-*.json in _internal/.wf_rpa (including hidden files)
        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        cred_files = list(wf_rpa_dir.glob("silver-argon-*.json"))
        
        self.assert_true(
            len(cred_files) > 0,
            f"DEV 크리덴셜 파일이 번들에 포함되지 않았습니다: {wf_rpa_dir}"
        )
        
        # Optional: Check if file is hidden (recommended for security)
        import stat
        if hasattr(stat, 'FILE_ATTRIBUTE_HIDDEN'):
            cred_file = cred_files[0]
            is_hidden = bool(cred_file.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
            if not is_hidden:
                logger.info(f"권장사항: DEV 크리덴셜 파일도 숨김 처리 권장: {cred_file.name}")

    @requires_level(CertificationLevel.STANDARD)
    def test_07_release_credential_valid_json(self):
        """RELEASE 크리덴셜 파일 JSON 유효성 검증"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        cred_files = list(wf_rpa_dir.glob("worksfree-*.json"))
        if not cred_files:
            self.fail("RELEASE 크리덴셜 파일이 없습니다")

        cred_file = cred_files[0]
        
        try:
            with open(cred_file, 'r', encoding='utf-8') as f:
                cred_data = json.load(f)
            
            # Google service account 필수 필드 확인
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in cred_data]
            
            self.assert_true(
                len(missing) == 0,
                f"크리덴셜 필수 필드 누락: {missing}"
            )
            
            # type이 service_account인지 확인
            self.assert_true(
                cred_data.get('type') == 'service_account',
                f"크리덴셜 타입이 잘못되었습니다: {cred_data.get('type')} (예상: service_account)"
            )

        except json.JSONDecodeError as e:
            self.fail(f"크리덴셜 파일 JSON 파싱 실패: {e}")

    @requires_level(CertificationLevel.STANDARD)
    def test_08_bundle_config_file_exists(self):
        """번들 wf_rpa_config.json 존재 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        config_path = self.internal_dir / ".wf_rpa" / "wf_rpa_config.json"
        
        self.assert_true(
            config_path.exists(),
            f"번들 wf_rpa_config.json이 없습니다: {config_path}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_09_bundle_config_sheet_ids(self):
        """번들 config에 sheet_id_release/dev 설정 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        config_path = self.internal_dir / ".wf_rpa" / "wf_rpa_config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        
        # sheet_id_release
        sheet_id_release = gs_config.get('sheet_id_release')
        self.assert_not_none(
            sheet_id_release,
            "번들 config에 sheet_id_release가 없습니다"
        )
        
        # sheet_id_dev
        sheet_id_dev = gs_config.get('sheet_id_dev')
        self.assert_not_none(
            sheet_id_dev,
            "번들 config에 sheet_id_dev가 없습니다"
        )

    # === FULL Level Tests - Installation & Actual Connectivity ===

    @requires_level(CertificationLevel.FULL)
    def test_10_nsis_installer_exists(self):
        """NSIS 설치 파일 존재 확인 ({app}_installer.exe)"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        # Installer is in parent directory
        version_dir = self.exe_dir.parent
        installer_name = f"{self.app_name}_installer.exe"
        installer_path = version_dir / installer_name

        self.assert_true(
            installer_path.exists(),
            f"NSIS 설치 파일이 없습니다: {installer_path}"
        )

        # Check file size (should be reasonably large)
        file_size = installer_path.stat().st_size / (1024 * 1024)  # MB
        self.assert_true(
            file_size > 10,  # At least 10MB
            f"설치 파일이 너무 작습니다: {file_size:.1f}MB (최소 10MB 필요)"
        )

    @requires_level(CertificationLevel.FULL)
    def test_11_google_sheets_config_consistency(self):
        """번들 config와 크리덴셜 파일의 project_id 일치 확인"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        config_path = self.internal_dir / ".wf_rpa" / "wf_rpa_config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        release_cred_filename = gs_config.get('credentials_file_release')

        if not release_cred_filename:
            return  # credentials_file_release 설정 없음

        # 실제 크리덴셜 파일 찾기
        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        cred_files = list(wf_rpa_dir.glob("worksfree-*.json"))
        if not cred_files:
            self.fail("RELEASE 크리덴셜 파일이 없습니다")

        # config의 filename과 실제 파일명이 일치하는지 확인
        cred_file = cred_files[0]
        self.assert_true(
            cred_file.name == release_cred_filename,
            f"config 파일명 불일치: 설정={release_cred_filename}, 실제={cred_file.name}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_12_credential_environment_separation(self):
        """DEV/RELEASE 크리덴셜 분리 확인 (다른 project_id)"""
        if self.skip_all:
            return  # DEV mode - package tests not applicable

        wf_rpa_dir = self.internal_dir / ".wf_rpa"
        release_files = list(wf_rpa_dir.glob("worksfree-*.json"))
        dev_files = list(wf_rpa_dir.glob("silver-argon-*.json"))

        if not release_files or not dev_files:
            return  # DEV/RELEASE 크리덴셜 파일 중 하나 이상 없음

        with open(release_files[0], 'r') as f:
            release_data = json.load(f)
        
        with open(dev_files[0], 'r') as f:
            dev_data = json.load(f)

        release_project = release_data.get('project_id')
        dev_project = dev_data.get('project_id')

        self.assert_true(
            release_project != dev_project,
            f"DEV/RELEASE가 같은 프로젝트를 사용합니다: {release_project}"
        )
