# -*- coding: utf-8 -*-
"""
WF-ACT Certification Engine
===========================
Manages test execution and certification decisions.

Usage:
    engine = CertificationEngine()
    engine.register_suite(RegistrationSuite)
    engine.register_suite(CreditSuite)

    result = engine.run_certification('bom_exporter')
    print(result.level)  # CertificationLevel.FULL
    print(result.passed)  # True
"""

import time
import logging
import traceback
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SkipTest(Exception):
    """Raised to indicate a skipped test."""
    pass


class CertificationLevel(Enum):
    """Certification levels"""
    NONE = 0        # Failed basic tests
    BASIC = 1       # Core functionality works
    STANDARD = 2    # Common scenarios pass
    FULL = 3        # All tests including edge cases pass


class TestResult(Enum):
    """Individual test result"""
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ERROR = auto()


@dataclass
class TestCase:
    """Individual test case result"""
    name: str
    description: str
    result: TestResult
    duration: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    required_for: CertificationLevel = CertificationLevel.BASIC

    @property
    def passed(self) -> bool:
        return self.result == TestResult.PASSED


@dataclass
class SuiteResult:
    """Test suite result"""
    name: str
    description: str
    tests: List[TestCase] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tests if t.result == TestResult.FAILED)

    @property
    def error_count(self) -> int:
        return sum(1 for t in self.tests if t.result == TestResult.ERROR)

    @property
    def skipped_count(self) -> int:
        return sum(1 for t in self.tests if t.result == TestResult.SKIPPED)

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return sum(t.duration for t in self.tests)

    @property
    def all_passed(self) -> bool:
        return all(t.passed or t.result == TestResult.SKIPPED for t in self.tests)


@dataclass
class CertificationResult:
    """Overall certification result"""
    app_name: str
    app_version: str = ""
    level: CertificationLevel = CertificationLevel.NONE
    suites: List[SuiteResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        return self.level != CertificationLevel.NONE

    @property
    def total_tests(self) -> int:
        return sum(s.total for s in self.suites)

    @property
    def passed_tests(self) -> int:
        return sum(s.passed_count for s in self.suites)

    @property
    def failed_tests(self) -> int:
        return sum(s.failed_count for s in self.suites)

    @property
    def skipped_tests(self) -> int:
        """Get total skipped tests count"""
        return sum(s.skipped_count for s in self.suites)

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def get_failed_tests(self) -> List[TestCase]:
        """Get all failed tests"""
        failed = []
        for suite in self.suites:
            for test in suite.tests:
                if test.result == TestResult.FAILED or test.result == TestResult.ERROR:
                    failed.append(test)
        return failed

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'app_name': self.app_name,
            'app_version': self.app_version,
            'level': self.level.name,
            'passed': self.passed,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'duration': self.duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error': self.error,
            'suites': [
                {
                    'name': s.name,
                    'description': s.description,
                    'total': s.total,
                    'passed': s.passed_count,
                    'failed': s.failed_count,
                    'skipped': s.skipped_count,
                    'duration': s.duration,
                    'tests': [
                        {
                            'name': t.name,
                            'description': t.description,
                            'result': t.result.name,
                            'duration': t.duration,
                            'message': t.message,
                            'required_for': t.required_for.name,
                        }
                        for t in s.tests
                    ]
                }
                for s in self.suites
            ]
        }


class CertificationEngine:
    """
    Main certification engine.
    Manages test suites and executes certification.
    """

    def __init__(self, output_dir: Optional[Path] = None, dev_mode: bool = True):
        """
        Initialize certification engine.

        Args:
            output_dir: Directory for test results (default: test_results/)
            dev_mode: If True, run from Python source; if False, run from packaged exe
        """
        self.suites: List[Type['BaseSuite']] = []
        self.output_dir = output_dir or Path(__file__).parent.parent / 'test_results'
        self.dev_mode = dev_mode

    def register_suite(self, suite_class: Type['BaseSuite']) -> None:
        """Register a test suite"""
        self.suites.append(suite_class)
        logger.info(f"[CertEngine] Registered suite: {suite_class.__name__}")

    def run_certification(self, app_name: str, target_level: CertificationLevel = CertificationLevel.FULL) -> CertificationResult:
        """
        Run certification for an app.

        Args:
            app_name: Application identifier
            target_level: Target certification level

        Returns:
            CertificationResult with all test results
        """
        result = CertificationResult(app_name=app_name)
        result.start_time = datetime.now()

        logger.info(f"{'='*60}")
        logger.info(f"  WF-ACT Certification: {app_name}")
        logger.info(f"  Target Level: {target_level.name}")
        logger.info(f"{'='*60}")

        try:
            # Import TestClient here to avoid circular imports
            from .test_client import TestClient

            # Create client and launch app (dev_mode or exe mode)
            client = TestClient(app_name, dev_mode=self.dev_mode)
            result.app_version = str(client.config.exe_path.parent.name) if client.config.exe_path else "unknown"

            if not client.launch_app():
                result.error = f"Failed to launch {app_name} in test mode"
                logger.error(f"[CertEngine] {result.error}")
                result.end_time = datetime.now()
                return result

            try:
                # Run each suite
                for suite_class in self.suites:
                    try:
                        suite_result = self._run_suite(suite_class, client, target_level)
                        result.suites.append(suite_result)

                        # Log suite summary
                        status = "PASS" if suite_result.all_passed else "FAIL"
                        logger.info(f"  [{status}] {suite_result.name}: {suite_result.passed_count}/{suite_result.total}")
                    except Exception as suite_error:
                        logger.error(f"[CertEngine] Suite error: {suite_error}")
                        logger.error(traceback.format_exc())

            finally:
                # Terminate app with extra wait time for EXE mode (single-instance cleanup)
                wait_time = 2.0 if not self.dev_mode else 0.5
                client.terminate_app(wait_time=wait_time)

            # Determine certification level
            result.level = self._determine_level(result)

        except Exception as e:
            logger.error(f"[CertEngine] Error: {e}")
            logger.error(traceback.format_exc())
            result.error = str(e)

        result.end_time = datetime.now()

        # Log final result
        logger.info(f"{'='*60}")
        logger.info(f"  Certification Result: {result.level.name}")
        logger.info(f"  Tests: {result.passed_tests}/{result.total_tests} passed")
        logger.info(f"  Duration: {result.duration:.1f}s")
        logger.info(f"{'='*60}")

        return result

    def _run_suite(self, suite_class: Type['BaseSuite'], client: 'TestClient', target_level: CertificationLevel) -> SuiteResult:
        """Run a single test suite"""
        suite = suite_class(client)
        suite_result = SuiteResult(
            name=suite.name,
            description=suite.description,
            start_time=datetime.now()
        )

        logger.info(f"\n[Suite] {suite.name}")
        logger.info(f"  {suite.description}")
        logger.info("-" * 40)

        # Check if suite should be skipped
        if hasattr(suite, 'should_skip') and callable(suite.should_skip):
            if suite.should_skip():
                logger.info(f"  [SKIP] Suite skipped")
                suite_result.end_time = datetime.now()
                return suite_result

        try:
            suite.setup()

            for test_method in suite.get_test_methods():
                test_case = self._run_test(suite, test_method, target_level)
                suite_result.tests.append(test_case)

                # Log test result
                icon = "✓" if test_case.passed else "✗"
                logger.info(f"  {icon} {test_case.name}: {test_case.message}")

        except Exception as e:
            logger.error(f"[Suite] Setup/teardown error: {e}")
        finally:
            try:
                suite.teardown()
            except:
                pass

        suite_result.end_time = datetime.now()
        return suite_result

    def _run_test(self, suite: 'BaseSuite', test_method: callable, target_level: CertificationLevel) -> TestCase:
        """Run a single test"""
        test_name = test_method.__name__
        test_doc = test_method.__doc__ or test_name
        required_level = getattr(test_method, '_required_level', CertificationLevel.BASIC)

        # Skip if above target level
        if required_level.value > target_level.value:
            return TestCase(
                name=test_name,
                description=test_doc,
                result=TestResult.SKIPPED,
                message=f"Skipped (requires {required_level.name})",
                required_for=required_level
            )

        start_time = time.time()

        try:
            test_method()
            duration = time.time() - start_time

            return TestCase(
                name=test_name,
                description=test_doc,
                result=TestResult.PASSED,
                duration=duration,
                message="Passed",
                required_for=required_level
            )

        except AssertionError as e:
            duration = time.time() - start_time
            return TestCase(
                name=test_name,
                description=test_doc,
                result=TestResult.FAILED,
                duration=duration,
                message=str(e) or "Assertion failed",
                required_for=required_level
            )

        except SkipTest as e:
            duration = time.time() - start_time
            return TestCase(
                name=test_name,
                description=test_doc,
                result=TestResult.SKIPPED,
                duration=duration,
                message=str(e) or "Skipped",
                required_for=required_level
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[Test] Error in {test_name}: {e}")
            return TestCase(
                name=test_name,
                description=test_doc,
                result=TestResult.ERROR,
                duration=duration,
                message=str(e),
                required_for=required_level
            )

    def _determine_level(self, result: CertificationResult) -> CertificationLevel:
        """Determine achieved certification level"""
        # Check each level from highest to lowest
        for level in [CertificationLevel.FULL, CertificationLevel.STANDARD, CertificationLevel.BASIC]:
            level_passed = True

            for suite in result.suites:
                for test in suite.tests:
                    if test.required_for.value <= level.value:
                        if not test.passed and test.result != TestResult.SKIPPED:
                            level_passed = False
                            break
                if not level_passed:
                    break

            if level_passed:
                return level

        return CertificationLevel.NONE


def requires_level(level: CertificationLevel):
    """Decorator to mark test's required certification level"""
    def decorator(func):
        func._required_level = level
        return func
    return decorator
