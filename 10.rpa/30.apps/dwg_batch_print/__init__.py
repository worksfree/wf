# -*- coding: utf-8 -*-
"""
DWG Batch Print Package
"""

__version__ = "0.1.0"
__author__ = "WorksFree"

from .automation import DwgBatchPrintAutomation
from .app_setting_data import get_config, Config

__all__ = [
    "DwgBatchPrintAutomation",
    "get_config",
    "Config",
]
