import os

from qtpy import QtCore
from qtpy import QtGui, QtWidgets

from . import colors
from . params import PlayBlastParams
from . playblast_history import PlayblastHistory
from . player_panel import PlayerPanel

from .. import icons
from .. controller import base_controller


class HistoryPanel(QtWidgets.QWidget):
    """
    Panel containing the PlayBlastHistory and the Blast button
    """

    def __init__(
            self,
            playblast_panel
    ):
        super(HistoryPanel, self).__init__(playblast_panel)

        self.playblast_history = PlayblastHistory(
            playblast_panel
        )
        layout = QtWidgets.QVBoxLayout()

        blast_button = QtWidgets.QPushButton("Blast")
        blast_button.setStyleSheet("background-color: {}".format(colors.HIGHLIGHT_COLOR))
        blast_button.clicked.connect(playblast_panel.on_blast_seq)

        layout.addWidget(self.playblast_history)
        layout.addWidget(blast_button)

        self.setLayout(layout)

    def on_refresh(self):
        self.playblast_history.on_refresh()

    def on_view_sequence(self, blast):
        self.playblast_history.on_view_sequence(blast)

    def select_row(self, row_index):
        self.playblast_history.selectRow(row_index)

    def on_delete_selected(self):
        self.playblast_history.on_delete_selected()


class PlayblastGui(QtWidgets.QWidget):
    """
    Main window of the play blast manager
    """

    WINDOW_TITLE = "Supa Blast Manager"
    STYLESHEET_FILE_NAME = "stylesheet.qss"

    def __init__(
            self,
            parent,
            controller_type,
            local_path,
            scene_path,
            default_camera,
            third_party_open
    ):
        """

        Args:
            parent (QWidget): parent widget
            controller_type: controller type
            local_path (str): destination of blast in local machine
            scene_path (str): scene path
            default_camera (str): default camera name
            third_party_open (list[tuple]): Optional list of callbacks to open blasts with third party applications
                the first item of the tuple will be the label of the action, when right-clicking a blast,
                the second item of the tuple the callback executed when clicking on this action,
                with BlastInfo of the blast as argument.
                For example: [("Open in Pd player", pd_player_callback), ("Open in RV", rv_callback)]
        """
        super().__init__(parent, QtCore.Qt.Window)

        self.controller = controller_type(
            local_path=local_path,
            scene_path=scene_path,
            default_camera=default_camera,
            third_party_open=third_party_open,
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowIcon(icons.get_icon("supa_prod.png"))

        self.load_stylesheet()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setLayout(QtWidgets.QVBoxLayout())

        splitter = QtWidgets.QSplitter(self)
        self.layout().addWidget(splitter)

        # Parameters panel (scrollable)
        self.param_panel = PlayBlastParams(self)
        self.scroll_param_panel = QtWidgets.QScrollArea()
        self.scroll_param_panel.setFocusPolicy(QtCore.Qt.NoFocus)
        self.scroll_param_panel.setWidgetResizable(True)
        self.scroll_param_panel.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_param_panel.setWidget(self.param_panel)

        self.player_panel = PlayerPanel()

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.addTab(self.player_panel, "Player")
        self.tab_widget.addTab(self.scroll_param_panel, "Settings")
        self.tab_widget.setCurrentWidget(self.scroll_param_panel)

        self.history_panel = HistoryPanel(self)

        splitter.addWidget(self.tab_widget)
        splitter.addWidget(self.history_panel)

        self.history_panel.on_refresh()

        self.resize(self.player_panel.width() + self.history_panel.width(), self.player_panel.height())
        splitter.setSizes([600, 600])

        previous_frame_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence.MoveToPreviousChar, self)
        previous_frame_shortcut.activated.connect(self.player_panel.move_previous_frame)

        next_frame_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence.MoveToNextChar, self)
        next_frame_shortcut.activated.connect(self.player_panel.move_next_frame)

        play_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self)
        play_shortcut.activated.connect(self.player_panel.play)

        delete_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.history_panel.on_delete_selected)

        self.resize(1280, 720)

    def load_stylesheet(self):
        stylesheet_location = os.path.join(os.path.dirname(__file__), self.STYLESHEET_FILE_NAME)

        with open(stylesheet_location, "r") as stylesheet:
            stylesheet_content = stylesheet.read()

            format_dict = {
                "primary": colors.PRIMARY_COLOR,
                "primary_light": colors.PRIMARY_LIGHT_COLOR,
                "secondary": colors.SECONDARY_COLOR,
                "tertiary": colors.TERTIARY_COLOR,
                "text": colors.TEXT_COLOR,
                "highlight": colors.HIGHLIGHT_COLOR,
                "lighter": colors.LIGHTER_COLOR,
                "check": icons.get_path("check.png").replace("\\", "/"),
                "arrow": icons.get_path("down_triangular_arrow.png").replace("\\", "/")
            }

            self.setStyleSheet(stylesheet_content.format(**format_dict))

    def refresh(self):
        self.history_panel.on_refresh()

    def get_blast_options(self):
        try:
            return self.param_panel.get_blast_options()
        except self.param_panel.ParamError as err:
            QtWidgets.QMessageBox.critical(
                self, "Supa Blast Manager Error", str(err)
            )
            raise
        except Exception as err:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "Error: ", str(err)
            )
            raise

    def on_blast_ended(self, blast):
        """
        Triggered when the DCC is done making a blast
        :param BlastInfo blast: Created blast
        """
        import tempfile

        blast.check_results()

        if tempfile.gettempdir() in os.path.abspath(blast.scene_path):
            os.remove(blast.scene_path)
        self.history_panel.on_refresh()

        self.history_panel.select_row(0)

        # Set the focus on the Player tab
        self.tab_widget.setCurrentIndex(0)

    def blast(self, params):
        """
        Make a new blast with the given params
        :param PlayBlastHUDParams params: params of the blast to create
        """
        try:
            blast = self.controller.blast(**params)
        except base_controller.PlayblastError as err:
            QtWidgets.QMessageBox.critical(
                self, "ERROR", str(err)
            )
            raise
        else:
            self.on_blast_ended(blast)

    def on_blast_seq(self):
        """
        Called when creating a new blast by clicking the blast button in the HistoryPanel
        Creates a blast with the params chosen in the PlayBlastHUDParams
        """
        params = self.param_panel.get_blast_options()
        params["blast_type"] = base_controller.SEQ
        self.blast(params)

    def open_sequence(self, blast):
        """
        Opens the blast in the PlayerPanel
        :param BlastInfo blast: blast to open
        """
        self.player_panel.open_sequence(blast)
