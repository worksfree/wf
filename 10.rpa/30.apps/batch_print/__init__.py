# -*- coding: utf-8 -*-
"""
Batch Print Package
"""

__version__ = "0.1.0"
__author__ = "WorksFree"

from .automation import BatchPrintAutomation
from .app_setting_data import get_config, Config

__all__ = [
    "BatchPrintAutomation",
    "get_config",
    "Config",
]
