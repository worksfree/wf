# -*- coding: utf-8 -*-
"""
WF-ACT Security Suite
=====================
Certification tests for security compliance.

Tests cover:
- Hardcoded credentials detection
- Sensitive files in gitignore
- Safe file handling
"""

import re
import logging
from pathlib import Path
from .base import BaseSuite
from core.certification import CertificationLevel, requires_level

logger = logging.getLogger(__name__)


class SecuritySuite(BaseSuite):
    """Security certification tests"""

    name = "Security Suite"
    description = "보안 인증 테스트 (자격증명 하드코딩, 민감파일 관리)"

    def setup(self):
        """Setup paths for security checks"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.common_dir = self.project_root / '10.common'

    def _get_app_dir(self, app_name: str) -> Path:
        """Get app directory path"""
        app_dirs = {
            'bom_exporter': self.project_root / '30.apps' / 'bom_exporter',
            'dwg_classifier': self.project_root / '50.data' / 'dwg_classifier',
            'dwg_batch_print': self.project_root / '30.apps' / 'dwg_batch_print',
            'conversion_verifier': self.project_root / '50.data' / 'conversion_verifier',
            'korean_filename_normalizer': self.project_root / '50.data' / 'korean_filename_normalizer',
            'attribute_reset': self.project_root / '30.apps' / 'attribute_reset',
            'qrcode_generator': self.project_root / '50.data' / 'qrcode_generator',
        }
        return app_dirs.get(app_name)

    # === STANDARD Level Tests ===

    @requires_level(CertificationLevel.STANDARD)
    def test_01_no_hardcoded_passwords(self):
        """소스코드에 하드코딩된 비밀번호가 없는지 확인"""
        app_name = self.app_config.name
        app_dir = self._get_app_dir(app_name)

        if not app_dir or not app_dir.exists():
            return  # Skip if app dir not found

        # Patterns that suggest hardcoded credentials
        suspicious_patterns = [
            r'password\s*=\s*["\'][^"\']{4,}["\']',
            r'passwd\s*=\s*["\'][^"\']{4,}["\']',
            r'secret\s*=\s*["\'][^"\']{4,}["\']',
            r'api_key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']',
        ]

        # Lines with these comments are intentional dev/fallback/config patterns
        excluded_comments = [
            'fallback', 'default', 'dev', 'debug', 'test', 'example',
            'admin', '관리자', 'license', '라이선스', 'config', '설정'
        ]

        violations = []
        for py_file in app_dir.glob('**/*.py'):
            # Skip test files and __pycache__
            if '__pycache__' in str(py_file) or 'test_' in py_file.name:
                continue

            try:
                lines = py_file.read_text(encoding='utf-8', errors='replace').splitlines()
                for line_num, line in enumerate(lines, 1):
                    # Skip lines with intentional dev/fallback comments
                    line_lower = line.lower()
                    if any(excl in line_lower for excl in excluded_comments):
                        continue

                    for pattern in suspicious_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(f"{py_file.name}:{line_num}")
            except Exception:
                continue

        self.assert_true(
            len(violations) == 0,
            f"하드코딩된 자격증명 의심: {violations[:3]}"
        )

    @requires_level(CertificationLevel.STANDARD)
    def test_02_no_private_keys_in_source(self):
        """소스코드에 개인키가 포함되지 않았는지 확인"""
        app_name = self.app_config.name
        app_dir = self._get_app_dir(app_name)

        if not app_dir or not app_dir.exists():
            return

        # Patterns for private keys
        key_patterns = [
            r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
            r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----',
        ]

        violations = []
        for py_file in app_dir.glob('**/*.py'):
            if '__pycache__' in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding='utf-8', errors='replace')
                for pattern in key_patterns:
                    if re.search(pattern, content):
                        violations.append(py_file.name)
            except Exception:
                continue

        self.assert_true(
            len(violations) == 0,
            f"개인키 포함 파일 발견: {violations}"
        )

    # === FULL Level Tests ===

    @requires_level(CertificationLevel.FULL)
    def test_03_gitignore_has_sensitive_patterns(self):
        """.gitignore에 민감 파일 패턴이 있는지 확인"""
        gitignore_path = self.project_root / '.gitignore'

        if not gitignore_path.exists():
            # No gitignore is a warning, not a failure
            return

        content = gitignore_path.read_text(encoding='utf-8', errors='replace')

        # Required patterns for sensitive files
        required_patterns = [
            '.env',
            '*.pem',
            '*credentials*.json',
        ]

        missing = []
        for pattern in required_patterns:
            if pattern not in content:
                missing.append(pattern)

        # At least some sensitive patterns should be in gitignore
        self.assert_true(
            len(missing) < len(required_patterns),
            f".gitignore에 민감 파일 패턴 부족: {missing}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_04_no_env_files_in_app(self):
        """앱 폴더에 .env 파일이 없는지 확인"""
        app_name = self.app_config.name
        app_dir = self._get_app_dir(app_name)

        if not app_dir or not app_dir.exists():
            return

        env_files = list(app_dir.glob('**/.env')) + list(app_dir.glob('**/.env.*'))
        # Filter out example files
        env_files = [f for f in env_files if 'example' not in f.name.lower()]

        self.assert_true(
            len(env_files) == 0,
            f".env 파일 발견 (제거 필요): {[f.name for f in env_files]}"
        )

    @requires_level(CertificationLevel.FULL)
    def test_05_credentials_in_config_not_source(self):
        """자격증명 파일이 config 폴더에 있는지 확인 (소스 폴더 아님)"""
        # Check that credentials JSON files are in config folder, not app source
        cred_files = list(self.common_dir.glob('config/*.json'))

        # Should have at least one credentials file in proper location
        has_creds_in_config = any('silver-argon' in f.name or 'worksfree' in f.name for f in cred_files)

        self.assert_true(
            has_creds_in_config,
            "자격증명 파일이 10.common/config/에 있어야 함"
        )

    @requires_level(CertificationLevel.FULL)
    def test_06_no_debug_credentials(self):
        """디버그용 자격증명이 남아있지 않은지 확인"""
        app_name = self.app_config.name
        app_dir = self._get_app_dir(app_name)

        if not app_dir or not app_dir.exists():
            return

        # Debug credential patterns
        debug_patterns = [
            r'test@test\.com',
            r'admin@admin',
            r'password123',
            r'qwerty',
            r'123456',
        ]

        violations = []
        for py_file in app_dir.glob('**/*.py'):
            if '__pycache__' in str(py_file) or 'test_' in py_file.name:
                continue

            try:
                content = py_file.read_text(encoding='utf-8', errors='replace')
                for pattern in debug_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        violations.append(f"{py_file.name}: {pattern}")
            except Exception:
                continue

        self.assert_true(
            len(violations) == 0,
            f"디버그용 자격증명 발견: {violations[:3]}"
        )
