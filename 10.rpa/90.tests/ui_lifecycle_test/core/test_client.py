# -*- coding: utf-8 -*-
"""
WF-ACT Test Client
==================
IPC client for test framework to communicate with apps in test mode.

Usage:
    client = TestClient('bom_exporter')
    client.connect()

    # Get state
    credits = client.call('get_credits')

    # Execute action
    client.call('click_button', 'work')

    # Set state
    client.call('set_credits', 500)

    client.disconnect()
"""

import json
import socket
import subprocess
import time
import logging
import shutil
from typing import Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration for testing"""
    name: str
    display_name: str
    exe_path: Path
    port: int
    credit_per_work: int
    trial_credits: int
    policy: dict = None


class TestClient:
    """
    IPC client for communicating with apps in test mode.
    """

    BASE_PORT = 19800
    CANDIDATES_DIR = Path("D:/release/candidates")
    DEV_APPS_DIR = Path("D:/drive_files/10.worksfree/10.rpa/30.apps")
    USER_HOME_WF_DIR = Path.home() / ".wf_rpa"
    
    # Apps in different directories (50.data instead of 30.apps)
    APP_DIR_OVERRIDES = {
        'dwg_classifier': Path("D:/drive_files/10.worksfree/10.rpa/50.data/dwg_classifier"),
        'conversion_verifier': Path("D:/drive_files/10.worksfree/10.rpa/50.data/conversion_verifier"),
        'korean_filename_normalizer': Path("D:/drive_files/10.worksfree/10.rpa/50.data/korean_filename_normalizer"),
        'qrcode_generator': Path("D:/drive_files/10.worksfree/10.rpa/50.data/qrcode_generator"),
    }

    def __init__(self, app_name: str, timeout: float = 30.0, dev_mode: bool = True):
        """
        Initialize test client.

        Args:
            app_name: Application identifier (e.g., 'bom_exporter')
            timeout: Socket timeout in seconds
            dev_mode: If True, run from Python source; if False, run from exe
        """
        self.app_name = app_name
        self.timeout = timeout
        self.dev_mode = dev_mode
        self.port = self._get_port_for_app(app_name)
        self.process: Optional[subprocess.Popen] = None
        self.config = self._load_app_config(app_name)

    @staticmethod
    def cleanup_user_home() -> None:
        """Clean up user home .wf_rpa directory for fresh EXE testing"""
        user_wf_dir = TestClient.USER_HOME_WF_DIR
        if user_wf_dir.exists():
            try:
                shutil.rmtree(user_wf_dir)
                logger.info(f"[TestClient] Cleaned user home: {user_wf_dir}")
                time.sleep(0.5)  # Wait for file system
            except Exception as e:
                logger.warning(f"[TestClient] Failed to clean user home: {e}")

    def _get_port_for_app(self, app_name: str) -> int:
        """Get deterministic port for app name"""
        app_ports = {
            'bom_exporter': 0,
            'dwg_classifier': 1,
            'dwg_batch_print': 2,
            'batch_print': 2,
            'conversion_verifier': 3,
            'korean_filename_normalizer': 4,
            'attribute_reset': 5,
            'qrcode_generator': 6,
        }
        offset = app_ports.get(app_name, hash(app_name) % 100)
        return self.BASE_PORT + offset

    def _load_app_config(self, app_name: str) -> AppConfig:
        """Load app configuration"""
        # App metadata (from BASIC_RULES.md Part 2.1)
        app_info = {
            'bom_exporter': {
                'display_name': 'BOM Exporter',
                'credit_per_work': 100,
                'trial_credits': 50000,
                'pricing_model': 'trial_500works',
                'auto_activate_trial': True,
                'require_registration': False,
                'max_installations': 1,
                'hardware_based_activation': True,
            },
            'dwg_classifier': {
                'display_name': 'DWG Classifier',
                'credit_per_work': 50,
                'trial_credits': 25000,
                'pricing_model': 'trial_500works',
                'auto_activate_trial': True,
                'require_registration': False,
                'max_installations': 1,
                'hardware_based_activation': True,
            },
            'dwg_batch_print': {
                'display_name': 'DWG Batch Print',
                'credit_per_work': 40,
                'trial_credits': 20000,
                'pricing_model': 'trial_500works',
                'auto_activate_trial': True,
                'require_registration': False,
                'max_installations': 1,
                'hardware_based_activation': True,
            },
            'batch_print': {
                'display_name': 'Batch Print',
                'credit_per_work': 40,
                'trial_credits': 20000,
                'pricing_model': 'trial_500works',
                'auto_activate_trial': True,
                'require_registration': False,
                'max_installations': 1,
                'hardware_based_activation': True,
            },
            'conversion_verifier': {
                'display_name': 'Conversion Verifier',
                'credit_per_work': 0,
                'trial_credits': -1,  # 무료 앱 (BASIC_RULES.md Part 2.1)
                'pricing_model': 'free',
            },
            'korean_filename_normalizer': {
                'display_name': 'Korean Filename Normalizer',
                'credit_per_work': 0,
                'trial_credits': -1,  # 무료 앱 (BASIC_RULES.md Part 2.1)
                'pricing_model': 'free',
            },
            'attribute_reset': {
                'display_name': 'Attribute Reset',
                'credit_per_work': 200,
                'trial_credits': 100000,
                'pricing_model': 'trial_500works',
                'auto_activate_trial': True,
                'require_registration': False,
                'max_installations': 1,
                'hardware_based_activation': True,
            },
            'qrcode_generator': {
                'display_name': 'QR Code Generator',
                'credit_per_work': 0,
                'trial_credits': -1,  # 무료 앱 (BASIC_RULES.md Part 2.1)
                'pricing_model': 'free',
            },
        }

        info = app_info.get(app_name, {
            'display_name': app_name,
            'credit_per_work': 100,
            'trial_credits': 50000,
            'pricing_model': 'trial_500works',
            'auto_activate_trial': True,
            'require_registration': False,
            'max_installations': 1,
            'hardware_based_activation': True,
        })

        # Find latest exe
        exe_path = self._find_latest_exe(app_name)

        return AppConfig(
            name=app_name,
            display_name=info['display_name'],
            exe_path=exe_path,
            port=self.port,
            credit_per_work=info['credit_per_work'],
            trial_credits=info['trial_credits'],
            policy={
                'pricing_model': info.get('pricing_model', 'trial_500works'),
                'credit_per_work': info['credit_per_work'],
                'trial_credits': info['trial_credits'],
                'auto_activate_trial': info.get('auto_activate_trial', False),
                'require_registration': info.get('require_registration', False),
                'max_installations': info.get('max_installations', 1),
                'hardware_based_activation': info.get('hardware_based_activation', False),
            }
        )

    def _find_latest_exe(self, app_name: str) -> Path:
        """Find the latest version exe in candidates directory"""
        pattern = f"{app_name}_v*"
        candidates = list(self.CANDIDATES_DIR.glob(pattern))

        if not candidates:
            logger.warning(f"No candidates found for {app_name}")
            return Path()

        # Sort by version (assuming format: app_name_vX.Y.Z.W)
        def version_key(p):
            try:
                version_str = p.name.split('_v')[1]
                parts = version_str.split('.')
                return tuple(int(x) for x in parts)
            except:
                return (0, 0, 0, 0)

        latest = sorted(candidates, key=version_key)[-1]
        exe_name = f"{app_name}.exe"
        portable_dir = latest / f"{latest.name}_portable"

        if portable_dir.exists():
            return portable_dir / exe_name
        return latest / exe_name

    def launch_app(self, extra_args: List[str] = None) -> bool:
        """
        Launch the app in test mode.

        Args:
            extra_args: Additional command line arguments

        Returns:
            True if launched successfully
        """
        if self.dev_mode:
            # Run from Python source
            # Check for app-specific directory override
            if self.app_name in self.APP_DIR_OVERRIDES:
                app_dir = self.APP_DIR_OVERRIDES[self.app_name]
            else:
                app_dir = self.DEV_APPS_DIR / self.app_name
            py_path = app_dir / "ui_main.py"
            if not py_path.exists():
                logger.error(f"Python source not found: {py_path}")
                return False

            # Use python (not pythonw) to ensure proper output/error handling
            python_exe = "python"
            args = [python_exe, str(py_path), '--test-mode']
            cwd = str(py_path.parent)
            logger.info(f"[TestClient] Dev mode: running {py_path}")
        else:
            # Run from exe
            if not self.config.exe_path.exists():
                logger.error(f"Exe not found: {self.config.exe_path}")
                return False
            args = [str(self.config.exe_path), '--test-mode']
            cwd = None

        if extra_args:
            args.extend(extra_args)

        try:
            # Don't capture stdout/stderr to avoid blocking GUI apps
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
            )
            logger.info(f"[TestClient] Launched {self.config.display_name} (PID: {self.process.pid})")

            # Wait for server to be ready (longer timeout for dev mode)
            if self.dev_mode and self.app_name == "batch_print":
                timeout = 45.0
            else:
                timeout = 15.0 if self.dev_mode else 10.0
            return self._wait_for_server(timeout=timeout)

        except Exception as e:
            logger.error(f"[TestClient] Failed to launch: {e}")
            return False

    def _wait_for_server(self, timeout: float = 10.0) -> bool:
        """Wait for test server to be ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                result = self.call('ping')
                if result == 'pong':
                    logger.info("[TestClient] Server ready")
                    return True
            except:
                pass
            time.sleep(0.2)

        logger.error("[TestClient] Server not ready within timeout")
        return False

    def call(self, command: str, *args, **kwargs) -> Any:
        """
        Call a command on the app.

        Args:
            command: Command name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Command result data

        Raises:
            ConnectionError: If connection fails
            RuntimeError: If command fails
        """
        request = {
            'command': command,
            'args': args,
            'kwargs': kwargs,
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(('127.0.0.1', self.port))

            # Send request
            sock.sendall((json.dumps(request) + '\n').encode('utf-8'))

            # Receive response
            data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break

            sock.close()

            response = json.loads(data.decode('utf-8').strip())

            if response.get('success'):
                return response.get('data')
            else:
                error = response.get('error', 'Unknown error')
                raise RuntimeError(f"Command failed: {error}")

        except socket.error as e:
            raise ConnectionError(f"Connection failed: {e}")

    def terminate_app(self, graceful: bool = True, wait_time: float = 2.0) -> None:
        """
        Terminate the app.

        Args:
            graceful: If True, try graceful shutdown first
            wait_time: Time to wait after termination (for single-instance cleanup)
        """
        if graceful:
            try:
                self.call('shutdown')
                time.sleep(0.5)
            except:
                pass

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except:
                    pass

            # Wait for single-instance cleanup (exe mode)
            if not self.dev_mode and wait_time > 0:
                logger.info(f"[TestClient] Waiting {wait_time}s for single-instance cleanup...")
                time.sleep(wait_time)

            self.process = None
            logger.info("[TestClient] App terminated")

    def is_running(self) -> bool:
        """Check if app is running"""
        if not self.process:
            return False
        return self.process.poll() is None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.terminate_app()


class MultiAppTestClient:
    """
    Client for testing multiple apps simultaneously.
    """

    def __init__(self, app_names: List[str]):
        """
        Initialize multi-app client.

        Args:
            app_names: List of app identifiers
        """
        self.clients = {name: TestClient(name) for name in app_names}

    def launch_all(self) -> bool:
        """Launch all apps"""
        success = True
        for name, client in self.clients.items():
            if not client.launch_app():
                logger.error(f"Failed to launch {name}")
                success = False
        return success

    def terminate_all(self) -> None:
        """Terminate all apps"""
        for client in self.clients.values():
            client.terminate_app()

    def get_client(self, app_name: str) -> TestClient:
        """Get client for specific app"""
        return self.clients.get(app_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate_all()
