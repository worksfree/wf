# -*- coding: utf-8 -*-
"""
WF-ACT Test Server
==================
IPC server that apps import to enable test mode.

Usage in app (ui_main.py):
    from wf_act.core import TestServer, TestMode

    if '--test-mode' in sys.argv:
        test_server = TestServer(app_name='bom_exporter')
        test_server.register_handler('get_credits', lambda: credit_manager.get_credits())
        test_server.register_handler('click_button', lambda name: click_button(name))
        test_server.start()
"""

import json
import threading
import socket
import logging
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class TestMode(Enum):
    """Test mode types"""
    DISABLED = auto()      # Normal operation
    CERTIFICATION = auto()  # Full certification mode
    DEBUG = auto()         # Debug mode with verbose logging


@dataclass
class CommandResult:
    """Result of a command execution"""
    success: bool
    data: Any = None
    error: str = ""

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error
        }


class TestServer:
    """
    IPC server for test mode communication.
    Uses TCP socket for reliable cross-process communication.
    """

    BASE_PORT = 19800  # Base port for test servers

    def __init__(self, app_name: str, port: Optional[int] = None):
        """
        Initialize test server.

        Args:
            app_name: Application identifier (e.g., 'bom_exporter')
            port: Optional specific port (auto-assigned if None)
        """
        self.app_name = app_name
        self.port = port or self._get_port_for_app(app_name)
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.mode = TestMode.CERTIFICATION

        # Register built-in handlers
        self._register_builtin_handlers()

        logger.info(f"[TestServer] Initialized for {app_name} on port {self.port}")

    def _get_port_for_app(self, app_name: str) -> int:
        """Get deterministic port for app name"""
        app_ports = {
            'bom_exporter': 0,
            'dwg_classifier': 1,
            'dwg_batch_print': 2,
            'conversion_verifier': 3,
            'korean_filename_normalizer': 4,
            'attribute_reset': 5,
            'qrcode_generator': 6,
        }
        offset = app_ports.get(app_name, hash(app_name) % 100)
        return self.BASE_PORT + offset

    def _register_builtin_handlers(self):
        """Register built-in command handlers"""
        self.handlers['ping'] = lambda: 'pong'
        self.handlers['get_app_name'] = lambda: self.app_name
        self.handlers['get_mode'] = lambda: self.mode.name
        self.handlers['shutdown'] = self._handle_shutdown

    def _handle_shutdown(self) -> str:
        """Handle shutdown command"""
        threading.Thread(target=self._delayed_stop, daemon=True).start()
        return 'shutting_down'

    def _delayed_stop(self):
        """Stop server after brief delay"""
        import time
        time.sleep(0.1)
        self.stop()

    def register_handler(self, command: str, handler: Callable) -> None:
        """
        Register a command handler.

        Args:
            command: Command name (e.g., 'get_credits', 'click_button')
            handler: Callable that handles the command
        """
        self.handlers[command] = handler
        logger.debug(f"[TestServer] Registered handler: {command}")

    def register_handlers(self, handlers: Dict[str, Callable]) -> None:
        """Register multiple handlers at once"""
        for cmd, handler in handlers.items():
            self.register_handler(cmd, handler)

    def start(self) -> bool:
        """Start the test server in a background thread"""
        if self.running:
            logger.warning("[TestServer] Already running")
            return False

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Allow periodic check for stop

            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()

            logger.info(f"[TestServer] Started on port {self.port}")
            return True

        except Exception as e:
            logger.error(f"[TestServer] Failed to start: {e}")
            return False

    def stop(self) -> None:
        """Stop the test server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logger.info("[TestServer] Stopped")

    def _server_loop(self) -> None:
        """Main server loop"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"[TestServer] Accept error: {e}")

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a client connection"""
        try:
            client_socket.settimeout(30.0)
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break

            if data:
                request = json.loads(data.decode('utf-8').strip())
                response = self._process_request(request)
                client_socket.sendall((json.dumps(response) + '\n').encode('utf-8'))

        except Exception as e:
            logger.error(f"[TestServer] Client error: {e}")
            try:
                error_response = CommandResult(False, error=str(e)).to_dict()
                client_socket.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass

    def _process_request(self, request: dict) -> dict:
        """Process a command request"""
        command = request.get('command', '')
        args = request.get('args', [])
        kwargs = request.get('kwargs', {})

        logger.debug(f"[TestServer] Processing: {command}")

        handler = self.handlers.get(command)
        if not handler:
            return CommandResult(False, error=f"Unknown command: {command}").to_dict()

        try:
            result = handler(*args, **kwargs)
            return CommandResult(True, data=result).to_dict()
        except Exception as e:
            logger.error(f"[TestServer] Handler error for {command}: {e}")
            return CommandResult(False, error=str(e)).to_dict()


class TestServerMixin:
    """
    Mixin class for easy integration with Tkinter apps.

    Usage:
        class MyApp(tk.Tk, TestServerMixin):
            def __init__(self):
                super().__init__()
                if '--test-mode' in sys.argv:
                    self.init_test_server('my_app')
    """

    test_server: Optional[TestServer] = None

    def init_test_server(self, app_name: str) -> None:
        """Initialize test server with common handlers"""
        self.test_server = TestServer(app_name)

        # Subclasses should override this to register app-specific handlers
        self._register_test_handlers()

        self.test_server.start()

    def _register_test_handlers(self) -> None:
        """Override this to register app-specific handlers"""
        pass

    def shutdown_test_server(self) -> None:
        """Shutdown test server"""
        if self.test_server:
            self.test_server.stop()
