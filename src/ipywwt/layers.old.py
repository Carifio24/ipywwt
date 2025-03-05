from traitlets import HasTraits, Unicode, Float, observe, Any
from uuid import uuid4
from io import StringIO
import re

from base64 import b64encode


def csv_table_win_newline(table):
    """
    Helper function to get Astropy tables as ASCII CSV with Windows line
    endings
    """
    s = StringIO()
    table.write(s, format="ascii.basic", delimiter=",", comment=False)
    s.seek(0)
    # Replace single \r or \n characters with \r\n
    return re.sub(r"(?<![\r\n])(\r|\n)(?![\r\n])", "\r\n", s.read())


def parse_table(tab):
    # TODO: We need to make sure that the table has ra/dec columns since
    #  WWT absolutely needs that upon creation.

    csv = csv_table_win_newline(tab)

    return b64encode(csv.encode("ascii", errors="replace")).decode("ascii")


class TableLayer(HasTraits):
    coord_type = Unicode(
        "spherical",
        help="Whether to give the coordinates "
        "in spherical or rectangular coordinates",
    ).tag(wwt="coordinatesType")

    lon_att = Unicode(help="The column to use for the longitude (`str`)").tag(
        wwt="lngColumn"
    )
    lon_unit = Any(
        help="The units to use for longitude (:class:`~astropy.units.Unit`)"
    ).tag(wwt="raUnits")
    lat_att = Unicode(help="The column to use for the latitude (`str`)").tag(
        wwt="latColumn"
    )

    size_att = Unicode(
        help="The name of the column in the table that contains the size data."
    ).tag(wwt=None)

    size_scale = Float(10, help="The scale factor applied to points in the layer.").tag(
        wwt="scaleFactor"
    )
    color = Unicode("white", help="The color of the points in the layer.").tag(
        wwt="color"
    )
    opacity = Float(
        1.0, help="The opacity of the points in the layer. Must be between 0 and 1."
    ).tag(wwt="opacity")
    marker_type = Unicode(
        "gaussian", help="The type of marker to use for the points in the layer."
    ).tag(wwt="plotType")
    marker_scale = Unicode(
        "screen", help="Whether the scale is defined in world or pixel coordinates."
    ).tag(wwt="markerScale")

    def __init__(self, parent, frame, name, data, **kwargs):
        self._parent = parent
        self._id = uuid4().hex
        self._frame = frame.capitalize()
        self._name = name
        self._data = data

        self._initialize_layer()

        # Force defaults
        self._on_trait_changed({"name": "coord_type", "new": self.coord_type})
        self._on_trait_changed({"name": "lon_unit", "new": self.lon_unit})
        self._on_trait_changed({"name": "size_scale", "new": self.size_scale})
        self._on_trait_changed({"name": "color", "new": self.color})
        self._on_trait_changed({"name": "opacity", "new": self.opacity})
        self._on_trait_changed({"name": "marker_type", "new": self.marker_type})
        self._on_trait_changed({"name": "marker_scale", "new": self.marker_scale})
        self._on_trait_changed({"name": "size_att", "new": self.size_att})

        self.observe(self._on_trait_changed, type="change")

        super().__init__(**kwargs)

    def _initialize_layer(self):
        self._parent._send_command(
            "add_table_layer",
            id=self.id,
            frame=self.frame,
            name=self.name,
            data=self.data64b,
        )

    @property
    def id(self):
        return self._id

    @property
    def frame(self):
        return self._frame

    @property
    def name(self):
        return self._name

    @property
    def data64b(self):
        return parse_table(self._data)

    def _on_trait_changed(self, changed):
        wwt_name = self.trait_metadata(changed["name"], "wwt")
        if wwt_name is not None:
            self._parent._send_command(
                "table_layer_set",
                id=self.id,
                setting=wwt_name,
                value=changed["new"],
            )
