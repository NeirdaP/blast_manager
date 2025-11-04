import math

from qtpy import QtCore
from qtpy import QtWidgets
from .. import icons


class TimeSlider(QtWidgets.QSlider):
    """
    Time slider of the PlayerPanel
    """

    def __init__(self, player_panel, parent=None):
        super(TimeSlider, self).__init__(parent)
        self.player_panel = player_panel
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setRange(0, 0)
        self.sliderMoved.connect(self.player_panel.time_slider_moved)

    def mousePressEvent(self, event):
        super(TimeSlider, self).mousePressEvent(event)
        self.player_panel.time_slider_moved()


class PlayerPanel(QtWidgets.QWidget):
    """
    Player to preview playblast directly in the playblast manager
    """

    def __init__(self, parent=None):
        super(PlayerPanel, self).__init__(parent)

        self.playing = False
        self.blast = None
        self.image_files = []
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.player = QtWidgets.QLabel()
        self.player.setStyleSheet("background-color: black;")
        self.player.setAlignment(QtCore.Qt.AlignCenter)
        self.player.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.player.setMinimumSize(100, 100)

        icon = icons.get_icon("supa_prod.png")
        pixmap = icon.pixmap(QtCore.QSize(int(self.player.width() / 2), int(self.player.height())))
        image = pixmap.toImage()
        x = - self.player.width() / 2 + pixmap.width() / 2
        y = - self.player.height() / 2 + pixmap.height() / 2
        resized_image = image.copy(x, y, self.player.width(), self.player.height())
        pixmap = pixmap.fromImage(resized_image)
        self.pixmap = pixmap

        self.player.setPixmap(self.pixmap)

        self.sequence_dir = QtCore.QDir()

        self.player_frame_rate = 25

        self.time_line = QtCore.QTimeLine()
        self.time_line.setEasingCurve(QtCore.QEasingCurve.Linear)
        self.time_line.frameChanged.connect(self.frame_changed)
        self.time_line.finished.connect(self.finished)
        self.time_line.setUpdateInterval(int(1000 / self.player_frame_rate))

        self.current_frame_display_button = QtWidgets.QPushButton()
        self.current_frame_display_button.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.current_frame_display_button.setText("1")
        self.current_frame_display_button.setEnabled(False)
        self.current_frame_display_button.setCheckable(True)
        self.current_frame_display_button.clicked.connect(self.refresh_frame_count_display)

        self.play_button = QtWidgets.QPushButton()
        self.play_button.setIcon(
            icons.get_icon("play.png")
        )
        self.play_button.clicked.connect(self.play)

        self.next_frame_button = QtWidgets.QPushButton()
        self.next_frame_button.setIcon(icons.get_icon("next_frame.png"))
        self.next_frame_button.setCheckable(False)
        self.next_frame_button.pressed.connect(self.move_next_frame)

        self.previous_frame_button = QtWidgets.QPushButton()
        self.previous_frame_button.setIcon(icons.get_icon("previous_frame.png"))

        self.previous_frame_button.setCheckable(False)
        self.previous_frame_button.pressed.connect(self.move_previous_frame)

        self.disable_control_buttons()

        self.time_slider = TimeSlider(self)

        self.error_label = QtWidgets.QLabel()
        self.error_label.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Maximum)
        self.error_label.setAlignment(QtCore.Qt.AlignCenter)

        # Create layouts to place inside widget
        control_layout = QtWidgets.QGridLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(self.current_frame_display_button, 0, 0)
        control_layout.addWidget(self.play_button, 1, 0)
        control_layout.addWidget(self.previous_frame_button, 1, 1)
        control_layout.addWidget(self.next_frame_button, 1, 2)
        control_layout.addWidget(self.time_slider, 1, 3)

        self.player_layout = QtWidgets.QVBoxLayout()
        self.player_layout.addWidget(self.player)
        self.player_layout.addWidget(self.error_label)

        self.player_layout.addLayout(control_layout)

        # Set widget to contain window contents
        self.setLayout(self.player_layout)
        self.resize(600, 600)

    def load_frame(self, file_path):
        """
        Loads the frame from the given path in the player while keeping scale correctly
        :param str file_path: file path of the frame
        """
        self.pixmap.load(file_path)
        pixmap = self.pixmap.scaled(self.player.width(), self.player.height(), QtCore.Qt.KeepAspectRatio)
        self.player.setPixmap(pixmap)

    def resizeEvent(self, event):
        """
        Resize the pixmap, so it fits the player (QLabel)
        :param QEvent event: event
        """
        pixmap = self.pixmap.scaled(self.player.width(), self.player.height(), QtCore.Qt.KeepAspectRatio)
        self.player.setPixmap(pixmap)

    def finished(self):
        """
        Triggered when the playblast ended in the player
        Pauses the player
        """
        self.time_line.setPaused(True)
        self.time_line.setStartFrame(1)
        self.play_button.setIcon(icons.get_icon("play.png"))

        self.playing = False

    def frame_changed(self):
        """
        Triggered when frame changed in the player
        Changes the image to match the frame and set the frame count accordingly
        """
        self.set_slider_position(self.time_line.currentFrame())
        current_image = self.image_files[self.time_line.currentFrame() - 1]
        self.load_frame(current_image.filePath())
        self.refresh_frame_count_display()

    def refresh_frame_count_display(self):
        """
        Sets the frame count from the current frame of self.time_line
        """
        if self.current_frame_display_button.isChecked():
            current_frame = str(self.time_line.currentFrame())
            tooltip = "Shot frame\n" \
                      "Click to switch to Montage frame"
        else:
            current_frame = str(self.time_line.currentFrame() + self.blast.start - 1)
            tooltip = "Montage frame\n" \
                      "Click to switch to Shot frame"
        self.current_frame_display_button.setText(current_frame)
        self.current_frame_display_button.setToolTip(tooltip)

    def open_sequence(self, blast):
        """
        Opens the given blast in the player
        :param BlastInfo blast: blast to open
        """
        self.blast = blast
        self.sequence_dir.setPath(blast.seq_path())
        self.player_frame_rate = blast.frame_rate
        self.time_line.setUpdateInterval(int(1000 / self.player_frame_rate))
        self.image_files = [image for image in self.sequence_dir.entryInfoList() if image.isFile()
                            and image.suffix() in ["png", "jpg", "jpeg"]]
        if not self.image_files:
            self.handle_error("No image found for this playblast")
        else:
            self.load_frame(self.image_files[0].filePath())
            self.time_line.setCurrentTime(1)
            self.enable_control_buttons()
            self.duration_changed(len(self.image_files))
            self.error_label.clear()
            self.refresh_frame_count_display()

    def play(self):
        """
        Triggered when the play button is clicked in the PlayerPanel
        Starts the timeline and plays the blast if blast is paused,
        or pause it if its already playing
        Also sets the icon of the play button to match the current state
        """
        if not self.playing:

            self.play_button.setIcon(icons.get_icon("pause.png"))
            if self.time_line.currentFrame() == self.time_line.endFrame():
                self.time_line.setCurrentTime(0)
            self.time_line.resume()
            self.playing = True
        else:
            self.time_line.setPaused(True)
            self.play_button.setIcon(icons.get_icon("play.png"))
            self.playing = False

    def time_slider_moved(self):
        """
        Triggered when the time slider cursor is moved
        Change the frame according to the new position of the slider
        """
        current_frame = self.time_slider.sliderPosition()
        self.move_to_frame(current_frame)

    def move_to_frame(self, frame):
        """
        Moves the player to the given frame
        :param int frame: frame to move to
        """
        target_time = math.floor(float(frame) / self.player_frame_rate * 1000)
        self.time_line.setCurrentTime(target_time)

    def move_next_frame(self):
        """
        Triggered when next frame button is clicked
        Moves the player to the next frame
        """
        current_frame = self.time_slider.sliderPosition()
        target_frame = current_frame + 1
        self.move_to_frame(target_frame)

    def move_previous_frame(self):
        """
        Triggered when previous frame button is clicked
        Moves the player to the previous frame
        """
        current_frame = self.time_slider.sliderPosition()
        target_frame = current_frame - 1
        self.move_to_frame(target_frame)

    def disable_control_buttons(self):
        """
        Disables the control buttons (play, previous frame, next frame)
        Used when first opening the playblast manager, when no blast is selected
        """
        for button in [self.play_button, self.previous_frame_button, self.next_frame_button,
                       self.current_frame_display_button]:
            button.setEnabled(False)

    def enable_control_buttons(self):
        """
        Enables the control buttons (play, previous frame, next frame)
        Used when opening a blast in the player
        """
        for button in [self.play_button, self.previous_frame_button, self.next_frame_button,
                       self.current_frame_display_button]:
            button.setEnabled(True)

    def duration_changed(self, duration):
        """
        Triggered when a blast is selected in the PlayblastHistory
        Changes the duration of the timeline with the duration of the new playblast
        :param int duration: duration of the blast (in frames)
        """
        self.time_slider.setRange(1, duration)
        self.time_line.setFrameRange(1, len(self.image_files))
        self.time_line.setDuration(int(float(duration) / self.player_frame_rate * 1000))

    def set_slider_position(self, position):
        """
        Sets the slider position with th given one
        :param int position: new slider position
        """
        if self.playing:
            self.time_line.setPaused(True)
            self.time_slider.setSliderPosition(position)
            self.time_line.resume()
        else:
            self.time_slider.setSliderPosition(position)

    def handle_error(self, error_message):
        """
        Called when encountering an error trying to open a blast in the player
        Will display the error below the player and set and error icon of the player
        :param str error_message: message of the error
        """
        self.disable_control_buttons()
        self.error_label.setText(error_message)

        icon = self.player.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton)
        pixmap = icon.pixmap(QtCore.QSize(int(self.player.width() / 2), int(self.player.height())))
        image = pixmap.toImage()
        x = - self.player.width() / 2 + pixmap.width() / 2
        y = - self.player.height() / 2 + pixmap.height() / 2
        resized_image = image.copy(x, y, self.player.width(), self.player.height())
        pixmap = pixmap.fromImage(resized_image)
        self.pixmap = pixmap
        self.player.setPixmap(self.pixmap)
