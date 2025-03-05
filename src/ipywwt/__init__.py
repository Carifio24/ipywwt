import multiprocessing
from threading import Timer
import time
from dataclasses import asdict
from pathlib import Path

import astropy.units as u
from astropy.time import Time
from anywidget import AnyWidget
from traitlets import Unicode, Float, observe, default
import logging
import numpy as np
from astropy.coordinates import SkyCoord
import ipywidgets as widgets

from .messages import *
from .imagery import get_imagery_layers
from .layers import LayerManager

bundler_output_dir = Path(__file__).parent / "static"

APP_LIVELINESS_DEADLINE = 10 
DEFAULT_SURVEYS_URL = "https://worldwidetelescope.github.io/pywwt/surveys.xml"
R2D = 180 / np.pi
R2H = 12 / np.pi

logger = logging.getLogger("pywwt")

from IPython.display import Javascript

#  https://stackoverflow.com/a/48741004
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            print("In run")
            Javascript("console.log('In run')");
            self.function(*self.args, **self.kwargs)


class WWTWidget(AnyWidget):
    _esm = bundler_output_dir / "main.js"
    _css = bundler_output_dir / "style.css"

    background = Unicode(
        "Hydrogen Alpha Full Sky Map",
        help="The layer to show in the background (`str`)",
    )

    foreground = Unicode(
        "Digitized Sky Survey (Color)",
        help="The layer to show in the foreground (`str`)",
    )

    foreground_opacity = Float(
        0.8, help="The opacity of the foreground layer " "(`float`)"
    )
    
    # View state that the frontend sends to us:
    _raRad = 0.0
    _decRad = 0.0
    _fovDeg = 60.0
    _rollDeg = 0.0
    _engineTime = Time("2017-03-09T12:30:00", format="isot")
    _systemTime = Time("2017-03-09T12:30:00", format="isot")
    _timeRate = 1.0

    _appAlive = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_queue = []
        self._on_ready = []
        self.on_msg(self._on_app_message_received)

        self._callbacks = {}
        self._futures = []

        self._available_layers = get_imagery_layers(DEFAULT_SURVEYS_URL)
        self.load_image_collection()

        self.layers = LayerManager(parent=self)
        self.current_mode = "sky"
        
        self._last_pong_timestamp = 0
        self._timer = RepeatTimer(1.0, self._check_ready)
        self._timer.start()
        print("HERE")

    def _send_msg(self, **kwargs):
        """
        Translate PyWWT-style raw dict messages to structured message classes.
        """
        msg_type = kwargs.get("event", None) or kwargs.get("type", None)
        msg_cls = msg_ref[msg_type]
        self.send(msg_cls(**kwargs))

    def send(self, msg: RemoteAPIMessage, buffers=None):
        if self._appAlive or getattr(msg, "type", None) == "wwt_ping_pong":
            super().send(asdict(msg), buffers)
        else:
            self.message_queue.append({'msg':msg, 'buffers':buffers})

    def _check_ready(self):
        print("Is it ready yet?")
        self._send_msg(
            type="wwt_ping_pong",
            threadId=str(time.time())
        )

        print(time.time(), self._last_pong_timestamp)
        alive = (time.time() - self._last_pong_timestamp) < APP_LIVELINESS_DEADLINE

        print(f"Alive: {alive}")
        self._on_app_status_change(alive=alive)
        print("Returning from _check_ready")

    def load_image_collection(self, url=DEFAULT_SURVEYS_URL):
        self.send(LoadImageCollectionMessage(url))

    def _on_app_status_change(self, alive=None):
        print(alive)
        if alive:
            print("It's alive!")
        if alive is not None:
            self._appAlive = alive

            if alive:
                while self.message_queue:
                    message = self.message_queue.pop(0)
                    self.send(message['msg'], message['buffers'])

                while self._on_ready:
                    callback = self._on_ready.pop(0)
                    callback()
                self._timer.join()
                
    def on_ready(self, callback):
        """
        Set a callback function that will be executed when the widget receives
        the "wwt_ready" message indicating the WWT application is ready to recieve
        messages.
        
        Useful for defining intialization actions that require the WWT application
        """
        self._on_ready.append(callback)

    def ensure_ready(self, callback):
        if self._appAlive:
            callback()
        else:
            self.on_ready(callback)
    
    @observe("foreground")
    def _on_foreground_change(self, changed):
        self.send(SetForegroundByNameMessage(name=changed["new"]))

        self.send(
            SetForegroundByOpacityMessage(
                value=self.foreground_opacity * 100,
            )
        )

    @observe("background")
    def set_background_image(self, changed):
        self.send(SetBackgroundByNameMessage(name=changed["new"]))

        self.send(
            SetForegroundByOpacityMessage(
                value=self.foreground_opacity * 100,
            )
        )

    def center_on_coordinates(self, coord, fov=60 * u.deg, roll=None, instant=True):
        """
        Navigate the camera to the specified position, asynchronously.

        Parameters
        ----------
        coord : `~astropy.units.Quantity`
            The set of coordinates the view should center on.
        fov : `~astropy.units.Quantity`, optional
            The desired field of view.
        roll: `~astropy.units.Quantity`, optional
            The desired roll angle of the camera. If not specified, the
            roll angle is not changed.
        instant : `bool`, optional
            Whether the view changes instantly or smoothly scrolls to the
            desired location.
        """
        coord_icrs = coord.icrs

        msg = CenterOnCoordinatesMessage(
            ra=coord_icrs.ra.deg,
            dec=coord_icrs.dec.deg,
            fov=fov.to(u.deg).value,
            instant=instant,
        )

        self.send(msg)

    def get_center(self):
        """
        Return the view's current right ascension and declination in degrees.
        """
        return SkyCoord(
            self._raRad * R2H,
            self._decRad * R2D,
            unit=(u.hourangle, u.deg),
        )

    def get_fov(self):
        return self._fovDeg * u.deg

    def get_roll(self):
        return self._rollDeg * u.deg

    def _on_app_message_received(self, instance, payload, buffers=None):
        """
        Call this function when a message is received from the research app.
        This will generally happen in some kind of asynchronous event handler,
        so there is no guarantee that exceptions raised here will be exposed to
        the user.
        """

        ptype = payload.get("type") or payload.get("event")
        # some events don't have type but do have:
        # pevent = payload.get('event')

        updated_fields = []

        if ptype == "wwt_ping_pong":
            try:
                ts = float(payload['threadId'])
            except Exception:
                print("invalid timestamp in pingpong response")
            else:
                self._last_pong_timestamp = ts

        if ptype == "wwt_view_state":
            try:
                self._raRad = float(payload["raRad"])
                self._decRad = float(payload["decRad"])
                self._fovDeg = float(payload["fovDeg"])
                self._rollDeg = float(payload["rollDeg"])
                self._engineTime = Time(payload["engineClockISOT"], format="isot")
                self._systemTime = Time(payload["systemClockISOT"], format="isot")
                self._timeRate = float(payload["engineClockRateFactor"])
            except ValueError:
                pass  # report a warning somehow?
        elif ptype == "wwt_application_state":
            hipscat = payload.get("hipsCatalogNames")

            if hipscat is not None:
                self._available_hips_catalog_names = hipscat

        elif ptype == "wwt_selection_state":
            most_recent = payload.get("mostRecentSource")
            sources = payload.get("selectedSources")

            if most_recent is not None:
                self._most_recent_source = most_recent
                updated_fields.append("most_recent_source")

            if sources is not None:
                self._selected_sources = sources
                updated_fields.append("selected_sources")

        # Any relevant async future to resolve?

        tid = payload.get("threadId")

        if tid is not None:
            try:
                fut = self._futures.pop(tid)
            except KeyError:
                pass
            else:
                fut.set_result(payload)

        # Any client-side callbacks to execute?

        callback = self._callbacks.get(ptype)

        if callback:
            try:
                callback(self, updated_fields)
            except:  # noqa: E722
                logger.exception("unhandled Python exception during a callback")

    def _set_message_type_callback(self, ptype, callback):
        """
        Set a callback function that will be executed when the widget receives
        a message with the given type.

        Parameters
        ----------
        ptype: str
            The string that identifies the message type
        callback: `BaseWWTWidget`
            A callable object which takes two arguments: the WWT widget
            instance, and a list of updated properties.
        """
        self._callbacks[ptype] = callback

    def set_selection_change_callback(self, callback):
        """
        Set a callback function that will be executed when the widget receives
        a selection change message.

        Parameters
        ----------
        callback:
            A callable object which takes two arguments: the WWT widget
            instance, and a list of updated properties.
        """
        self._set_message_type_callback("wwt_selection_state", callback)

    _most_recent_source = None

    @property
    def most_recent_source(self):
        """
        The most recent source selected in the viewer, represented as a dictionary.
        The items of this dictionary match the entries of the Source object detailed
        `here <https://docs.worldwidetelescope.org/webgl-reference/latest/apiref/research-app-messages/interfaces/selections.source.html>`_.
        """
        return self._most_recent_source

    _selected_sources = []

    @property
    def selected_sources(self):
        """
        A list of the selected sources, with each source represented as a dictionary.
        The items of these dictionaries match the entries of the Source object detailed
        `here <https://docs.worldwidetelescope.org/webgl-reference/latest/apiref/research-app-messages/interfaces/selections.source.html>`_.
        """
        return self._selected_sources

    def reset_view(self):
        """
        Reset the current view mode's coordinates and field of view to
        their original states.
        """
        if self.current_mode == "sky":
            self.center_on_coordinates(
                SkyCoord(0.0, 0.0, unit=u.deg), fov=60 * u.deg, instant=False
            )
        if self.current_mode == "planet":
            self.center_on_coordinates(
                SkyCoord(35.55, 11.43, unit=u.deg), fov=40 * u.deg, instant=False
            )
        if self.current_mode == "solar system":
            self.center_on_coordinates(
                SkyCoord(0.0, 0.0, unit=u.deg), fov=50 * u.deg, instant=False
            )
        if self.current_mode == "milky way":
            self.center_on_coordinates(
                SkyCoord(114.85, -29.52, unit=u.deg), fov=6e9 * u.deg, instant=False
            )
        if self.current_mode == "universe":
            self.center_on_coordinates(
                SkyCoord(16.67, 37.72, unit=u.deg), fov=1e14 * u.deg, instant=False
            )
        if self.current_mode == "panorama":
            pass

    @default("layout")
    def _default_layout(self):
        return widgets.Layout(height="400px", align_self="stretch")
