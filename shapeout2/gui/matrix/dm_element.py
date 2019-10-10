import pkg_resources

from PyQt5 import uic, QtWidgets, QtCore


class MatrixElement(QtWidgets.QWidget):
    _quick_view_instance = None
    quickview_selected = QtCore.pyqtSignal()

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "dm_element.ui")
        uic.loadUi(path_ui, self)

        self.active = False
        self.enabled = True

        self.update_content()

    def __getstate__(self):
        state = {"active": self.active,
                 "enabled": self.enabled}
        return state

    def __setstate__(self, state):
        self.active = state["active"]
        self.enabled = state["enabled"]
        self.update_content()

    def has_quickview(self):
        curinst = MatrixElement._quick_view_instance
        if curinst is self:
            quickview = True
        else:
            quickview = False
        return quickview

    def mousePressEvent(self, event):
        # toggle selection
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            quickview = not self.has_quickview()
        else:
            self.active = not self.active
            quickview = False
        self.update_content(quickview)
        event.accept()

    def update_content(self, quickview=False):
        if self.active and self.enabled:
            color = "#86E789"  # green
            label = "active"
            tooltip = "Click to deactivate"
        elif self.active and not self.enabled:
            color = "#C9DAC9"  # gray-green
            label = "active\n(disabled)"
            tooltip = "Click to deactivate"
        elif not self.active and self.enabled:
            color = "#EFEFEF"  # light gray
            label = "inactive"
            tooltip = "Click to activate"
        else:
            color = "#DCDCDC"  # gray
            label = "inactive\n(disabled)"
            tooltip = "Click to activate"

        if self.has_quickview():
            do_quickview = True
        elif quickview:
            curinst = MatrixElement._quick_view_instance
            # reset color of old quick view instance
            if curinst is not None and self is not curinst:
                MatrixElement._quick_view_instance = None
                curinst.update_content()
            MatrixElement._quick_view_instance = self
            do_quickview = True
        else:
            do_quickview = False
        if do_quickview:
            color = "#F0A1D6"
            label += "\n(QV)"
            self.quickview_selected.emit()
        else:
            tooltip += "\nShift+Click for Quick View"

        self.setStyleSheet("background-color:{}".format(color))
        self.label.setStyleSheet("background-color:{}".format(color))
        self.label.setText(label)
        self.setToolTip(tooltip)
        self.label.setToolTip(tooltip)