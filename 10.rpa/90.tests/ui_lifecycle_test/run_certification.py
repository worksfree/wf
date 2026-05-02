# -*- coding: utf-8 -*-
"""
WF-ACT - WF-RPA App Certification Toolkit
=========================================

앱 라이프사이클 인증 도구

Usage:
    python run_certification.py                    # 모든 앱 인증 (FULL 레벨)
    python run_certification.py --app bom_exporter # 특정 앱만 인증
    python run_certification.py --level basic      # BASIC 레벨만 테스트
    python run_certification.py --list             # 테스트 목록 출력
    python run_certification.py --help             # 도움말

인증 레벨:
    BASIC    - 핵심 기능 (40개 필수 테스트)
    STANDARD - 일반 시나리오 (60개 테스트)
    FULL     - 모든 테스트 (76개+ 테스트)

출력:
    test_results/certification_YYYYMMDD_HHMMSS/
    ├── certification_report.html  # 웹 리포트
    ├── certification_result.json  # JSON 결과
    └── {app_name}_result.json     # 앱별 상세 결과
"""

import sys
import argparse
import logging
import io
import shutil
import time
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core import CertificationEngine, CertificationLevel, ReportGenerator, generate_index_html
from suites import ALL_SUITES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def backup_user_home():
    """Backup user .wf_rpa directory for clean EXE testing"""
    user_wf_dir = Path.home() / ".wf_rpa"
    backup_dir = Path.home() / ".wf_rpa.bak"
    
    if not user_wf_dir.exists():
        logger.info("[Backup] User home does not exist, nothing to backup")
        return backup_dir  # Return backup path even if nothing to backup
    
    # Remove old backup if exists (force remove with retries)
    if backup_dir.exists():
        try:
            shutil.rmtree(backup_dir)
            logger.info(f"[Backup] Removed old backup: {backup_dir}")
            time.sleep(0.3)  # Wait for file system to update
        except Exception as e:
            logger.warning(f"[Backup] Failed to remove old backup: {e}")
            # Try alternative: rename then remove
            try:
                temp_dir = Path.home() / f".wf_rpa.bak.{int(time.time())}"
                shutil.move(str(backup_dir), str(temp_dir))
                logger.info(f"[Backup] Moved old backup to temp: {temp_dir}")
            except Exception as e2:
                logger.error(f"[Backup] Failed to move old backup: {e2}")
            time.sleep(0.5)
    
    # Backup current .wf_rpa to .wf_rpa.bak (copy, not move)
    try:
        shutil.copytree(str(user_wf_dir), str(backup_dir))
        logger.info(f"[Backup] User home backed up: {user_wf_dir} → {backup_dir}")
        time.sleep(0.3)  # Wait for file system
        
        # Remove original after successful copy
        shutil.rmtree(str(user_wf_dir))
        logger.info(f"[Backup] Removed original: {user_wf_dir}")
        time.sleep(0.3)
        return backup_dir
    except Exception as e:
        logger.error(f"[Backup] Failed to backup user home: {e}")
        raise


def restore_user_home(backup_dir: Path):
    """Restore user .wf_rpa directory from backup"""
    user_wf_dir = Path.home() / ".wf_rpa"
    
    if not backup_dir or not backup_dir.exists():
        logger.info("[Restore] No backup to restore")
        return  # Nothing to restore
    
    # Remove current .wf_rpa if exists (force remove with retries)
    if user_wf_dir.exists():
        try:
            shutil.rmtree(str(user_wf_dir))
            logger.info(f"[Restore] Removed current .wf_rpa: {user_wf_dir}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"[Restore] Failed to remove current .wf_rpa: {e}")
            # Try alternative: rename
            try:
                temp_dir = Path.home() / f".wf_rpa.old.{int(time.time())}"
                shutil.move(str(user_wf_dir), str(temp_dir))
                logger.info(f"[Restore] Moved current to temp: {temp_dir}")
            except Exception as e2:
                logger.error(f"[Restore] Failed to move current .wf_rpa: {e2}")
            time.sleep(0.5)
    
    # Restore from backup (copy, not move)
    try:
        shutil.copytree(str(backup_dir), str(user_wf_dir))
        logger.info(f"[Restore] User home restored: {backup_dir} → {user_wf_dir}")
        time.sleep(0.3)  # Wait for file system
        
        # Remove backup after successful restore
        shutil.rmtree(str(backup_dir))
        logger.info(f"[Restore] Removed backup: {backup_dir}")
        
    except Exception as e:
        logger.error(f"[Restore] Failed to restore user home: {e}")


# Supported apps (7 apps total)
SUPPORTED_APPS = [
    'bom_exporter',
    'dwg_classifier',
    'batch_print',
    'conversion_verifier',
    'korean_filename_normalizer',
    'attribute_reset',
    'qrcode_generator',
]


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='WF-ACT - WF-RPA App Certification Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
인증 레벨:
  BASIC    - 핵심 기능 테스트 (필수)
  STANDARD - 일반 시나리오 테스트
  FULL     - 모든 엣지케이스 테스트

예시:
  %(prog)s                           # 모든 앱, FULL 레벨
  %(prog)s --app bom_exporter        # BOM Exporter만
  %(prog)s --level standard          # STANDARD 레벨까지
  %(prog)s --app be dc --level basic # 여러 앱, BASIC 레벨
        """
    )

    parser.add_argument(
        '--app', '-a',
        nargs='+',
        help='인증할 앱 (기본: 모든 앱). 사용 가능: ' + ', '.join(SUPPORTED_APPS)
    )

    parser.add_argument(
        '--level', '-l',
        choices=['basic', 'standard', 'full'],
        default='full',
        help='인증 레벨 (기본: full)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='결과 저장 디렉토리 (기본: test_results/certification_TIMESTAMP)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='테스트 목록만 출력'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 로그 출력'
    )

    parser.add_argument(
        '--exe',
        action='store_true',
        help='패키징된 EXE 파일 대상 인증 (기본: 소스코드 dev 모드)'
    )

    parser.add_argument(
        '--candidates-dir',
        type=Path,
        help='EXE 후보 디렉토리 (기본: D:/release/candidates)'
    )

    return parser.parse_args()


def resolve_app_names(app_args):
    """Resolve app name shortcuts"""
    if not app_args:
        return SUPPORTED_APPS

    shortcuts = {
        'be': 'bom_exporter',
        'dc': 'dwg_classifier',
        'bp': 'batch_print',
        'dp': 'batch_print',
        'dbp': 'batch_print',
        'dwg_batch_print': 'batch_print',
        'cv': 'conversion_verifier',
        'kfn': 'korean_filename_normalizer',
        'ar': 'attribute_reset',
        'qr': 'qrcode_generator',
    }

    resolved = []
    for name in app_args:
        name = name.lower()
        if name in shortcuts:
            resolved.append(shortcuts[name])
        elif name in SUPPORTED_APPS:
            resolved.append(name)
        else:
            logger.warning(f"알 수 없는 앱: {name}")

    return resolved


def list_tests():
    """List all tests"""
    print("\n" + "=" * 60)
    print("WF-ACT Test Suites")
    print("=" * 60)

    total = 0

    for suite_class in ALL_SUITES:
        # Create dummy instance to get test list
        class DummyClient:
            config = type('Config', (), {
                'name': 'dummy',
                'credit_per_work': 100,
                'trial_credits': 10000
            })()
            def call(self, *args, **kwargs):
                pass

        suite = suite_class(DummyClient())
        tests = suite.get_test_methods()

        print(f"\n{suite.name}")
        print(f"  {suite.description}")
        print("-" * 40)

        for test in tests:
            level = getattr(test, '_required_level', CertificationLevel.BASIC)
            doc = test.__doc__ or test.__name__
            print(f"  [{level.name:8}] {test.__name__}")
            print(f"             {doc.strip()}")
            total += 1

    print("\n" + "=" * 60)
    print(f"Total: {total} tests")
    print("=" * 60 + "\n")


def run_certification(apps, level, output_dir, dev_mode=True, candidates_dir=None):
    """Run certification for specified apps

    Args:
        apps: List of app names to certify
        level: Certification level (basic, standard, full)
        output_dir: Output directory for results
        dev_mode: If True, test source code; if False, test packaged exe
        candidates_dir: Directory containing packaged exe candidates
    """
    # Setup output directory
    mode_suffix = "dev" if dev_mode else "exe"
    if not output_dir:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(__file__).parent / 'test_results' / f'certification_{timestamp}_{mode_suffix}'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Map level string to enum
    level_map = {
        'basic': CertificationLevel.BASIC,
        'standard': CertificationLevel.STANDARD,
        'full': CertificationLevel.FULL,
    }
    target_level = level_map[level]

    # Create certification engine with dev_mode
    engine = CertificationEngine(output_dir, dev_mode=dev_mode)

    # Update candidates directory if specified
    if candidates_dir and not dev_mode:
        from core.test_client import TestClient
        TestClient.CANDIDATES_DIR = candidates_dir

    # Register all suites
    for suite_class in ALL_SUITES:
        engine.register_suite(suite_class)

    # Run certification for each app
    results = []
    backup_dir = None

    print("\n" + "=" * 70)
    print("  WF-ACT - WF-RPA App Certification Toolkit")
    print("=" * 70)
    print(f"  Mode: {'DEV (Source Code)' if dev_mode else 'EXE (Packaged)'}")
    print(f"  Target Level: {target_level.name}")
    print(f"  Apps: {', '.join(apps)}")
    print(f"  Output: {output_dir}")
    print("=" * 70 + "\n")

    # Backup user home before EXE mode testing
    if not dev_mode:
        logger.info("[Setup] EXE 모드: 사용자 홈 폴더 백업 중...")
        backup_dir = backup_user_home()

    try:
        for app_name in apps:
            print(f"\n{'#' * 70}")
            print(f"  Certifying: {app_name}")
            print(f"{'#' * 70}\n")

            try:
                result = engine.run_certification(app_name, target_level)
                results.append(result)

                # Save individual result
                report = ReportGenerator(result)
                report.generate_json(output_dir / f'{app_name}_result.json')

            except Exception as e:
                logger.error(f"인증 실패 ({app_name}): {e}")
                import traceback
                traceback.print_exc()

    finally:
        # Restore user home after EXE mode testing
        if not dev_mode and backup_dir:
            logger.info("[Cleanup] 사용자 홈 폴더 복원 중...")
            restore_user_home(backup_dir)

    # Generate reports
    if results:
        # Generate individual app reports
        for result in results:
            report = ReportGenerator(result)
            report.generate_html(output_dir / f'{result.app_name}_report.html')
            report.generate_json(output_dir / f'{result.app_name}_result.json')

        # Generate unified index.html with all apps
        index_path = generate_index_html(results, output_dir)
        print(f"\n  📊 Unified report: {index_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("  CERTIFICATION SUMMARY")
    print("=" * 80)

    for result in results:
        icon = {
            CertificationLevel.FULL: '🥇',
            CertificationLevel.STANDARD: '🥈',
            CertificationLevel.BASIC: '🥉',
            CertificationLevel.NONE: '❌',
        }.get(result.level, '?')

        # 테스트 통계 계산
        passed = result.passed_tests
        failed = result.failed_tests
        total = result.total_tests
        skipped = result.skipped_tests
        executed = total - skipped  # 실제 실행된 테스트

        # 진행률 계산
        if total > 0:
            pass_rate = (passed / total * 100) if total > 0 else 0
        else:
            pass_rate = 0

        print(f"\n  {icon} {result.app_name}")
        print(f"     Level: {result.level.name}")
        print(f"     통과: {passed} | 스킵: {skipped} | 실패: {failed} | 전체: {total} ({pass_rate:.1f}%)")
        print(f"     Duration: {result.duration:.1f}s")

        if result.failed_tests > 0:
            print(f"     ❌ 실패 테스트:")
            for test in result.get_failed_tests()[:5]:  # Show first 5
                print(f"       - {test.name}: {test.message}")
            if len(result.get_failed_tests()) > 5:
                print(f"       ... and {len(result.get_failed_tests()) - 5} more")
        elif skipped > 0:
            print(f"     ⏭️  {skipped}개 테스트 스킵됨 (무료앱/API 한도)")

    print("\n" + "=" * 80)
    print(f"  Results saved to: {output_dir}")
    print("=" * 80 + "\n")

    # Open index.html in browser
    if results:
        index_path = output_dir / 'index.html'
        if index_path.exists():
            import webbrowser
            try:
                webbrowser.open(str(index_path.absolute()))
                print(f"  🌐 Opening results in browser: {index_path}")
            except Exception as e:
                logger.warning(f"Failed to open browser: {e}")

    # Return overall success
    return all(r.passed for r in results)


def main():
    """Main entry point"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        list_tests()
        return 0

    apps = resolve_app_names(args.app)

    if not apps:
        logger.error("인증할 앱이 없습니다.")
        return 1

    # dev_mode: True for source code, False for exe
    dev_mode = not args.exe

    # 🔥 인증 전 사용자 홈 정리 (DEV 모드에서는 스킵, demo/release만 실행)
    # DEV 모드는 10.common/config/{app}/ 하의 설정만 사용하므로 cleanup 불필요
    if not dev_mode:
        logger.info("\n" + "="*70)
        logger.info("[CERTIFICATION INIT] 사용자 홈 설정 초기화 중 (exe 모드)...")
        logger.info("="*70)
        try:
            from cleanup_user_home import cleanup_user_home
            if not cleanup_user_home():
                logger.warning("[WARNING] 사용자 홈 정리 중 오류가 발생했으나 계속 진행합니다.")
        except Exception as e:
            logger.warning(f"[WARNING] 사용자 홈 정리 실패(무시): {e}")
        
        logger.info("[CERTIFICATION INIT] ✅ 초기화 완료 - 인증 시작\n")
    else:
        logger.info("\n" + "="*70)
        logger.info("[CERTIFICATION INIT] DEV 모드 - 사용자 홈 정리 스킵")
        logger.info("="*70)
        logger.info("[CERTIFICATION INIT] ✅ 소스 설정만 사용 - 인증 시작\n")

    success = run_certification(
        apps,
        args.level,
        args.output,
        dev_mode=dev_mode,
        candidates_dir=args.candidates_dir
    )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
