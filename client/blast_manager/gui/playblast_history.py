import time
from datetime import datetime

from qtpy import QtCore
from qtpy import QtGui, QtWidgets

from .. controller import base_controller
from . import colors


class PlayblastHistory(QtWidgets.QTableWidget):
    """
    Contains the history of all the local playblasts
    """

    BACKGROUND_VALID_COLOR = QtGui.QBrush(QtGui.QColor(colors.VALID_COLOR))

    class Error(Exception):
        pass

    def __init__(
            self,
            playblast_panel
    ):
        super(PlayblastHistory, self).__init__(playblast_panel)

        self.playblast_panel = playblast_panel
        self.rows_data = dict()
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.setFont(QtGui.QFont("Verdana", 9))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self.setColumnCount(4)

        self.header = self.horizontalHeader()
        self.header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setHorizontalHeaderLabels(["User", "Range", "Date", "Time"])
        self.resize(600, 600)

        self.itemSelectionChanged.connect(self.selection_changed)
        self.customContextMenuRequested.connect(self.on_popup)

    def selection_changed(self):
        """
        Called when selection changed in PlayblastHistory
        Will open the blast in the PlayerPanel
        """
        items = self.selectedItems()
        if not items:
            return
        else:
            item = items[0]
            blast = self.get_blast_from_item(item)
            self.playblast_panel.open_sequence(blast)

    def mouseDoubleClickEvent(self, event):
        """
        Open a blast in Pd Player when double clicking on it
        :param QEvent event: event
        """
        super(PlayblastHistory, self).mouseDoubleClickEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            item = self.itemAt(event.pos())
            blast = self.get_blast_from_item(item)
            self.on_view_sequence(blast)

    def on_popup(self, pos):
        """
        Called when right-clicking a blast line in the PlayblastHistory
        Will show a menu depending on the blast info of this line
        :param QPoint pos: position of click
        """
        item = self.itemAt(pos)
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("QMenu { font-size: 10pt; }")

        if item is not None:
            blast = self.get_blast_from_item(item)

            if blast.has_seq:
                for third_party_action_info in self.playblast_panel.controller.third_party_open:
                    action_name = third_party_action_info[0]
                    action_callback = third_party_action_info[1]

                    menu.addAction(
                        action_name,
                        lambda _blast=blast: action_callback(_blast)
                    )

            menu.addAction(
                "Explore",
                lambda _blast=blast: self.on_explore(_blast)
            )
            menu.addSeparator()

            menu.addAction("Delete", self.on_delete_selected)
            menu.addSeparator()

        menu.addAction("Refresh", self.on_refresh)

        global_pos = self.mapToGlobal(pos)
        menu.exec_(global_pos)

    def on_delete_selected(self):
        """
        Deletes the selected blast
        """
        if not self.selectedItems():
            return

        self.setStyleSheet("selection-background-color: {};".format(colors.ERROR_COLOR))
        message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical,
                                            "Delete Blast",
                                            "Are you sure you want to delete this blast?",
                                            parent=self
                                            )

        delete_button = QtWidgets.QPushButton("Delete")
        delete_button.setStyleSheet("background-color: {};".format(colors.ERROR_COLOR))

        cancel_button = QtWidgets.QPushButton("Cancel")
        message_box.addButton(cancel_button, QtWidgets.QMessageBox.RejectRole)
        message_box.addButton(delete_button, QtWidgets.QMessageBox.ApplyRole)
        message_box.setDefaultButton(cancel_button)
        result = message_box.exec_()

        self.setStyleSheet("selection-background-color: {};".format(colors.INFO_COLOR))
        if result:
            item = self.selectedItems()[0]
            blast = self.get_blast_from_item(item)
            blast.delete()
            self.on_refresh()

    def get_blast_from_item(self, item):
        """
        Gets the blast from the given item
        :param QTableWidgetItem item: item to take the blast from
        :return: blast
        :rtype: BlastInfo
        """

        try:
            blast = self.rows_data.get(item.row())
        except AttributeError:
            if not hasattr(item, "_blast"):
                raise self.Error("No blast info on item.")
            else:
                blast = item._blast
                
        return blast

    def add_entry(self, blast):
        """
        Adds a line to the PlayblastHistory with the given blast
        :param BlastInfo blast: blast to add to history panel
        """
        blast_type = "["
        blast_type += blast.has_mov and base_controller.MOV or "   "
        blast_type += "|"
        blast_type += blast.has_seq and base_controller.SEQ or "   "
        blast_type += "]:"
        warning = ""

        if blast.has_seq and (blast.seq_disk_range[0] != blast.start or blast.seq_disk_range[1] != blast.end):
            warning = "(/!\\ Incomplete Frames)"

        display = "%s by %s %4s->%-4s %s (%sx%s)*%.2f on %s" % (
            blast_type, blast.user,
            blast.start, blast.end, warning,
            blast.width, blast.height, blast.scale,
            time.ctime(blast.timestamp).rsplit(" ", 1)[0],
        )

        user_item = QtWidgets.QTableWidgetItem(blast.user)
        range_item = QtWidgets.QTableWidgetItem("{} -> {}".format(blast.start, blast.end))

        date_item = QtWidgets.QTableWidgetItem(datetime.fromtimestamp(blast.timestamp).strftime("%d/%m/%Y"))
        time_item = QtWidgets.QTableWidgetItem(datetime.fromtimestamp(blast.timestamp).strftime("%H:%M:%S"))

        for item in [user_item, range_item, date_item, time_item]:
            item.setTextAlignment(QtCore.Qt.AlignCenter)

        row_count = self.rowCount()
        self.setRowCount(row_count + 1)
        vertical_header_labels = [str(index + 1) for index in range(row_count + 1)]
        vertical_header_labels.reverse()
        self.setVerticalHeaderLabels(vertical_header_labels)
        row_index = self.rowCount() - 1

        self.setItem(row_index, 0, user_item)
        self.setItem(row_index, 1, range_item)
        self.setItem(row_index, 2, date_item)
        self.setItem(row_index, 3, time_item)

        self.rows_data[row_index] = blast

    def on_refresh(self):
        """
        Refreshes the PlayblastHistory view
        """
        try:
            history = self.playblast_panel.controller.get_history()
        except base_controller.PlayblastError as err:
            QtWidgets.QMessageBox.critical(
                self, "Supa Blast Manager Error", str(err)
            )
            return

        self.setRowCount(0)

        # Sort by date
        history.sort(key=lambda x: x.timestamp)
        history.reverse()

        for (i, blast) in enumerate(history):
            self.add_entry(blast)

    def on_view_sequence(self, blast):
        """
        Triggered when double-clicking a blast
        or when clicking the "Open in Pd Player" in the right click menu

        :param BlastInfo blast: blast to open in Viewer
        """
        self.playblast_panel.controller.view_blast_seq(blast)

    def on_explore(self, blast):
        """
        Opens the related folder in Windows
        :param BlastInfo blast: blast
        """
        self.playblast_panel.controller.explore_blast(blast)

