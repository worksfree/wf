# -*- coding: utf-8 -*-
"""
WF-ACT Deployment Suite
=======================
Certification tests for deployment files and environment configuration.

Tests cover:
- Setup BAT files existence
- DEV/RELEASE environment configuration
- Google Sheets environment settings
- Credentials file configuration
"""

import os
import json
import logging
from pathlib import Path
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class DeploymentSuite(BaseSuite):
    """Deployment files and environment certification tests"""

    name = "Deployment Suite"
    description = "배포 파일 및 환경 설정 인증 테스트 (BAT 파일, DEV/RELEASE 환경)"

    def setup(self):
        """Setup paths for deployment checks"""
        # Common directory path
        # Path: suites/cert_deployment.py → suites → ui_lifecycle_test → 90.tests → 10.rpa
        self.common_dir = Path(__file__).parent.parent.parent.parent / '10.common'
        self.config_dir = self.common_dir / 'config'

    # === BASIC Level Tests - Essential BAT Files ===

    @requires_level(CertificationLevel.BASIC)
    def test_01_setup_worksfree_bat_exists(self):
        """setup_worksfree.bat 파일 존재 확인 (메인 설정 스크립트)"""
        bat_path = self.common_dir / 'setup_worksfree.bat'
        self.assert_true(
            bat_path.exists(),
            f"setup_worksfree.bat 파일이 없습니다: {bat_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_02_shortcut_bat_exists(self):
        """바로가기_생성.bat 파일 존재 확인"""
        bat_path = self.common_dir / '바로가기_생성.bat'
        self.assert_true(
            bat_path.exists(),
            f"바로가기_생성.bat 파일이 없습니다: {bat_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_03_app_reset_bat_exists(self):
        """앱_설정_초기화.bat 파일 존재 확인"""
        bat_path = self.common_dir / '앱_설정_초기화.bat'
        self.assert_true(
            bat_path.exists(),
            f"앱_설정_초기화.bat 파일이 없습니다: {bat_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_04_wf_reset_all_bat_exists(self):
        """wf_전체_초기화.bat 파일 존재 확인"""
        bat_path = self.common_dir / 'wf_전체_초기화.bat'
        self.assert_true(
            bat_path.exists(),
            f"wf_전체_초기화.bat 파일이 없습니다: {bat_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_05_uninstall_bat_exists(self):
        """제거.bat 파일 존재 확인"""
        bat_path = self.common_dir / '제거.bat'
        self.assert_true(
            bat_path.exists(),
            f"제거.bat 파일이 없습니다: {bat_path}"
        )

    @requires_level(CertificationLevel.BASIC)
    def test_06_sync_registration_bat_exists(self):
        """등록정보_동기화.bat 파일 존재 확인"""
        bat_path = self.common_dir / '등록정보_동기화.bat'
        self.assert_true(
            bat_path.exists(),
            f"등록정보_동기화.bat 파일이 없습니다: {bat_path}"
        )

    # === STANDARD Level Tests - wf_rpa_config.json Structure ===

    @requires_level(CertificationLevel.STANDARD)
    def test_07_wf_rpa_config_exists(self):
        """wf_rpa_config.json 파일 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        self.assert_true(
            config_path.exists(),
            f"wf_rpa_config.json 파일이 없습니다: {config_path}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_08_google_sheets_section_exists(self):
        """wf_rpa_config.json에 google_sheets 섹션 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        if not config_path.exists():
            self.assert_true(False, "wf_rpa_config.json 파일이 없습니다")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.assert_true(
            'google_sheets' in config,
            "wf_rpa_config.json에 google_sheets 섹션이 없습니다"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_09_sheet_id_release_exists(self):
        """google_sheets.sheet_id_release 설정 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        sheet_id_release = gs_config.get('sheet_id_release')

        self.assert_not_none(
            sheet_id_release,
            "google_sheets.sheet_id_release 설정이 없습니다"
        )
        self.assert_true(
            len(sheet_id_release) > 10,
            f"sheet_id_release가 유효하지 않습니다: {sheet_id_release}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_10_sheet_id_dev_exists(self):
        """google_sheets.sheet_id_dev 설정 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        sheet_id_dev = gs_config.get('sheet_id_dev')

        self.assert_not_none(
            sheet_id_dev,
            "google_sheets.sheet_id_dev 설정이 없습니다"
        )
        self.assert_true(
            len(sheet_id_dev) > 10,
            f"sheet_id_dev가 유효하지 않습니다: {sheet_id_dev}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_11_credentials_file_release_exists(self):
        """google_sheets.credentials_file_release 설정 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        cred_file = gs_config.get('credentials_file_release')

        self.assert_not_none(
            cred_file,
            "google_sheets.credentials_file_release 설정이 없습니다"
        )
        self.assert_true(
            cred_file.endswith('.json'),
            f"credentials_file_release가 JSON 파일이 아닙니다: {cred_file}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_12_credentials_file_dev_exists(self):
        """google_sheets.credentials_file_dev 설정 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        cred_file = gs_config.get('credentials_file_dev')

        self.assert_not_none(
            cred_file,
            "google_sheets.credentials_file_dev 설정이 없습니다"
        )
        self.assert_true(
            cred_file.endswith('.json'),
            f"credentials_file_dev가 JSON 파일이 아닙니다: {cred_file}"
        )

    # === FULL Level Tests - Actual File Validation ===

    @requires_level(CertificationLevel.FULL)
    def test_13_release_credentials_file_exists(self):
        """RELEASE 크리덴셜 파일 실제 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        cred_file = gs_config.get('credentials_file_release')

        if cred_file:
            cred_path = self.config_dir / cred_file
            self.assert_true(
                cred_path.exists(),
                f"RELEASE 크리덴셜 파일이 없습니다: {cred_path}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_14_dev_credentials_file_exists(self):
        """DEV 크리덴셜 파일 실제 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        cred_file = gs_config.get('credentials_file_dev')

        if cred_file:
            cred_path = self.config_dir / cred_file
            self.assert_true(
                cred_path.exists(),
                f"DEV 크리덴셜 파일이 없습니다: {cred_path}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_15_sheet_ids_are_different(self):
        """DEV와 RELEASE 시트 ID가 다른지 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        sheet_id_release = gs_config.get('sheet_id_release')
        sheet_id_dev = gs_config.get('sheet_id_dev')

        if sheet_id_release and sheet_id_dev:
            self.assert_true(
                sheet_id_release != sheet_id_dev,
                f"DEV와 RELEASE 시트 ID가 동일합니다 (분리 필요): {sheet_id_release}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_16_credentials_files_are_different(self):
        """DEV와 RELEASE 크리덴셜 파일이 다른지 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs_config = config.get('google_sheets', {})
        cred_release = gs_config.get('credentials_file_release')
        cred_dev = gs_config.get('credentials_file_dev')

        if cred_release and cred_dev:
            self.assert_true(
                cred_release != cred_dev,
                f"DEV와 RELEASE 크리덴셜 파일이 동일합니다 (분리 권장): {cred_release}"
            )

    @requires_level(CertificationLevel.FULL)
    def test_17_setup_bat_has_korean_encoding(self):
        """setup_worksfree.bat에 한글 인코딩 설정(chcp 65001) 존재 확인"""
        bat_path = self.common_dir / 'setup_worksfree.bat'
        if not bat_path.exists():
            self.assert_true(False, "setup_worksfree.bat 파일이 없습니다")

        content = bat_path.read_text(encoding='utf-8', errors='replace')
        self.assert_true(
            'chcp 65001' in content or 'chcp  65001' in content,
            "setup_worksfree.bat에 한글 인코딩 설정(chcp 65001)이 없습니다"
        )

    @requires_level(CertificationLevel.FULL)
    def test_18_no_duplicate_shortcut_bat(self):
        """중복 바로가기 스크립트(create_desktop_shortcut.bat) 제거 확인"""
        duplicate_path = self.common_dir / 'create_desktop_shortcut.bat'
        self.assert_false(
            duplicate_path.exists(),
            f"중복 파일이 존재합니다 (제거 필요): {duplicate_path}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_19_email_settings_exist(self):
        """wf_rpa_config.json에 email_settings 섹션 존재 확인"""
        config_path = self.config_dir / 'wf_rpa_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.assert_true(
            'email_settings' in config,
            "wf_rpa_config.json에 email_settings 섹션이 없습니다"
        )

        email_settings = config.get('email_settings', {})
        self.assert_true(
            'smtp_server' in email_settings,
            "email_settings에 smtp_server가 없습니다"
        )

    @requires_level(CertificationLevel.FULL)
    def test_20_app_policy_files_exist(self):
        """현재 앱의 policy.json 파일 존재 확인"""
        app_name = self.app_config.name
        policy_path = self.config_dir / app_name / 'policy.json'

        self.assert_true(
            policy_path.exists(),
            f"앱 정책 파일이 없습니다: {policy_path}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_21_app_settings_files_exist(self):
        """현재 앱의 settings.json 파일 존재 확인"""
        app_name = self.app_config.name
        settings_path = self.config_dir / app_name / 'settings.json'

        self.assert_true(
            settings_path.exists(),
            f"앱 설정 파일이 없습니다: {settings_path}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_22_user_manual_pdf_exists(self):
        """앱의 사용자 매뉴얼 PDF 파일 존재 확인"""
        app_name = self.app_config.name

        # App directories mapping
        app_dirs = {
            'bom_exporter': Path(__file__).parent.parent.parent.parent / '30.apps' / 'bom_exporter',
            'dwg_classifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'dwg_classifier',
            'batch_print': Path(__file__).parent.parent.parent.parent / '30.apps' / 'batch_print',
            'conversion_verifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'conversion_verifier',
            'korean_filename_normalizer': Path(__file__).parent.parent.parent.parent / '50.data' / 'korean_filename_normalizer',
            'attribute_reset': Path(__file__).parent.parent.parent.parent / '30.apps' / 'attribute_reset',
            'qrcode_generator': Path(__file__).parent.parent.parent.parent / '50.data' / 'qrcode_generator',
        }

        app_dir = app_dirs.get(app_name)
        if not app_dir:
            self.assert_true(False, f"알 수 없는 앱: {app_name}")
            return

        # Find *_USER_MANUAL.pdf or *_manual*.pdf
        manual_files = list(app_dir.glob('*USER_MANUAL*.pdf')) + list(app_dir.glob('*_manual*.pdf'))

        self.assert_true(
            len(manual_files) > 0,
            f"사용자 매뉴얼 PDF가 없습니다: {app_dir}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_23_app_icon_exists(self):
        """앱의 아이콘 파일 존재 확인"""
        app_name = self.app_config.name

        # App directories mapping
        app_dirs = {
            'bom_exporter': Path(__file__).parent.parent.parent.parent / '30.apps' / 'bom_exporter',
            'dwg_classifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'dwg_classifier',
            'batch_print': Path(__file__).parent.parent.parent.parent / '30.apps' / 'batch_print',
            'conversion_verifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'conversion_verifier',
            'korean_filename_normalizer': Path(__file__).parent.parent.parent.parent / '50.data' / 'korean_filename_normalizer',
            'attribute_reset': Path(__file__).parent.parent.parent.parent / '30.apps' / 'attribute_reset',
            'qrcode_generator': Path(__file__).parent.parent.parent.parent / '50.data' / 'qrcode_generator',
        }

        app_dir = app_dirs.get(app_name)
        if not app_dir:
            self.assert_true(False, f"알 수 없는 앱: {app_name}")
            return

        # Check for .ico files in res folder or app root
        icon_files = list(app_dir.glob('res/*.ico')) + list(app_dir.glob('*.ico'))

        self.assert_true(
            len(icon_files) > 0,
            f"앱 아이콘 파일(.ico)이 없습니다: {app_dir}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_24_spec_file_exists(self):
        """앱의 PyInstaller spec 파일 존재 확인"""
        app_name = self.app_config.name

        # App directories mapping
        app_dirs = {
            'bom_exporter': Path(__file__).parent.parent.parent.parent / '30.apps' / 'bom_exporter',
            'dwg_classifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'dwg_classifier',
            'batch_print': Path(__file__).parent.parent.parent.parent / '30.apps' / 'batch_print',
            'conversion_verifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'conversion_verifier',
            'korean_filename_normalizer': Path(__file__).parent.parent.parent.parent / '50.data' / 'korean_filename_normalizer',
            'attribute_reset': Path(__file__).parent.parent.parent.parent / '30.apps' / 'attribute_reset',
            'qrcode_generator': Path(__file__).parent.parent.parent.parent / '50.data' / 'qrcode_generator',
        }

        app_dir = app_dirs.get(app_name)
        if not app_dir:
            self.assert_true(False, f"알 수 없는 앱: {app_name}")
            return

        # Check for .spec files
        spec_files = list(app_dir.glob('*.spec'))

        self.assert_true(
            len(spec_files) > 0,
            f"PyInstaller spec 파일이 없습니다: {app_dir}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_25_build_script_exists(self):
        """앱의 빌드 스크립트(build_*.ps1) 존재 확인"""
        app_name = self.app_config.name

        # App directories mapping
        app_dirs = {
            'bom_exporter': Path(__file__).parent.parent.parent.parent / '30.apps' / 'bom_exporter',
            'dwg_classifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'dwg_classifier',
            'batch_print': Path(__file__).parent.parent.parent.parent / '30.apps' / 'batch_print',
            'conversion_verifier': Path(__file__).parent.parent.parent.parent / '50.data' / 'conversion_verifier',
            'korean_filename_normalizer': Path(__file__).parent.parent.parent.parent / '50.data' / 'korean_filename_normalizer',
            'attribute_reset': Path(__file__).parent.parent.parent.parent / '30.apps' / 'attribute_reset',
            'qrcode_generator': Path(__file__).parent.parent.parent.parent / '50.data' / 'qrcode_generator',
        }

        app_dir = app_dirs.get(app_name)
        if not app_dir:
            self.assert_true(False, f"알 수 없는 앱: {app_name}")
            return

        # Check for build_*.ps1 files
        build_scripts = list(app_dir.glob('build_*.ps1'))

        self.assert_true(
            len(build_scripts) > 0,
            f"빌드 스크립트(build_*.ps1)가 없습니다: {app_dir}"
        )
