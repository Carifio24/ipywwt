import importlib.metadata
import pathlib

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


class WWTWidget(anywidget.AnyWidget, BaseWWTWidget):
    _esm = STATIC / "widget.js"
    _css = STATIC / "widget.css"

    _commands = traitlets.List(default_value=[]).tag(sync=True)
    _dirty = traitlets.Bool(default_value=False).tag(sync=True)
    _wwt_ready = traitlets.Bool(default_value=False).tag(sync=True)

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
