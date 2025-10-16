import os
from qtpy import QtGui


def get_icon(name):
    icon_path = get_path(name)
    if not os.path.exists(icon_path):
        raise KeyError(f"Icon '{name}' was not found")
    pixmap = QtGui.QPixmap(icon_path)

    return QtGui.QIcon(pixmap)


def get_path(name):
    icons_directory = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(icons_directory, name)
    return icon_path
