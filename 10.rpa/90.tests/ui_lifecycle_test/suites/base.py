# -*- coding: utf-8 -*-
"""
WF-ACT Base Test Suite
======================
Base class for all certification test suites.
"""

import logging
from typing import List, Callable, Any
from abc import ABC, abstractmethod
from core.certification import SkipTest

logger = logging.getLogger(__name__)


class BaseSuite(ABC):
    """
    Base class for certification test suites.

    Subclasses should:
    1. Set `name` and `description` class attributes
    2. Define test methods prefixed with `test_`
    3. Use assertions for test verification

    Example:
        class MySuite(BaseSuite):
            name = "My Suite"
            description = "Tests my functionality"

            def test_something(self):
                '''Test that something works'''
                result = self.client.call('get_something')
                assert result == expected, "Something is wrong"
    """

    name: str = "Base Suite"
    description: str = "Base test suite"

    def __init__(self, client: 'TestClient'):
        """
        Initialize suite with test client.

        Args:
            client: TestClient instance connected to app
        """
        self.client = client
        self.app_config = client.config

    def setup(self) -> None:
        """
        Setup before running tests.
        Override in subclass if needed.
        """
        pass

    def teardown(self) -> None:
        """
        Cleanup after running tests.
        Override in subclass if needed.
        """
        pass

    def get_test_methods(self) -> List[Callable]:
        """Get all test methods in this suite"""
        methods = []
        for name in dir(self):
            if name.startswith('test_'):
                method = getattr(self, name)
                if callable(method):
                    methods.append(method)
        # Sort by name to ensure consistent order
        methods.sort(key=lambda m: m.__name__)
        return methods

    # === Helper methods for tests ===

    def call(self, command: str, *args, **kwargs) -> Any:
        """Shortcut to client.call()"""
        return self.client.call(command, *args, **kwargs)

    def assert_equal(self, actual: Any, expected: Any, message: str = "") -> None:
        """Assert two values are equal"""
        if actual != expected:
            msg = message or f"Expected {expected}, got {actual}"
            raise AssertionError(msg)

    def assert_true(self, condition: bool, message: str = "") -> None:
        """Assert condition is true"""
        if not condition:
            msg = message or "Condition is not true"
            raise AssertionError(msg)

    def assert_false(self, condition: bool, message: str = "") -> None:
        """Assert condition is false"""
        if condition:
            msg = message or "Condition is not false"
            raise AssertionError(msg)

    def assert_greater(self, a: Any, b: Any, message: str = "") -> None:
        """Assert a > b"""
        if not (a > b):
            msg = message or f"Expected {a} > {b}"
            raise AssertionError(msg)

    def assert_less(self, a: Any, b: Any, message: str = "") -> None:
        """Assert a < b"""
        if not (a < b):
            msg = message or f"Expected {a} < {b}"
            raise AssertionError(msg)

    def assert_in(self, item: Any, container: Any, message: str = "") -> None:
        """Assert item in container"""
        if item not in container:
            msg = message or f"Expected {item} in {container}"
            raise AssertionError(msg)

    def assert_not_none(self, value: Any, message: str = "") -> None:
        """Assert value is not None"""
        if value is None:
            msg = message or "Value is None"
            raise AssertionError(msg)

    def fail(self, message: str = "") -> None:
        """Fail the current test with a message"""
        raise AssertionError(message or "Test failed")

    def skip(self, message: str = "") -> None:
        """Skip the current test with a message"""
        raise SkipTest(message or "Skipped")

    def assert_raises(self, exception_type: type, func: Callable, *args, **kwargs) -> None:
        """Assert function raises specific exception"""
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} was not raised")
        except exception_type:
            pass  # Expected

    def get_credits(self) -> int:
        """Get current credits"""
        return self.call('get_credits')

    def set_credits(self, amount: int) -> None:
        """Set credits to specific amount"""
        self.call('set_credits', amount)

    def get_registration_status(self) -> dict:
        """Get registration status"""
        return self.call('get_registration_status')

    def simulate_work(self, file_count: int = 1) -> dict:
        """Simulate work operation"""
        return self.call('simulate_work', file_count)

    def get_state(self) -> dict:
        """Get app state"""
        return self.call('get_state')

    def is_free_app(self) -> bool:
        """Check if this is a free app (trial_credits=-1)"""
        return self.app_config.trial_credits == -1
