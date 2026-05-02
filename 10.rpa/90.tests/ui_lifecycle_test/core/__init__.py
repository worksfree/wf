# -*- coding: utf-8 -*-
"""
WF-ACT Core Module
==================
WF-RPA App Certification Toolkit - Core Components

Components:
- TestServer: IPC server for apps (apps import this)
- TestClient: IPC client for test framework
- CertificationEngine: Test execution and certification
- ReportGenerator: HTML/JSON report generation
"""

from .test_server import TestServer, TestMode
from .test_client import TestClient
from .certification import CertificationEngine, CertificationLevel
from .report import ReportGenerator, generate_index_html

__all__ = [
    'TestServer',
    'TestMode',
    'TestClient',
    'CertificationEngine',
    'CertificationLevel',
    'ReportGenerator',
    'generate_index_html',
]
