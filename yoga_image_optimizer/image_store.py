import os
from pathlib import Path

from gi.repository import Gtk
from gi.repository import GdkPixbuf

from . import helpers
from .image_formats import IMAGES_FORMATS
from .translation import gettext as _
from .translation import format_string


class ImageStore(object):

    # fmt: off
    FIELDS = {
        "input_file":            {"id":  0, "label": "",                 "type": str,              "default": ""},
        "output_file":           {"id":  1, "label": "",                 "type": str,              "default": ""},
        "input_file_display":    {"id":  2, "label": _("Input Image"),   "type": str,              "default": ""},
        "output_file_display":   {"id":  3, "label": _("Output Image"),  "type": str,              "default": ""},
        "input_size":            {"id":  4, "label": "",                 "type": int,              "default": 0},
        "output_size":           {"id":  5, "label": "",                 "type": int,              "default": 0},
        "input_size_display":    {"id":  6, "label": _("Input Size"),    "type": str,              "default": ""},
        "output_size_display":   {"id":  7, "label": _("Output Size"),   "type": str,              "default": ""},
        "input_format":          {"id":  8, "label": _("Input Format"),  "type": str,              "default": ""},
        "output_format":         {"id":  9, "label": "",                 "type": str,              "default": ""},
        "output_format_display": {"id": 10, "label": _("Output Format"), "type": str,              "default": ""},
        "preview":               {"id": 11, "label": "",                 "type": GdkPixbuf.Pixbuf, "default": None},
        "separator":             {"id": 12, "label": "",                 "type": str,              "default": "➡️"},
        "status":                {"id": 13, "label": "",                 "type": int,              "default": 0},
        "status_display":        {"id": 14, "label": _("Status"),        "type": str,              "default": ""},
        "jpeg_quality":          {"id": 15, "label": "",                 "type": int,              "default": 90},
        "webp_quality":          {"id": 16, "label": "",                 "type": int,              "default": 90},
        "png_slow_optimization": {"id": 17, "label": "",                 "type": bool,             "default": False},
    }
    # fmt: on

    STATUS_NONE = 0
    STATUS_PENDING = 1
    STATUS_IN_PROGRESS = 2
    STATUS_DONE = 3

    gtk_list_store = None

    def __init__(self):
        store_fields = sorted(self.FIELDS.values(), key=lambda v: v["id"])
        self.gtk_list_store = Gtk.ListStore(*[f["type"] for f in store_fields])

    @property
    def length(self):
        """The length of the store."""
        return len(self.gtk_list_store)

    def append(self, **kwargs):
        """Appends a row to the image store.

        :param **kwargs: The columns key/value of the row.

        >>> image_store = ImageStore()
        >>> image_store.length
        0
        >>> image_store.append(
        ...     input_file="/tmp/foobar.png",
        ...     output_file="/tmp/foobar.opti.png",
        ... )
        >>> image_store.length
        1
        >>> image_store.append(foo="bar")
        Traceback (most recent call last):
            ...
        KeyError: "Invalid field 'foo'"
        """
        for key in kwargs:
            if key not in self.FIELDS:
                raise KeyError("Invalid field '%s'" % key)

        row = [None] * len(self.FIELDS)

        for key in self.FIELDS:
            field_info = self.FIELDS[key]
            row[field_info["id"]] = field_info["default"]

        iter_ = self.gtk_list_store.append(row)
        self.update(iter_, **kwargs)

    def clear(self):
        """Clears the store.

        >>> image_store = ImageStore()
        >>> image_store.append()
        >>> image_store.length
        1
        >>> image_store.clear()
        >>> image_store.length
        0
        """
        self.gtk_list_store.clear()

    def get(self, index):
        """Gets row data.

        :param int,gtk.TreeIter index: The index of the row.

        :rtype: dict
        :returns: The row data (e.g. ``{"field_name": "value"}``.

        >>> image_store = ImageStore()
        >>> image_store.append()
        >>> image_store.get(0)
        {...}
        >>> image_store.get(1)
        Traceback (most recent call last):
            ...
        IndexError: ...
        """
        row = self.gtk_list_store[index]
        result = {}

        for field_name, field_info in self.FIELDS.items():
            result[field_name] = row[field_info["id"]]

        return result

    def get_all(self):
        """Get all rows of the store.

        :rtype: generator

        >>> image_store = ImageStore()
        >>> image_store.get_all()
        <generator object ImageStore.get_all at ...>
        """
        for i in range(self.length):
            yield self.get(i)

    def remove(self, iter_):
        """Removes a row at given gtk.TreeIter from the store.

        :param gtk.TreeIter index: The iter of the row.
        """
        self.gtk_list_store.remove(iter_)

    def remove_at_index(self, index):
        """Removes a row at given index from the store.

        :param int index: The index of the row.

        >>> image_store = ImageStore()
        >>> image_store.append()
        >>> image_store.length
        1
        >>> image_store.remove_at_index(0)
        >>> image_store.length
        0
        >>> image_store.remove_at_index(0)
        Traceback (most recent call last):
            ...
        IndexError: ...
        """
        try:
            iter_ = self.gtk_list_store.get_iter(index)
        except ValueError as error:
            raise IndexError(error)
        self.remove(iter_)

    def update(self, index, **kwargs):
        """Updates a row.

        :param int,gtk.TreeIter index: The index of the row.
        :param **kwargs: The columns key/value of the row.

        >>> image_store = ImageStore()
        >>> image_store.append(output_file="aaa.png")
        >>> image_store.get(0)["output_file"]
        'aaa.png'
        >>> image_store.update(0, output_file="bbb.png")
        >>> image_store.get(0)["output_file"]
        'bbb.png'
        >>> image_store.update(0, foo="bar")
        Traceback (most recent call last):
            ...
        KeyError: "Invalid field 'foo'"
        >>> image_store.update(1, output_file="ccc.png")
        Traceback (most recent call last):
            ...
        IndexError: ...
        """
        for key in kwargs:
            if key not in self.FIELDS:
                raise KeyError("Invalid field '%s'" % key)

        for key in kwargs:
            self._update_field(index, key, kwargs[key])

        if "input_file" in kwargs:
            path = Path(self.get(index)["input_file"])
            self._update_field(
                index,
                "input_file_display",
                path.name,
            )

        if (
            "output_format" in kwargs
            or "jpeg_quality" in kwargs
            or "webp_quality" in kwargs
            or "png_slow_optimization" in kwargs
        ):
            _FORMATS_EXTS = {
                fid: fmt["exts"][0] for fid, fmt in IMAGES_FORMATS.items()
            }

            output_format = self.get(index)["output_format"]

            if output_format == "jpeg":
                text = "%s (%i %%)" % (
                    IMAGES_FORMATS["jpeg"]["display_name"],
                    self.get(index)["jpeg_quality"],
                )
                self._update_field(index, "output_format_display", text)
            elif output_format == "webp":
                text = "%s (%i %%)" % (
                    IMAGES_FORMATS["webp"]["display_name"],
                    self.get(index)["webp_quality"],
                )
                self._update_field(index, "output_format_display", text)
            elif output_format == "png":
                text = "%s%s" % (
                    IMAGES_FORMATS["png"]["display_name"],
                    (" (%s)" % "slow")
                    if self.get(index)["png_slow_optimization"]
                    else "",
                )
                self._update_field(index, "output_format_display", text)
            else:
                self._update_field(
                    index,
                    "output_format_display",
                    IMAGES_FORMATS[output_format]["display_name"],
                )

            output_file = Path(self.get(index)["output_file"])

            self._update_field(
                index,
                "output_file",
                str(output_file.with_suffix(_FORMATS_EXTS[output_format])),
            )

        if "output_file" in kwargs or "output_format" in kwargs:
            output_file = Path(self.get(index)["output_file"])
            input_file = Path(self.get(index)["input_file"])
            self._update_field(
                index,
                "output_file_display",
                os.path.relpath(
                    output_file,
                    start=input_file.parent,
                ),
            )

        if "input_size" in kwargs:
            self._update_field(
                index,
                "input_size_display",
                helpers.human_readable_file_size(
                    self.get(index)["input_size"]
                ),
            )

        if "output_size" in kwargs:
            input_size = self.get(index)["input_size"]
            output_size = self.get(index)["output_size"]

            output_size_display = ""

            if output_size > 0:
                size_delta = -(100 - output_size / input_size * 100)
                output_size_display = "%s (%s%s %%)" % (
                    helpers.human_readable_file_size(output_size),
                    "+" if output_size > input_size else "",
                    format_string("%.1f", size_delta),
                )

            self._update_field(
                index,
                "output_size_display",
                output_size_display,
            )

        if "status" in kwargs:
            _STATUS = {
                0: "",
                1: "⏸️ %s" % _("Pending"),
                2: "🔄️ %s" % _("In progress"),
                3: "✅️ %s" % _("Done"),
            }
            self._update_field(
                index,
                "status_display",
                _STATUS[self.get(index)["status"]],
            )

    def _update_field(self, index, field_name, value):
        row = self.gtk_list_store[index]
        row[self.FIELDS[field_name]["id"]] = value
