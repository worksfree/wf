# -*- coding: utf-8 -*-
"""
WF-ACT Test Suites
==================
Certification test suites for WF-RPA apps.

Suites:
- DeploymentSuite: Deployment files and environment tests
- PackageIntegritySuite: Package integrity tests (EXE mode only)
- ConfigSuite: Configuration tests
- SecuritySuite: Security compliance tests
- RegistrationSuite: Registration lifecycle tests
- CreditSuite: Credit system tests
- StateSuite: State management tests
- RecoverySuite: Error recovery tests
- UISuite: UI responsiveness tests
"""

from .base import BaseSuite
from .cert_deployment import DeploymentSuite
from .cert_package import PackageIntegritySuite
from .cert_env import ExecutionEnvironmentSuite
from .cert_registration import RegistrationSuite
from .cert_trial_mode import TrialModeSuite
from .cert_credits import CreditSuite
from .cert_state import StateSuite
from .cert_config import ConfigSuite
from .cert_recovery import RecoverySuite
from .cert_ui import UISuite
from .cert_security import SecuritySuite

# All suites in recommended execution order
ALL_SUITES = [
    DeploymentSuite,             # Deployment files first (static checks)
    PackageIntegritySuite,       # Package integrity second (EXE mode only)
    ExecutionEnvironmentSuite,   # Execution environment third (DEV/EXE mode detection)
    ConfigSuite,                 # Configuration fourth
    SecuritySuite,               # Security checks fifth
    RegistrationSuite,           # Then registration
    TrialModeSuite,              # Then trial mode (30-day evaluation) - NEW
    CreditSuite,                 # Then credit system
    StateSuite,                  # Then state management
    RecoverySuite,               # Then error recovery
    UISuite,                     # Finally UI responsiveness
]

__all__ = [
    'BaseSuite',
    'DeploymentSuite',
    'PackageIntegritySuite',
    'ExecutionEnvironmentSuite',
    'ConfigSuite',
    'SecuritySuite',
    'RegistrationSuite',
    'TrialModeSuite',
    'CreditSuite',
    'StateSuite',
    'RecoverySuite',
    'UISuite',
    'ALL_SUITES',
]
