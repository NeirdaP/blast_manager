import traceback

from qtpy import QtGui, QtWidgets, QtCore
from .. import icons
from .. controller import base_controller
from .colors import PRIMARY_LIGHT_COLOR

THREE_DOTS_ICON = icons.get_icon("three_dots.png")


class CtrlWidget(QtWidgets.QWidget):
    """
    This widget can create a variety of control
    widget on itself (or, sometimes another widget).

    See _add_* methods
    """
    _LABEL_W = 100
    _CTRL_W = 250

    def __init__(self, parent):
        super(CtrlWidget, self).__init__(parent)

    @staticmethod
    def add_buttons(parent, *labels):
        bl = []
        lo = QtWidgets.QHBoxLayout()
        for label in labels:
            if label is None:
                lo.addStretch()
                continue
            b = QtWidgets.QPushButton(label, parent)
            lo.addWidget(b)
            bl.append(b)
        parent.layout().addLayout(lo)
        return bl

    def add_group(self, name, in_layout=None):
        group = QtWidgets.QGroupBox(name, self)
        if in_layout is None:
            in_layout = self.layout()
        in_layout.addWidget(group)
        lo = QtWidgets.QVBoxLayout()
        group.setLayout(lo)
        return group

    def make_field_lb(self, label, parent):
        lb = QtWidgets.QLabel(label, parent)
        lb.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignRight)
        lb.setMinimumWidth(self._LABEL_W)
        return lb

    def add_le(self, parent, label, value=""):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        le = QtWidgets.QLineEdit(value, parent)
        layout.addWidget(le)
        parent.layout().addLayout(layout)
        return le

    @staticmethod
    def add_tools(parent, layout, *tools):
        if not tools:
            return None

        tool_butt = QtWidgets.QToolButton(parent)
        tool_butt.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        tool_butt.setIcon(THREE_DOTS_ICON)

        tool_butt.setStyleSheet(
            (
                "* {{ font-size: 10pt }}"
                "QToolButton {{ border-radius: 5px; width: 18px; height: 18px; }}"
                "QToolButton:hover {{ background-color: {};  }}"
                "QToolButton::menu-indicator {{ border: none; }}"
            ).format(PRIMARY_LIGHT_COLOR)
        )

        layout.addWidget(tool_butt)
        tool_butt.actions = {}

        for tool in tools:
            if tool is None:
                a = QtWidgets.QAction(tool_butt)
                a.setSeparator(True)
                tool_butt.addAction(a)
                continue
            a = QtWidgets.QAction(tool, tool_butt)
            tool_butt.addAction(a)
            tool_butt.actions[tool] = a

        return tool_butt

    def add_combo(self, parent, label, *tools):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        cb = QtWidgets.QComboBox(parent)
        cb.setMinimumWidth(self._CTRL_W)
        layout.addWidget(cb)
        tool_butt = self.add_tools(parent, layout, *tools)
        layout.addStretch(10)
        parent.layout().addLayout(layout)
        if tool_butt:
            return cb, tool_butt
        return cb

    def add_check(self, parent, label):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        cb = QtWidgets.QCheckBox("", parent)
        layout.addWidget(cb)
        layout.addStretch(10)
        parent.layout().addLayout(layout)
        return cb

    def add_combo_check(self, parent, label, check_label):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        cb = QtWidgets.QComboBox(parent)
        cb.setMinimumWidth(self._CTRL_W)
        layout.addWidget(cb)
        check = QtWidgets.QCheckBox(check_label, parent)
        layout.addWidget(check)
        layout.addStretch(10)
        parent.layout().addLayout(layout)
        return cb, check

    def add_int_slider(self, parent, label, min_value, max_value):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        le = QtWidgets.QLineEdit(str(min_value), parent)
        le.setValidator(QtGui.QIntValidator(min_value, max_value, parent))
        le.setMinimumWidth(self._CTRL_W)
        layout.addWidget(le)
        sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, parent)
        sl.setMinimum(min_value)
        sl.setMaximum(max_value)
        sl.wheelEvent = lambda e: None  # disable wheel event
        sl.valueChanged.connect(lambda v: (le.setText(str(v)),
                                           le.emit(QtCore.SIGNAL("textEdited(const QString&)"),
                                                   str(v))
                                           )
                                )
        layout.addWidget(sl)
        parent.layout().addLayout(layout)
        return le, sl

    def add_int(self, parent, label, *tools):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        le = QtWidgets.QLineEdit(parent)
        le.setValidator(QtGui.QIntValidator(parent))
        le.setMinimumWidth(self._CTRL_W)
        layout.addWidget(le)
        tool_butt = self.add_tools(parent, layout, *tools)
        layout.addStretch(10)
        parent.layout().addLayout(layout)
        if tool_butt:
            return le, tool_butt
        return le

    def add_bool(self, parent, label, *tools):
        layout = QtWidgets.QHBoxLayout()
        lb = self.make_field_lb(label, parent)
        layout.addWidget(lb)
        cb = QtWidgets.QCheckBox(parent)
        cb.setMinimumWidth(self._CTRL_W)
        layout.addWidget(cb)
        tool_butt = self.add_tools(parent, layout, *tools)
        layout.addStretch(10)
        parent.layout().addLayout(layout)
        if tool_butt:
            return cb, tool_butt
        return cb

    def add_listbox(self, parent):
        layout = QtWidgets.QHBoxLayout()
        lb = QtWidgets.QListWidget(parent)
        lb.setFont(QtGui.QFont("Courier", 9))
        lb.setMinimumHeight(300)
        lb.setMinimumWidth(self._LABEL_W + parent.layout().spacing() + self._CTRL_W)
        layout.addWidget(lb)
        parent.layout().addLayout(layout)
        return lb


class PlayBlastHUDParams(object):

    def __init__(self):
        super(PlayBlastHUDParams, self).__init__()
        self.parent = None
        self.group = None
        self.hud_size = None
        self.font_size = None
        self.hud_background = None
        self.hud_foreground = None

        self.hud_size_values = (
            "Small",
            "Large",
        )

        self.font_size_values = (
            "Small",
            "Large",
        )

        self.hud_background_values = (
            ("None", None),
            ("Red", (1.0, 0.0, 0.0)),
            ("Green", (0.0, 1.0, 0.0)),
            ("Blue", (0.0, 0.0, 1.0)),
            ("Dark Red", (0.5, 0.0, 0.0)),
            ("Dark Green", (0.0, 0.5, 0.0)),
            ("Dark Blue", (0.0, 0.0, 0.5)),
            ("Black", (0.0, 0.0, 0.0)),
            ("Dark Grey", (0.4, 0.4, 0.4)),
            ("Light Grey", (0.6, 0.6, 0.6)),
            ("White", (1.0, 1.0, 1.0)),
        )

        self.hud_foreground_values = (
            ("Red", (1.0, 0.0, 0.0)),
            ("Green", (0.0, 1.0, 0.0)),
            ("Blue", (0.0, 0.0, 1.0)),
            ("Dark Red", (0.5, 0.0, 0.0)),
            ("Dark Green", (0.0, 0.5, 0.0)),
            ("Dark Blue", (0.0, 0.0, 0.5)),
            ("Black", (0.0, 0.0, 0.0)),
            ("Dark Grey", (0.4, 0.4, 0.4)),
            ("Light Grey", (0.6, 0.6, 0.6)),
            ("White", (1.0, 1.0, 1.0)),
        )

        self.default_hud_size = 0
        self.default_text_size = 1
        self.default_bg_color = 0
        self.default_fg_color = 8

    def add_to_ctrl_widget(self, parent):
        self.parent = parent
        self.group = parent.add_group("HUD")
        self.hud_size = parent.add_combo(self.group, "HUD Size")
        self.font_size = parent.add_combo(self.group, "Text Size")
        self.hud_background = parent.add_combo(self.group, "Text Background")
        self.hud_foreground = parent.add_combo(self.group, "Text Color")

    def setup_and_connect(self):
        if self.parent:
            self.hud_size.addItems(self.hud_size_values)
            self.font_size.addItems(self.font_size_values)
            self.hud_background.addItems([key for key, value in self.hud_background_values])
            self.hud_foreground.addItems([key for key, value in self.hud_foreground_values])

            self.hud_background.currentIndexChanged.connect(self.on_background_changed)
            self.hud_foreground.currentIndexChanged.connect(self.on_foreground_changed)

    def on_background_changed(self, index):
        self.hud_background.setStyleSheet(
            "color: {col};".format(
                col=QtGui.QColor(*[i * 255 for i in self.hud_background_values[index][1]]).name()
            )
        )

    def on_foreground_changed(self, index):
        self.hud_foreground.setStyleSheet(
            "color: {col};".format(
                col=QtGui.QColor(*[i * 255 for i in self.hud_foreground_values[index][1]]).name()
            )
        )

    def set_defaults(self):
        self.hud_size.setCurrentIndex(self.default_hud_size)
        self.font_size.setCurrentIndex(self.default_text_size)
        self.hud_background.setCurrentIndex(self.default_bg_color)
        self.hud_foreground.setCurrentIndex(self.default_fg_color)

    def get_params(self):
        return {
            "blockSize": self.hud_size.currentText().lower(),
            "labelFontSize": self.font_size.currentText().lower(),
            "text_color": self.hud_foreground_values[self.hud_foreground.currentIndex()][1],
            "text_background": self.hud_background_values[self.hud_background.currentIndex()][1],
        }


class PlayBlastParams(CtrlWidget):
    class ParamError(Exception):
        def __init__(self, param_name):
            super(PlayBlastParams.ParamError, self).__init__(
                f"The value for the {param_name} parameter is not valid."
            )

    _LABEL_W = 100
    _CTRL_W = 100

    def __init__(self, parent):
        super(PlayBlastParams, self).__init__(parent)
        self.playblast_panel = parent
        self.scale_options = (
            ("Full", 1.0),
            ("50%", 0.5),
            ("33%", 1 / 3.0),
            ("25%", 0.25),
        )

        self.bg_color_options = self.playblast_panel.controller.get_bg_color_options()
        self.display_configs = self.playblast_panel.controller.get_display_configs()
        self.hud_options = PlayBlastHUDParams()
        self.render_options = [render_option_type()
                               for render_option_type in self.playblast_panel.controller.ALL_RENDER_OPTION_TYPES]

        self.default_scale_config_index = 0
        self.get_default_bg_color = self.playblast_panel.controller.get_default_bg_color()
        self.default_display_config_index = 1

        self._build_controls()
        self._setup_and_connect()
        self.set_defaults()

    def _build_controls(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        group = self.add_group("Video")
        # Commenting use_sequencer for now, and see if animators notice, else we can remove it
        # self.use_sequencer = self.add_bool(group, "Use Sequencer")

        self.camera = self.add_combo(group, "Camera")
        self.sound = self.add_combo(group, "Sound")

        group = self.add_group("Range")
        self.start, self.range_tools = self.add_int(
            group, "Start Frame",
            "Load Playback Range", "Load Global Range", "Load Montage Range"
        )
        self.end = self.add_int(group, "End Frame")

        group = self.add_group("Size")
        self.width, self.size_tools = self.add_int(
            group, "Width",
            "Load Render Settings"
        )
        self.height = self.add_int(group, "Height")
        self.scale_combo = self.add_combo(group, "Scale")

        group = self.add_group("Display")
        colors = [k for k in self.bg_color_options.keys()]
        colors.sort()
        self.bg_color, self.bg_color_tools = self.add_int(
            group, "BG Color", *colors
        )
        self.display_combo = self.add_combo(group, "Config")

        for render_option in self.render_options:
            render_option.build_controls(self, group)

        self.display_grid = self.add_bool(group, "Display grid")

        self.hud_options.add_to_ctrl_widget(self)

        reset_butt, = self.add_buttons(self, "Reset Options")
        reset_butt.clicked.connect(self.set_defaults)

        self.layout().addStretch(10)

    def _use_sequencer_changed(self):
        enabled = not self.use_sequencer.isChecked()
        self.camera.setEnabled(enabled)
        self.sound.setEnabled(enabled)

    def _setup_and_connect(self):
        # self.use_sequencer.stateChanged.connect(self._use_sequencer_changed)

        self.range_tools.actions["Load Global Range"].triggered.connect(self.on_set_range_from_anim)
        self.range_tools.actions["Load Playback Range"].triggered.connect(self.on_set_range_from_playback)
        self.range_tools.actions["Load Montage Range"].triggered.connect(self.on_set_range_from_montage_range)
        self.size_tools.actions["Load Render Settings"].triggered.connect(self.on_set_range_from_render_setting)

        self.scale_combo.addItems([n for n, v in self.scale_options])
        self.bg_color.setEnabled(False)
        for n, v in self.bg_color_options.items():
            self.bg_color_tools.actions[n].triggered.connect(lambda b=True, col=n: self.on_set_bg_color(col))

        self.camera.addItems(self.playblast_panel.controller.get_available_cameras())
        self.sound.addItems(["*", ""] + self.playblast_panel.controller.get_available_audios())

        self.display_combo.addItems(list(self.display_configs.keys()))

        self.hud_options.setup_and_connect()

    def set_defaults(self):
        self.set_default_range()
        self.set_default_size()
        self.scale_combo.setCurrentIndex(self.default_scale_config_index)
        self.set_default_bg_color()
        self.display_combo.setCurrentIndex(self.default_display_config_index)
        default_camera = self.playblast_panel.controller.get_default_camera()
        for i in range(self.camera.count()):
            if self.camera.itemText(i) == default_camera:
                self.camera.setCurrentIndex(i)
                break
        self.sound.setCurrentText(self.playblast_panel.controller.get_current_audio())
        for render_option in self.render_options:
            render_option.set_default()
        self.hud_options.set_defaults()

    def set_default_range(self):
        if not self.on_set_range_from_montage_range():
            self.set_range(1, 100)

    def set_default_size(self):
        if not self.on_set_range_from_render_setting():
            self.set_size(320, 240)

    def set_default_bg_color(self):
        self.on_set_bg_color(self.get_default_bg_color)

    def on_set_range_from_anim(self):
        """
        Tries to set the start and end params to maya's animation
        range.

        Returns False on fail.
        """
        try:
            s, e = self.playblast_panel.controller.get_global_range()
        except base_controller.PlayblastError:
            traceback.print_exc()
            return False
        self.set_range(s, e)
        return True

    def on_set_range_from_playback(self):
        """
        Tries to set the start and end params to maya's playback
        range.

        Returns False on fail.
        """
        try:
            s, e = self.playblast_panel.controller.get_playback_range()
        except base_controller.PlayblastError:
            return False
        self.set_range(s, e)
        return True

    def on_set_range_from_montage_range(self):

        try:
            first, last = self.playblast_panel.controller.get_montage_range()
        except Exception as err:
            print("Error getting range from Montage:\n" + str(err))
            return False

        self.set_range(first, last)
        return True

    def on_set_range_from_render_setting(self):

        try:
            w, h = self.playblast_panel.controller.get_render_size()
        except Exception as err:
            print("Error getting size from Render:\n" + str(err))
            return False

        self.set_size(w, h)
        return True

    def on_set_bg_color(self, color_name):
        rgb = tuple([i for i in self.bg_color_options[color_name]])
        self.bg_color.setStyleSheet(
            "color: rgb{col}; background-color: rgb{col}; ".format(col=rgb)
        )
        self.bg_color.setText(color_name)

    def set_range(self, start, end):
        self.start.setText(str(start))
        self.end.setText(str(end))

    def set_size(self, width, height):
        self.width.setText(str(width))
        self.height.setText(str(height))

    def set_scale(self, scale):
        for i, (name, value) in enumerate(self.scale_options):
            if value == scale:
                self.scale_combo.setCurrentIndex(i)

    def get_blast_options(self):
        ret = {}
        try:
            ret["start"] = int(self.start.text())
        except Exception as e:
            raise self.ParamError("Start Frame")

        try:
            ret["end"] = int(self.end.text())
        except Exception:
            raise self.ParamError("End Frame")

        ret["use_sequencer"] = False

        try:
            ret["camera"] = self.camera.currentText()
        except Exception:
            raise self.ParamError("Camera")

        sound = self.sound.currentText()
        if not sound:
            ret["sounds"] = []
        elif sound == "*":
            ret["sounds"] = self.playblast_panel.controller.get_available_audios()
        else:
            ret["sounds"] = [sound]

        if ret["start"] >= ret["end"]:
            raise self.ParamError("Start Frame or End Frame")

        try:
            ret["width"] = int(self.width.text())
        except Exception:
            raise self.ParamError("Width")

        try:
            ret["height"] = int(self.height.text())
        except Exception:
            raise self.ParamError("Height")

        try:
            ret["scale"] = self.scale_options[self.scale_combo.currentIndex()][1]
        except Exception:
            raise self.ParamError("Scale")

        try:
            ret["bg_color"] = self.bg_color.text()
        except Exception:
            raise self.ParamError("BG Color")

        try:
            ret["display_types"] = self.display_configs[self.display_combo.currentText()]
        except Exception:
            raise self.ParamError("Display Config")

        try:
            ret["render_options"] = [
                (render_option.__class__.__name__, render_option.active) for render_option in self.render_options
            ]
        except Exception:
            raise self.ParamError("Display Options")

        try:
            ret["display_grid"] = self.display_grid.isChecked()
        except Exception:
            raise self.ParamError("Display Options")

        try:
            ret["hud_options"] = self.hud_options.get_params()
        except Exception:
            raise self.ParamError("Display Options")

        return ret
