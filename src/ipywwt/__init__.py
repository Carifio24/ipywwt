import importlib.metadata
import pathlib
import os
import subprocess
import threading
import time
import socket

import anywidget
import traitlets
from traitlets import observe

from .layers import TableLayer
from .core import BaseWWTWidget

try:
    __version__ = importlib.metadata.version("ipywwt")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

STATIC = pathlib.Path(__file__).parent / "static"
RESEARCH_APP = pathlib.Path(__file__).parent / "web_static" / "research"


class WWTWidget(anywidget.AnyWidget, BaseWWTWidget):
    _esm = STATIC / "widget.js"
    _css = STATIC / "widget.css"

    _commands = traitlets.List(default_value=[]).tag(sync=True)
    _dirty = traitlets.Bool(default_value=False).tag(sync=True)
    _wwt_ready = traitlets.Bool(default_value=False).tag(sync=True)

    server_url = traitlets.Unicode(default_value="").tag(sync=True)

    def __init__(self, hide_all_chrome=True, port=8899, *args, **kwargs):
        super().__init__(hide_all_chrome=hide_all_chrome, *args, **kwargs)

        # Define path to research app
        self._research_app_path = RESEARCH_APP

        # Start server
        self._port = port
        self.server_url = f"http://localhost:{self._port}"

        # Check if server is already running
        if not self._is_server_running():
            self._start_server()

    def _is_server_running(self):
        """Check if a process is already listening on the given port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("localhost", self._port)) == 0

    def _start_server(self):
        """Start a simple HTTP server to serve the research app."""
        if not self._research_app_path.exists():
            raise FileNotFoundError(
                f"WWT research app not found at {self._research_app_path}"
            )

        def run_server():
            os.chdir(self._research_app_path)
            subprocess.run(["python", "-m", "http.server", str(self._port)], check=True)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait a bit to ensure the server starts
        time.sleep(1)

    def _actually_send_msg(self, payload):
        """Sends a command to the JavaScript widget."""
        self._commands = self._commands + [payload]

    @observe("_wwt_ready")
    def _on_wwt_ready(self, change):
        if change["new"]:
            self._on_app_status_change(True)

    @observe("_dirty")
    def _on_dirty(self, change):
        if self._dirty:
            self._commands = []  # Clear the command queue
            self._dirty = False
