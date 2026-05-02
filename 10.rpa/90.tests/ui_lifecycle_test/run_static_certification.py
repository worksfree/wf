# -*- coding: utf-8 -*-
"""
WF-ACT Static Certification
============================
정적 파일 및 설정 검증 (앱 실행 불필요)

Usage:
    python run_static_certification.py           # 모든 앱 검증
    python run_static_certification.py --app be  # 특정 앱만 검증
"""

import sys
import io
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
COMMON_DIR = PROJECT_ROOT / '10.common'
CONFIG_DIR = COMMON_DIR / 'config'
OUTPUT_DIR = Path(__file__).parent / 'test_results'

# All 7 apps
ALL_APPS = [
    'bom_exporter',
    'dwg_classifier',
    'dwg_batch_print',
    'conversion_verifier',
    'korean_filename_normalizer',
    'attribute_reset',
    'qrcode_generator',
]

# Paid apps (trial_500works 적용 대상)
PAID_APPS = {
    'attribute_reset',
    'dwg_classifier',
    'dwg_batch_print',
    'bom_exporter',
}

# App shortcuts
SHORTCUTS = {
    'be': 'bom_exporter',
    'dc': 'dwg_classifier',
    'dbp': 'dwg_batch_print',
    'cv': 'conversion_verifier',
    'kfn': 'korean_filename_normalizer',
    'ar': 'attribute_reset',
    'qr': 'qrcode_generator',
}


@dataclass
class TestResult:
    name: str
    description: str
    passed: bool
    message: str = ""
    level: str = "BASIC"


@dataclass
class AppCertResult:
    app_name: str
    tests: List[TestResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tests if not t.passed)


class StaticCertification:
    """Static file and configuration certification"""

    def __init__(self, app_name: str, test_connectivity: bool = False):
        self.app_name = app_name
        self.test_connectivity = test_connectivity
        self.results: List[TestResult] = []

    def add_result(self, name: str, desc: str, passed: bool, msg: str = "", level: str = "BASIC"):
        self.results.append(TestResult(name, desc, passed, msg, level))

    def run_all_tests(self) -> AppCertResult:
        """Run all static tests"""
        # Common BAT files (BASIC)
        self._test_bat_files()

        # Config structure (STANDARD)
        self._test_config_structure()

        # DEV/RELEASE environment (STANDARD)
        self._test_dev_release_config()

        # App-specific files (FULL)
        self._test_app_files()

        # Credentials validation (FULL)
        self._test_credentials()

        # Google Sheets connectivity (CONNECTIVITY - optional)
        if self.test_connectivity:
            self._test_google_sheets_connectivity()

        return AppCertResult(app_name=self.app_name, tests=self.results)

    def _test_bat_files(self):
        """Test BAT file existence"""
        bat_files = [
            ('setup_worksfree.bat', '메인 설정 스크립트'),
            ('바로가기_생성.bat', '바로가기 생성'),
            ('앱_설정_초기화.bat', '앱 설정 초기화'),
            ('wf_전체_초기화.bat', 'WF 전체 초기화'),
            ('제거.bat', '앱 제거'),
            ('등록정보_동기화.bat', '등록정보 동기화'),
        ]

        for filename, desc in bat_files:
            path = COMMON_DIR / filename
            passed = path.exists()
            msg = "존재함" if passed else f"파일 없음: {path}"
            self.add_result(f"bat_{filename}", f"{desc} ({filename})", passed, msg, "BASIC")

        # Check duplicate removal
        dup_path = COMMON_DIR / 'create_desktop_shortcut.bat'
        passed = not dup_path.exists()
        msg = "제거됨" if passed else "중복 파일 존재 (제거 필요)"
        self.add_result("bat_no_duplicate", "중복 바로가기 스크립트 제거", passed, msg, "FULL")

    def _test_config_structure(self):
        """Test wf_rpa_config.json structure"""
        config_path = CONFIG_DIR / 'wf_rpa_config.json'

        # File existence
        if not config_path.exists():
            self.add_result("config_exists", "wf_rpa_config.json 존재", False,
                          f"파일 없음: {config_path}", "STANDARD")
            return

        self.add_result("config_exists", "wf_rpa_config.json 존재", True, "존재함", "STANDARD")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self.add_result("config_parse", "설정 파일 파싱", False, str(e), "STANDARD")
            return

        self.add_result("config_parse", "설정 파일 파싱", True, "JSON 파싱 성공", "STANDARD")

        # google_sheets section
        gs = config.get('google_sheets', {})
        passed = bool(gs)
        self.add_result("config_google_sheets", "google_sheets 섹션", passed,
                       "존재함" if passed else "섹션 없음", "STANDARD")

        # email_settings section
        email = config.get('email_settings', {})
        passed = bool(email)
        self.add_result("config_email_settings", "email_settings 섹션", passed,
                       "존재함" if passed else "섹션 없음", "STANDARD")

    def _test_dev_release_config(self):
        """Test DEV/RELEASE environment configuration"""
        config_path = CONFIG_DIR / 'wf_rpa_config.json'
        if not config_path.exists():
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs = config.get('google_sheets', {})

        # sheet_id_release
        val = gs.get('sheet_id_release')
        passed = bool(val) and len(str(val)) > 10
        self.add_result("env_sheet_id_release", "sheet_id_release 설정", passed,
                       f"설정됨: {val[:20]}..." if passed else "미설정", "STANDARD")

        # sheet_id_dev
        val = gs.get('sheet_id_dev')
        passed = bool(val) and len(str(val)) > 10
        self.add_result("env_sheet_id_dev", "sheet_id_dev 설정", passed,
                       f"설정됨: {val[:20]}..." if passed else "미설정", "STANDARD")

        # credentials_file_release
        val = gs.get('credentials_file_release')
        passed = bool(val) and str(val).endswith('.json')
        self.add_result("env_cred_release", "credentials_file_release 설정", passed,
                       f"설정됨: {val}" if passed else "미설정", "STANDARD")

        # credentials_file_dev
        val = gs.get('credentials_file_dev')
        passed = bool(val) and str(val).endswith('.json')
        self.add_result("env_cred_dev", "credentials_file_dev 설정", passed,
                       f"설정됨: {val}" if passed else "미설정", "STANDARD")

        # Check DEV != RELEASE
        release_id = gs.get('sheet_id_release')
        dev_id = gs.get('sheet_id_dev')
        if release_id and dev_id:
            passed = release_id != dev_id
            self.add_result("env_sheet_ids_different", "DEV/RELEASE 시트 ID 분리", passed,
                           "분리됨" if passed else "동일함 (분리 필요)", "FULL")

        release_cred = gs.get('credentials_file_release')
        dev_cred = gs.get('credentials_file_dev')
        if release_cred and dev_cred:
            passed = release_cred != dev_cred
            self.add_result("env_creds_different", "DEV/RELEASE 크리덴셜 분리", passed,
                           "분리됨" if passed else "동일함 (분리 권장)", "FULL")

    def _test_credentials(self):
        """Test credentials file existence"""
        config_path = CONFIG_DIR / 'wf_rpa_config.json'
        if not config_path.exists():
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        gs = config.get('google_sheets', {})

        # Release credentials
        cred_file = gs.get('credentials_file_release')
        if cred_file:
            cred_path = CONFIG_DIR / cred_file
            passed = cred_path.exists()
            self.add_result("cred_release_exists", "RELEASE 크리덴셜 파일", passed,
                           f"존재함: {cred_file}" if passed else f"파일 없음: {cred_path}", "FULL")

        # Dev credentials
        cred_file = gs.get('credentials_file_dev')
        if cred_file:
            cred_path = CONFIG_DIR / cred_file
            passed = cred_path.exists()
            self.add_result("cred_dev_exists", "DEV 크리덴셜 파일", passed,
                           f"존재함: {cred_file}" if passed else f"파일 없음: {cred_path}", "FULL")

    def _test_google_sheets_connectivity(self):
        """Test actual Google Sheets API connectivity"""
        config_path = CONFIG_DIR / 'wf_rpa_config.json'
        if not config_path.exists():
            self.add_result("gs_conn_config", "연결 테스트용 설정", False,
                           "wf_rpa_config.json 없음", "CONNECTIVITY")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self.add_result("gs_conn_config", "연결 테스트용 설정", False, str(e), "CONNECTIVITY")
            return

        gs = config.get('google_sheets', {})

        # Import gspread
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            self.add_result("gs_conn_import", "gspread 모듈 임포트", True,
                           "gspread, google.oauth2 로드 성공", "CONNECTIVITY")
        except ImportError as e:
            self.add_result("gs_conn_import", "gspread 모듈 임포트", False,
                           f"모듈 없음: {e}", "CONNECTIVITY")
            return

        # Test DEV connection
        self._test_sheets_connection(gs, 'dev', gspread, Credentials)

        # Test RELEASE connection
        self._test_sheets_connection(gs, 'release', gspread, Credentials)

    def _test_sheets_connection(self, gs_config: dict, env: str, gspread, Credentials):
        """Helper: Test connection for specific environment (dev/release)"""
        sheet_id = gs_config.get(f'sheet_id_{env}')
        cred_file = gs_config.get(f'credentials_file_{env}')

        if not sheet_id or not cred_file:
            self.add_result(f"gs_conn_{env}_config", f"{env.upper()} 연결 설정", False,
                           f"sheet_id 또는 credentials 미설정", "CONNECTIVITY")
            return

        cred_path = CONFIG_DIR / cred_file
        if not cred_path.exists():
            self.add_result(f"gs_conn_{env}_cred", f"{env.upper()} 크리덴셜", False,
                           f"파일 없음: {cred_path}", "CONNECTIVITY")
            return

        # Attempt connection
        try:
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            credentials = Credentials.from_service_account_file(str(cred_path), scopes=SCOPES)
            gc = gspread.authorize(credentials)

            self.add_result(f"gs_conn_{env}_auth", f"{env.upper()} 인증", True,
                           "서비스 계정 인증 성공", "CONNECTIVITY")

            # Try to open spreadsheet
            spreadsheet = gc.open_by_key(sheet_id)
            sheet_title = spreadsheet.title

            self.add_result(f"gs_conn_{env}_open", f"{env.upper()} 시트 접근", True,
                           f"시트 열기 성공: {sheet_title}", "CONNECTIVITY")

            # Try to read worksheet list
            worksheets = spreadsheet.worksheets()
            ws_names = [ws.title for ws in worksheets[:5]]  # 최대 5개만

            self.add_result(f"gs_conn_{env}_read", f"{env.upper()} 워크시트 읽기", True,
                           f"워크시트 {len(worksheets)}개: {', '.join(ws_names)}", "CONNECTIVITY")

        except gspread.exceptions.SpreadsheetNotFound:
            self.add_result(f"gs_conn_{env}_open", f"{env.upper()} 시트 접근", False,
                           f"시트를 찾을 수 없음: {sheet_id[:20]}...", "CONNECTIVITY")
        except gspread.exceptions.APIError as e:
            self.add_result(f"gs_conn_{env}_api", f"{env.upper()} API 호출", False,
                           f"API 오류: {e}", "CONNECTIVITY")
        except Exception as e:
            self.add_result(f"gs_conn_{env}_error", f"{env.upper()} 연결", False,
                           f"연결 실패: {type(e).__name__}: {e}", "CONNECTIVITY")

    def _test_app_files(self):
        """Test app-specific files"""
        app_config_dir = CONFIG_DIR / self.app_name

        # policy.json
        policy_path = app_config_dir / 'policy.json'
        passed = policy_path.exists()
        self.add_result("app_policy", f"{self.app_name}/policy.json", passed,
                       "존재함" if passed else f"파일 없음: {policy_path}", "FULL")

        if passed:
            try:
                with open(policy_path, 'r', encoding='utf-8') as f:
                    policy = json.load(f)

                identity = policy.get('identity', {})
                app_name = identity.get('app_name')
                passed = app_name == self.app_name
                self.add_result("app_policy_name", "policy.json app_name 일치", passed,
                               f"일치: {app_name}" if passed else f"불일치: {app_name} != {self.app_name}", "FULL")

                # Trial credits policy validation (deployment defaults)
                policy_body = policy.get('policy', {})
                pricing_model = policy_body.get('pricing_model')
                trial_credits = policy_body.get('trial_credits')
                credit_per_work = policy_body.get('credit_per_work')

                if self.app_name in PAID_APPS:
                    expected_trial = (credit_per_work or 0) * 500
                    is_pricing_ok = pricing_model == 'trial_500works'
                    is_credit_ok = (
                        isinstance(trial_credits, int)
                        and isinstance(credit_per_work, int)
                        and credit_per_work > 0
                        and trial_credits == expected_trial
                    )
                    self.add_result(
                        "policy_paid_pricing_model",
                        "유료 앱 pricing_model=trial_500works",
                        is_pricing_ok,
                        f"{pricing_model}" if is_pricing_ok else f"invalid: {pricing_model}",
                        "FULL",
                    )
                    self.add_result(
                        "policy_paid_trial_credits",
                        "유료 앱 trial_credits=credit_per_work×500",
                        is_credit_ok,
                        f"trial_credits={trial_credits}, credit_per_work={credit_per_work}",
                        "FULL",
                    )
                else:
                    # Free apps should not use trial_500works and must be unlimited
                    is_free_model_ok = pricing_model != 'trial_500works'
                    is_free_credit_ok = (trial_credits == -1 and credit_per_work == 0)
                    self.add_result(
                        "policy_free_not_trial_500works",
                        "무료 앱은 trial_500works 사용 금지",
                        is_free_model_ok,
                        f"{pricing_model}" if is_free_model_ok else f"invalid: {pricing_model}",
                        "FULL",
                    )
                    self.add_result(
                        "policy_free_unlimited",
                        "무료 앱 trial_credits=-1 & credit_per_work=0",
                        is_free_credit_ok,
                        f"trial_credits={trial_credits}, credit_per_work={credit_per_work}",
                        "FULL",
                    )
            except Exception as e:
                self.add_result("app_policy_parse", "policy.json 파싱", False, str(e), "FULL")

        # settings.json
        settings_path = app_config_dir / 'settings.json'
        passed = settings_path.exists()
        self.add_result("app_settings", f"{self.app_name}/settings.json", passed,
                       "존재함" if passed else f"파일 없음: {settings_path}", "FULL")


def generate_html_report(results: List[AppCertResult], output_path: Path):
    """Generate HTML certification report"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>WF-ACT Static Certification Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
        .summary-card {{ background: #f8f9fa; padding: 15px 20px; border-radius: 8px; min-width: 150px; }}
        .summary-card.pass {{ border-left: 4px solid #4CAF50; }}
        .summary-card.fail {{ border-left: 4px solid #f44336; }}
        .summary-card h3 {{ margin: 0 0 5px 0; font-size: 14px; color: #666; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; }}
        .app-section {{ margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 8px; }}
        .app-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .app-name {{ font-size: 18px; font-weight: bold; color: #333; }}
        .app-stats {{ color: #666; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .pass {{ color: #4CAF50; }}
        .fail {{ color: #f44336; }}
        .level {{ font-size: 12px; color: #999; padding: 2px 6px; background: #eee; border-radius: 4px; }}
        .timestamp {{ color: #999; font-size: 12px; }}
        .icon {{ font-size: 18px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>WF-ACT Static Certification Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
'''

    # Overall summary
    total_tests = sum(r.total for r in results)
    total_passed = sum(r.passed_count for r in results)
    total_failed = sum(r.failed_count for r in results)

    html += f'''
        <div class="summary">
            <div class="summary-card">
                <h3>Total Apps</h3>
                <div class="value">{len(results)}</div>
            </div>
            <div class="summary-card pass">
                <h3>Tests Passed</h3>
                <div class="value pass">{total_passed}</div>
            </div>
            <div class="summary-card fail">
                <h3>Tests Failed</h3>
                <div class="value fail">{total_failed}</div>
            </div>
            <div class="summary-card">
                <h3>Pass Rate</h3>
                <div class="value">{total_passed/total_tests*100:.1f}%</div>
            </div>
        </div>
'''

    # Per-app results
    for result in results:
        icon = "✅" if result.failed_count == 0 else "⚠️"
        html += f'''
        <div class="app-section">
            <div class="app-header">
                <span class="app-name"><span class="icon">{icon}</span> {result.app_name}</span>
                <span class="app-stats">{result.passed_count}/{result.total} passed</span>
            </div>
            <table>
                <tr><th>Test</th><th>Description</th><th>Level</th><th>Result</th><th>Message</th></tr>
'''
        for test in result.tests:
            status_class = "pass" if test.passed else "fail"
            status_icon = "✓" if test.passed else "✗"
            html += f'''
                <tr>
                    <td>{test.name}</td>
                    <td>{test.description}</td>
                    <td><span class="level">{test.level}</span></td>
                    <td class="{status_class}"><span class="icon">{status_icon}</span></td>
                    <td>{test.message}</td>
                </tr>
'''
        html += '''
            </table>
        </div>
'''

    html += '''
    </div>
</body>
</html>
'''

    output_path.write_text(html, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='WF-ACT Static Certification')
    parser.add_argument('--app', '-a', nargs='+', help='Apps to certify (default: all)')
    parser.add_argument('--connectivity', '-c', action='store_true',
                       help='Include Google Sheets connectivity test (requires network)')
    args = parser.parse_args()

    # Resolve app names
    apps = []
    if args.app:
        for name in args.app:
            name = name.lower()
            if name in SHORTCUTS:
                apps.append(SHORTCUTS[name])
            elif name in ALL_APPS:
                apps.append(name)
            else:
                print(f"Unknown app: {name}")
    else:
        apps = ALL_APPS

    print("=" * 70)
    print("  WF-ACT Static Certification")
    print("=" * 70)
    print(f"  Apps: {', '.join(apps)}")
    print(f"  Config Dir: {CONFIG_DIR}")
    print(f"  Connectivity Test: {'Enabled' if args.connectivity else 'Disabled'}")
    print("=" * 70)
    print()

    # Run certification for each app
    results = []
    for app_name in apps:
        print(f"\n{'#' * 50}")
        print(f"  Certifying: {app_name}")
        print(f"{'#' * 50}\n")

        cert = StaticCertification(app_name, test_connectivity=args.connectivity)
        result = cert.run_all_tests()
        results.append(result)

        # Print results
        for test in result.tests:
            icon = "✓" if test.passed else "✗"
            status = "PASS" if test.passed else "FAIL"
            print(f"  {icon} [{test.level:8}] {test.name}: {test.message}")

        print(f"\n  Summary: {result.passed_count}/{result.total} passed")

    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = OUTPUT_DIR / f'static_certification_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)

    # HTML report
    html_path = output_dir / 'static_certification_report.html'
    generate_html_report(results, html_path)

    # JSON results
    json_path = output_dir / 'static_certification_result.json'
    json_data = {
        'timestamp': timestamp,
        'apps': [
            {
                'app_name': r.app_name,
                'total': r.total,
                'passed': r.passed_count,
                'failed': r.failed_count,
                'tests': [
                    {
                        'name': t.name,
                        'description': t.description,
                        'level': t.level,
                        'passed': t.passed,
                        'message': t.message,
                    }
                    for t in r.tests
                ]
            }
            for r in results
        ]
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')

    # Final summary
    total_tests = sum(r.total for r in results)
    total_passed = sum(r.passed_count for r in results)
    total_failed = sum(r.failed_count for r in results)

    print("\n" + "=" * 70)
    print("  CERTIFICATION SUMMARY")
    print("=" * 70)

    for result in results:
        icon = "✅" if result.failed_count == 0 else "⚠️"
        print(f"\n  {icon} {result.app_name}: {result.passed_count}/{result.total}")
        if result.failed_count > 0:
            for test in result.tests:
                if not test.passed:
                    print(f"      ✗ {test.name}: {test.message}")

    print("\n" + "-" * 70)
    print(f"  Total: {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
    print(f"  Report: {html_path}")
    print("=" * 70 + "\n")

    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
