# -*- coding: utf-8 -*-
"""
WF-ACT Report Generator
=======================
Generates certification reports in HTML and JSON formats.

Usage:
    generator = ReportGenerator(result)
    generator.generate_html('report.html')
    generator.generate_json('report.json')

    # 통합 리포트 생성
    generate_index_html(results, output_dir)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .certification import CertificationResult, CertificationLevel, TestResult


def generate_index_html(results: List[CertificationResult], output_dir: Path) -> Path:
    """
    Generate unified index.html that shows all apps certification results.

    Args:
        results: List of certification results from all apps
        output_dir: Output directory for the index.html

    Returns:
        Path to the generated index.html
    """
    output_dir = Path(output_dir)
    output_path = output_dir / 'index.html'

    # Calculate totals
    total_apps = len(results)
    total_tests = sum(r.total_tests for r in results)
    total_passed = sum(r.passed_tests for r in results)
    total_failed = sum(r.failed_tests for r in results)
    total_duration = sum(r.duration for r in results)

    # Build app cards HTML
    app_cards_html = ""
    for r in results:
        level_styles = {
            CertificationLevel.FULL: ('gold', '#FFD700', '🥇'),
            CertificationLevel.STANDARD: ('silver', '#C0C0C0', '🥈'),
            CertificationLevel.BASIC: ('bronze', '#CD7F32', '🥉'),
            CertificationLevel.NONE: ('failed', '#DC3545', '❌'),
        }
        badge_class, badge_color, badge_icon = level_styles.get(r.level, level_styles[CertificationLevel.NONE])

        pass_rate = (r.passed_tests / r.total_tests * 100) if r.total_tests > 0 else 0

        # Build failed tests list
        failed_tests_html = ""
        failed_tests = r.get_failed_tests()
        if failed_tests:
            for test in failed_tests[:5]:
                failed_tests_html += f'<li><code>{test.name}</code>: {test.message[:50]}...</li>'
            if len(failed_tests) > 5:
                failed_tests_html += f'<li>... +{len(failed_tests) - 5} more</li>'

        app_cards_html += f"""
        <div class="app-card {'passed' if r.passed else 'failed'}">
            <div class="app-header">
                <div class="app-info">
                    <h3>{r.app_name}</h3>
                    <span class="app-version">{r.app_version}</span>
                </div>
                <div class="app-badge" style="background: linear-gradient(135deg, {badge_color}22, {badge_color}44); border-color: {badge_color};">
                    <span class="badge-icon">{badge_icon}</span>
                    <span class="badge-level" style="color: {badge_color};">{r.level.name}</span>
                </div>
            </div>
            <div class="app-stats">
                <div class="stat">
                    <span class="stat-value">{r.passed_tests}/{r.total_tests}</span>
                    <span class="stat-label">Tests</span>
                </div>
                <div class="stat">
                    <span class="stat-value {'success' if pass_rate >= 90 else 'warning' if pass_rate >= 70 else 'danger'}">{pass_rate:.0f}%</span>
                    <span class="stat-label">Pass Rate</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{r.duration:.1f}s</span>
                    <span class="stat-label">Duration</span>
                </div>
            </div>
            {'<div class="failed-tests"><strong>Failed:</strong><ul>' + failed_tests_html + '</ul></div>' if failed_tests_html else ''}
            <div class="app-actions">
                <a href="{r.app_name}_report.html" class="btn btn-primary">상세 리포트</a>
                <a href="{r.app_name}_result.json" class="btn btn-secondary">JSON</a>
            </div>
        </div>
        """

    # Build common failures analysis
    failure_counts = {}
    for r in results:
        for test in r.get_failed_tests():
            test_name = test.name
            if test_name not in failure_counts:
                failure_counts[test_name] = {'count': 0, 'apps': [], 'message': test.message}
            failure_counts[test_name]['count'] += 1
            failure_counts[test_name]['apps'].append(r.app_name)

    # Sort by frequency
    common_failures = sorted(failure_counts.items(), key=lambda x: x[1]['count'], reverse=True)

    common_failures_html = ""
    for test_name, info in common_failures[:10]:
        common_failures_html += f"""
        <tr>
            <td><code>{test_name}</code></td>
            <td>{info['count']}/{total_apps}</td>
            <td>{', '.join(info['apps'][:3])}{'...' if len(info['apps']) > 3 else ''}</td>
            <td title="{info['message']}">{info['message'][:60]}...</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WF-ACT Certification Dashboard</title>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --danger: #dc2626;
            --warning: #d97706;
            --gray: #6b7280;
            --light: #f3f4f6;
            --dark: #1f2937;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: var(--light);
            padding: 20px;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; }}

        .header {{
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            color: white;
            text-align: center;
        }}

        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 16px; }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
            color: var(--primary);
        }}

        .summary-card .value.success {{ color: var(--success); }}
        .summary-card .value.danger {{ color: var(--danger); }}
        .summary-card .value.warning {{ color: var(--warning); }}

        .summary-card .label {{
            font-size: 14px;
            color: var(--gray);
            text-transform: uppercase;
            margin-top: 5px;
        }}

        .section-title {{
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--light);
        }}

        .apps-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .app-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid var(--success);
        }}

        .app-card.failed {{ border-left-color: var(--danger); }}

        .app-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}

        .app-info h3 {{ font-size: 18px; margin-bottom: 4px; }}
        .app-version {{ color: var(--gray); font-size: 12px; }}

        .app-badge {{
            text-align: center;
            padding: 10px 15px;
            border-radius: 8px;
            border: 2px solid;
        }}

        .badge-icon {{ font-size: 24px; display: block; }}
        .badge-level {{ font-size: 12px; font-weight: bold; }}

        .app-stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            padding: 10px 0;
            border-top: 1px solid var(--light);
            border-bottom: 1px solid var(--light);
        }}

        .stat {{ text-align: center; flex: 1; }}
        .stat-value {{ font-size: 18px; font-weight: bold; display: block; }}
        .stat-value.success {{ color: var(--success); }}
        .stat-value.warning {{ color: var(--warning); }}
        .stat-value.danger {{ color: var(--danger); }}
        .stat-label {{ font-size: 11px; color: var(--gray); text-transform: uppercase; }}

        .failed-tests {{
            background: #fef2f2;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
            font-size: 12px;
        }}

        .failed-tests ul {{ margin-left: 20px; margin-top: 5px; }}
        .failed-tests li {{ margin-bottom: 3px; }}

        .app-actions {{
            display: flex;
            gap: 10px;
        }}

        .btn {{
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .btn-primary {{
            background: var(--primary);
            color: white;
        }}

        .btn-primary:hover {{ background: #1d4ed8; }}

        .btn-secondary {{
            background: var(--light);
            color: var(--dark);
        }}

        .btn-secondary:hover {{ background: #e5e7eb; }}

        .analysis {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 30px;
        }}

        .analysis table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .analysis th {{
            text-align: left;
            padding: 12px;
            background: var(--light);
            font-size: 12px;
            text-transform: uppercase;
            color: var(--gray);
        }}

        .analysis td {{
            padding: 12px;
            border-bottom: 1px solid var(--light);
            font-size: 13px;
        }}

        .analysis code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }}

        .footer {{
            text-align: center;
            color: var(--gray);
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>WF-ACT Certification Dashboard</h1>
            <div class="subtitle">WF-RPA App Certification Toolkit - 통합 인증 결과</div>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="value">{total_apps}</div>
                <div class="label">Total Apps</div>
            </div>
            <div class="summary-card">
                <div class="value">{total_tests}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card">
                <div class="value success">{total_passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card">
                <div class="value danger">{total_failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="value {'success' if total_failed == 0 else 'warning' if (total_tests > 0 and total_passed/total_tests >= 0.8) else 'danger'}">{(total_passed/total_tests*100 if total_tests > 0 else 0):.1f}%</div>
                <div class="label">Pass Rate</div>
            </div>
            <div class="summary-card">
                <div class="value">{total_duration:.1f}s</div>
                <div class="label">Total Duration</div>
            </div>
        </div>

        <h2 class="section-title">App Certification Results</h2>
        <div class="apps-grid">
            {app_cards_html}
        </div>

        <h2 class="section-title">Common Failure Analysis</h2>
        <div class="analysis">
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Fail Count</th>
                        <th>Affected Apps</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {common_failures_html if common_failures_html else '<tr><td colspan="4" style="text-align:center;color:var(--success);">No common failures! All tests passed.</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by WF-ACT (WF-RPA App Certification Toolkit)</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


class ReportGenerator:
    """
    Generates certification reports.
    """

    def __init__(self, result: CertificationResult):
        """
        Initialize report generator.

        Args:
            result: Certification result to generate report for
        """
        self.result = result

    def generate_json(self, output_path: Path) -> None:
        """Generate JSON report"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.result.to_dict(), f, indent=2, ensure_ascii=False)

    def generate_html(self, output_path: Path) -> None:
        """Generate HTML report"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self._build_html()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _build_html(self) -> str:
        """Build HTML report content"""
        r = self.result

        # Determine badge color and icon
        level_styles = {
            CertificationLevel.FULL: ('gold', '🥇', '#FFD700'),
            CertificationLevel.STANDARD: ('silver', '🥈', '#C0C0C0'),
            CertificationLevel.BASIC: ('bronze', '🥉', '#CD7F32'),
            CertificationLevel.NONE: ('failed', '❌', '#DC3545'),
        }
        badge_class, badge_icon, badge_color = level_styles.get(r.level, level_styles[CertificationLevel.NONE])

        # Build suites HTML
        suites_html = ""
        for suite in r.suites:
            tests_html = ""
            for test in suite.tests:
                result_class = {
                    TestResult.PASSED: 'passed',
                    TestResult.FAILED: 'failed',
                    TestResult.SKIPPED: 'skipped',
                    TestResult.ERROR: 'error',
                }.get(test.result, 'unknown')

                result_icon = {
                    TestResult.PASSED: '✓',
                    TestResult.FAILED: '✗',
                    TestResult.SKIPPED: '○',
                    TestResult.ERROR: '⚠',
                }.get(test.result, '?')

                tests_html += f"""
                <tr class="test-row {result_class}">
                    <td class="test-icon">{result_icon}</td>
                    <td class="test-name">{test.name}</td>
                    <td class="test-desc">{test.description}</td>
                    <td class="test-level">{test.required_for.name}</td>
                    <td class="test-duration">{test.duration:.2f}s</td>
                    <td class="test-message">{test.message}</td>
                </tr>
                """

            suite_status = "passed" if suite.all_passed else "failed"
            suites_html += f"""
            <div class="suite {suite_status}">
                <div class="suite-header">
                    <h3>{suite.name}</h3>
                    <span class="suite-stats">{suite.passed_count}/{suite.total} passed</span>
                </div>
                <p class="suite-desc">{suite.description}</p>
                <table class="tests-table">
                    <thead>
                        <tr>
                            <th width="30"></th>
                            <th>Test</th>
                            <th>Description</th>
                            <th>Level</th>
                            <th>Duration</th>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tests_html}
                    </tbody>
                </table>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WF-ACT Certification Report - {r.app_name}</title>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --danger: #dc2626;
            --warning: #d97706;
            --gray: #6b7280;
            --light: #f3f4f6;
            --dark: #1f2937;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: var(--light);
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-left h1 {{
            font-size: 24px;
            margin-bottom: 5px;
        }}

        .header-left .subtitle {{
            color: var(--gray);
        }}

        .badge {{
            text-align: center;
            padding: 20px 30px;
            border-radius: 12px;
            background: linear-gradient(135deg, {badge_color}22, {badge_color}44);
            border: 2px solid {badge_color};
        }}

        .badge-icon {{
            font-size: 48px;
            display: block;
        }}

        .badge-level {{
            font-size: 18px;
            font-weight: bold;
            color: {badge_color};
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }}

        .summary {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}

        .summary-item {{
            text-align: center;
            padding: 15px;
            background: var(--light);
            border-radius: 8px;
        }}

        .summary-value {{
            font-size: 28px;
            font-weight: bold;
            color: var(--primary);
        }}

        .summary-value.success {{ color: var(--success); }}
        .summary-value.danger {{ color: var(--danger); }}

        .summary-label {{
            font-size: 12px;
            color: var(--gray);
            text-transform: uppercase;
        }}

        .suite {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .suite.failed {{
            border-left: 4px solid var(--danger);
        }}

        .suite.passed {{
            border-left: 4px solid var(--success);
        }}

        .suite-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .suite-header h3 {{
            font-size: 18px;
        }}

        .suite-stats {{
            background: var(--light);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
        }}

        .suite-desc {{
            color: var(--gray);
            margin-bottom: 15px;
        }}

        .tests-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .tests-table th {{
            text-align: left;
            padding: 10px;
            background: var(--light);
            font-size: 12px;
            text-transform: uppercase;
            color: var(--gray);
        }}

        .tests-table td {{
            padding: 10px;
            border-bottom: 1px solid var(--light);
        }}

        .test-row.passed {{ }}
        .test-row.failed {{ background: #fef2f2; }}
        .test-row.skipped {{ opacity: 0.6; }}
        .test-row.error {{ background: #fffbeb; }}

        .test-icon {{
            font-size: 16px;
            text-align: center;
        }}

        .test-row.passed .test-icon {{ color: var(--success); }}
        .test-row.failed .test-icon {{ color: var(--danger); }}
        .test-row.skipped .test-icon {{ color: var(--gray); }}
        .test-row.error .test-icon {{ color: var(--warning); }}

        .test-name {{
            font-family: monospace;
            font-size: 13px;
        }}

        .test-desc {{
            font-size: 13px;
        }}

        .test-level {{
            font-size: 11px;
            color: var(--gray);
        }}

        .test-duration {{
            font-size: 12px;
            color: var(--gray);
        }}

        .test-message {{
            font-size: 12px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .footer {{
            text-align: center;
            color: var(--gray);
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>WF-ACT Certification Report</h1>
                <div class="subtitle">
                    {r.app_name} | {r.app_version}
                </div>
            </div>
            <div class="badge">
                <span class="badge-icon">{badge_icon}</span>
                <span class="badge-level">{r.level.name}</span>
            </div>
        </div>

        <div class="summary">
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{r.total_tests}</div>
                    <div class="summary-label">Total Tests</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value success">{r.passed_tests}</div>
                    <div class="summary-label">Passed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value danger">{r.failed_tests}</div>
                    <div class="summary-label">Failed</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{r.duration:.1f}s</div>
                    <div class="summary-label">Duration</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{r.start_time.strftime('%H:%M:%S') if r.start_time else '-'}</div>
                    <div class="summary-label">Started</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{r.end_time.strftime('%H:%M:%S') if r.end_time else '-'}</div>
                    <div class="summary-label">Finished</div>
                </div>
            </div>
        </div>

        {suites_html}

        <div class="footer">
            <p>Generated by WF-ACT (WF-RPA App Certification Toolkit)</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
