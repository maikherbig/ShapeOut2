import copy
import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets

from ...pipeline import Plot
from ...pipeline.plot import STATE_OPTIONS


COLORMAPS = STATE_OPTIONS["scatter"]["colormap"]


class PlotPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.pipeline.Plot is to be changed
    plot_changed = QtCore.pyqtSignal(dict)
    #: Emitted when the pipeline is to be changed
    pipeline_changed = QtCore.pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_plot.ui")
        uic.loadUi(path_ui, self)

        # current Shape-Out 2 pipeline
        self._pipeline = None
        self._init_controls()
        self.update_content()

        # options for division
        self.comboBox_division.clear()
        self.comboBox_division.addItem("Merge all plots", "merge")
        self.comboBox_division.addItem("One plot per dataset", "each")
        self.comboBox_division.addItem("Scatter plots and joint contour plot",
                                       "multiscatter+contour")
        self.comboBox_division.setCurrentIndex(2)

        # signals
        self.pushButton_duplicate.clicked.connect(self.on_duplicate_plot)
        self.pushButton_remove.clicked.connect(self.on_remove_plot)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.pushButton_apply.clicked.connect(self.write_plot)
        self.comboBox_plots.currentIndexChanged.connect(self.update_content)
        self.comboBox_marker_hue.currentIndexChanged.connect(
            self.on_hue_select)
        self.comboBox_axis_x.currentIndexChanged.connect(self.on_axis_select)
        self.comboBox_axis_y.currentIndexChanged.connect(self.on_axis_select)

    def __getstate__(self):
        feats_srt = self.pipeline.get_features(
            scalar=True, label_sort=True, plot_id=self.current_plot.identifier)

        rx = self.widget_range_x.__getstate__()
        ry = self.widget_range_y.__getstate__()

        state = {
            "identifier": self.current_plot.identifier,
            "layout": {
                "column count": self.spinBox_column_count.value(),
                "division": self.comboBox_division.currentData(),
                "label plots": self.checkBox_label_plots.isChecked(),
                "name": self.lineEdit.text(),
                "size x": self.spinBox_size_x.value(),
                "size y": self.spinBox_size_y.value(),
            },
            "general": {
                "axis x": feats_srt[self.comboBox_axis_x.currentIndex()],
                "axis y": feats_srt[self.comboBox_axis_y.currentIndex()],
                "isoelastics": self.checkBox_isoelastics.isChecked(),
                "kde": self.comboBox_kde.currentData(),
                "range x": [rx["start"], rx["end"]],
                "range y": [ry["start"], ry["end"]],
                "scale x": self.comboBox_scale_x.currentData(),
                "scale y": self.comboBox_scale_y.currentData(),
            },
            "scatter": {
                "colormap": self.comboBox_colormap.currentData(),
                "downsample": self.checkBox_downsample.isChecked(),
                "downsampling value": self.spinBox_downsample.value(),
                "enabled": self.groupBox_scatter.isChecked(),
                "hue feature": self.comboBox_marker_feature.currentData(),
                "marker alpha": self.spinBox_alpha.value() / 100,
                "marker hue": self.comboBox_marker_hue.currentData(),
                "marker size": self.doubleSpinBox_marker_size.value(),
                "show event count": self.checkBox_event_count.isChecked(),
            },
            "contour": {
                "enabled": self.groupBox_contour.isChecked(),
                "legend":  self.checkBox_legend.isChecked(),
                "line widths": [self.doubleSpinBox_lw_1.value(),
                                self.doubleSpinBox_lw_2.value(),
                                ],
                "line styles": [self.comboBox_ls_1.currentData(),
                                self.comboBox_ls_2.currentData(),
                                ],
                "percentiles": [self.doubleSpinBox_perc_1.value(),
                                self.doubleSpinBox_perc_2.value(),
                                ],
                "spacing x": self.doubleSpinBox_spacing_x.value(),
                "spacing y": self.doubleSpinBox_spacing_y.value(),
            }
        }
        return state

    def __setstate__(self, state):
        if self.current_plot.identifier != state["identifier"]:
            raise ValueError("Plot identifier mismatch!")
        feats_srt = self.pipeline.get_features(
            scalar=True, label_sort=True, plot_id=self.current_plot.identifier)
        toblock = [
            self.comboBox_axis_x,
            self.comboBox_axis_y,
        ]

        for b in toblock:
            b.blockSignals(True)

        # General
        lay = state["layout"]
        self.spinBox_column_count.setValue(lay["column count"])
        idx = self.comboBox_division.findData(lay["division"])
        self.comboBox_division.setCurrentIndex(idx)
        self.checkBox_label_plots.setChecked(lay["label plots"])
        self.lineEdit.setText(lay["name"])
        self.spinBox_size_x.setValue(lay["size x"])
        self.spinBox_size_y.setValue(lay["size y"])
        gen = state["general"]
        self.comboBox_axis_x.setCurrentIndex(feats_srt.index(gen["axis x"]))
        self.comboBox_axis_y.setCurrentIndex(feats_srt.index(gen["axis y"]))
        self.checkBox_isoelastics.setChecked(gen["isoelastics"])
        kde_index = self.comboBox_kde.findData(gen["kde"])
        self.comboBox_kde.setCurrentIndex(kde_index)
        scx_index = self.comboBox_scale_x.findData(gen["scale x"])
        self.comboBox_scale_x.setCurrentIndex(scx_index)
        scy_index = self.comboBox_scale_y.findData(gen["scale y"])
        self.comboBox_scale_y.setCurrentIndex(scy_index)
        self._set_range_state(axis_x=gen["axis x"],
                              axis_y=gen["axis y"],
                              range_x=gen["range x"],
                              range_y=gen["range y"],
                              )

        # Scatter
        sca = state["scatter"]
        self.checkBox_downsample.setChecked(sca["downsample"])
        self.spinBox_downsample.setValue(sca["downsampling value"])
        self.groupBox_scatter.setChecked(sca["enabled"])
        hue_index = self.comboBox_marker_hue.findData(sca["marker hue"])
        self.comboBox_marker_hue.setCurrentIndex(hue_index)
        self.doubleSpinBox_marker_size.setValue(sca["marker size"])
        feat_index = feats_srt.index(sca["hue feature"])
        self.comboBox_marker_feature.setCurrentIndex(feat_index)
        color_index = COLORMAPS.index(sca["colormap"])
        self.comboBox_colormap.setCurrentIndex(color_index)
        self.checkBox_event_count.setChecked(sca["show event count"])
        self.spinBox_alpha.setValue(sca["marker alpha"]*100)

        # Contour
        con = state["contour"]
        self.groupBox_contour.setChecked(con["enabled"])
        self.checkBox_legend.setChecked(con["legend"])
        self.doubleSpinBox_perc_1.setValue(con["percentiles"][0])
        self.doubleSpinBox_perc_2.setValue(con["percentiles"][1])
        self.doubleSpinBox_lw_1.setValue(con["line widths"][0])
        self.doubleSpinBox_lw_2.setValue(con["line widths"][1])
        ls1_index = self.comboBox_ls_1.findData(con["line styles"][0])
        self.comboBox_ls_1.setCurrentIndex(ls1_index)
        ls2_index = self.comboBox_ls_2.findData(con["line styles"][1])
        self.comboBox_ls_2.setCurrentIndex(ls2_index)
        for control, spacing in zip([self.doubleSpinBox_spacing_x,
                                     self.doubleSpinBox_spacing_y],
                                    [con["spacing x"],
                                     con["spacing y"]]):
            if spacing >= 1:
                dec = 2
            else:
                dec = -np.int(np.log10(spacing)) + 3
            control.setDecimals(dec)
            control.setMinimum(10**-dec)
            control.setSingleStep(10**-dec)
            control.setValue(spacing)

        for b in toblock:
            b.blockSignals(False)

    def _init_controls(self):
        """All controls that are not subject to change"""
        # KDE
        kde_names = STATE_OPTIONS["general"]["kde"]
        self.comboBox_kde.clear()
        for kn in kde_names:
            self.comboBox_kde.addItem(kn.capitalize(), kn)
        # Scales
        scales = STATE_OPTIONS["general"]["scale x"]
        self.comboBox_scale_x.clear()
        self.comboBox_scale_y.clear()
        for sc in scales:
            if sc == "log":
                vc = "logarithmic"
            else:
                vc = sc
            self.comboBox_scale_x.addItem(vc, sc)
            self.comboBox_scale_y.addItem(vc, sc)
        # Marker hue
        hues = STATE_OPTIONS["scatter"]["marker hue"]
        self.comboBox_marker_hue.clear()
        for hue in hues:
            if hue == "kde":
                huev = "KDE"
            else:
                huev = hue.capitalize()
            self.comboBox_marker_hue.addItem(huev, hue)
        self.comboBox_colormap.clear()
        for c in COLORMAPS:
            self.comboBox_colormap.addItem(c, c)
        # Contour line styles
        lstyles = STATE_OPTIONS["contour"]["line styles"][0]
        self.comboBox_ls_1.clear()
        self.comboBox_ls_2.clear()
        for l in lstyles:
            self.comboBox_ls_1.addItem(l, l)
            self.comboBox_ls_2.addItem(l, l)
        # range controls
        for rc in [self.widget_range_x, self.widget_range_y]:
            rc.setLabel("")
            rc.setCheckable(False)

    def _set_range_state(self, axis_x=None, range_x=None,
                         axis_y=None, range_y=None):
        """Set a proper state for the range controls"""
        if len(self.pipeline.slots) == 0:
            self.setEnabled(False)
            # do nothing
            return
        else:
            self.setEnabled(True)
        for axis, rang, rc in zip([axis_x, axis_y],
                                  [range_x, range_y],
                                  [self.widget_range_x, self.widget_range_y],
                                  ):
            if axis is not None:
                lim = self.pipeline.get_min_max(feat=axis)
                rc.setLimits(vmin=lim[0],
                             vmax=lim[1])
                if rang is None:
                    rang = lim
                rc.__setstate__({"active": True,
                                 "start": rang[0],
                                 "end": rang[1],
                                 })

    def _set_contour_spacing(self, axis_x=None, axis_y=None):
        if len(self.pipeline.slots) == 0:
            self.setEnabled(False)
            # do nothing
            return
        else:
            self.setEnabled(True)
        for axis, doubleSpinBox in zip([axis_x, axis_y],
                                       [self.doubleSpinBox_spacing_x,
                                        self.doubleSpinBox_spacing_y]):
            if axis is None:
                # nothing to do
                continue
            else:
                # determine good approximation
                dslist, _ = self.pipeline.get_plot_datasets(
                    self.current_plot.identifier)
                spacings = []
                for ds in dslist:
                    spa = dclab.kde_methods.bin_width_percentile(ds[axis])
                    spacings.append(spa)
                if spacings:
                    doubleSpinBox.setValue(np.min(spacings))

    @property
    def current_plot(self):
        if self.plot_ids:
            plot_index = self.comboBox_plots.currentIndex()
            plot_id = self.plot_ids[plot_index]
            plot = Plot.get_instances()[plot_id]
        else:
            plot = None
        return plot

    @property
    def pipeline(self):
        return self._pipeline

    @property
    def plot_ids(self):
        """List of plot identifiers"""
        if self.pipeline is not None:
            ids = [plot.identifier for plot in self.pipeline.plots]
        else:
            ids = []
        return ids

    @property
    def plot_names(self):
        """List of plot names"""
        if self.pipeline is not None:
            ids = [plot.name for plot in self.pipeline.plots]
        else:
            ids = []
        return ids

    def on_axis_select(self):
        gen = self.__getstate__()["general"]
        if self.sender() == self.comboBox_axis_x:
            self._set_range_state(axis_x=gen["axis x"])
            self._set_contour_spacing(axis_x=gen["axis x"])
        elif self.sender() == self.comboBox_axis_y:
            self._set_range_state(axis_y=gen["axis y"])
            self._set_contour_spacing(axis_y=gen["axis y"])

    def on_duplicate_plot(self):
        # determine the new filter state
        plot_state = self.__getstate__()
        new_state = copy.deepcopy(plot_state)
        new_plot = Plot()
        new_state["identifier"] = new_plot.identifier
        new_state["layout"]["name"] = new_plot.name
        new_plot.__setstate__(new_state)
        # determine the filter position
        pos = self.pipeline.plot_ids.index(plot_state["identifier"])
        self.pipeline.add_plot(new_plot, index=pos+1)
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_remove_plot(self):
        plot_state = self.__getstate__()
        self.pipeline.remove_plot(plot_state["identifier"])
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_hue_select(self):
        """Show/hide options for feature-based hue selection"""
        selection = self.comboBox_marker_hue.currentData()
        # hide everything
        self.comboBox_marker_feature.hide()
        self.widget_dataset_alpha.hide()
        self.comboBox_colormap.hide()
        self.label_colormap.hide()
        # Only show feature selection if needed
        if selection == "feature":
            self.comboBox_marker_feature.show()
            self.comboBox_colormap.show()
            self.label_colormap.show()
        elif selection == "kde":
            self.comboBox_colormap.show()
            self.label_colormap.show()
        elif selection in ["dataset", "none"]:
            self.widget_dataset_alpha.show()
        else:
            raise ValueError("Unknown selection: '{}'".format(selection))

    def show_plot(self, plot_id):
        self.update_content(plot_index=self.plot_ids.index(plot_id))

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def update_content(self, event=None, plot_index=None):
        if self.plot_ids:
            self.setEnabled(True)
            # update combobox
            self.comboBox_plots.blockSignals(True)
            # this also updates the combobox
            if plot_index is None:
                plot_index = self.comboBox_plots.currentIndex()
                if plot_index > len(self.plot_ids) - 1 or plot_index < 0:
                    plot_index = len(self.plot_ids) - 1
            self.comboBox_plots.clear()
            self.comboBox_plots.addItems(self.plot_names)
            self.comboBox_plots.setCurrentIndex(plot_index)
            self.comboBox_plots.blockSignals(False)
            # set choices for all comboboxes that deal with features
            for cb in [self.comboBox_axis_x,
                       self.comboBox_axis_y,
                       self.comboBox_marker_feature]:
                cb.blockSignals(True)
                if cb.count:
                    # remember current selection
                    curfeat = cb.currentData()
                else:
                    curfeat = None
                # repopulate
                cb.clear()
                feats_srt = self.pipeline.get_features(
                    scalar=True,
                    label_sort=True,
                    plot_id=self.current_plot.identifier)
                for feat in feats_srt:
                    cb.addItem(dclab.dfn.feature_name2label[feat], feat)
                if curfeat is not None:
                    # write back current selection
                    curidx = feats_srt.index(curfeat)
                    cb.setCurrentIndex(curidx)
                cb.blockSignals(False)
            # populate content
            plot = Plot.get_plot(identifier=self.plot_ids[plot_index])
            state = plot.__getstate__()
            self.__setstate__(state)
            # set default contour spacings
            gen = state["general"]
            self._set_contour_spacing(axis_x=gen["axis x"],
                                      axis_y=gen["axis y"])

        else:
            self.setEnabled(False)

    def write_plot(self):
        """Update the shapeout2.pipeline.Plot instance"""
        # get current index
        plot_index = self.comboBox_plots.currentIndex()
        plot = Plot.get_plot(identifier=self.plot_ids[plot_index])
        plot_state = self.__getstate__()
        plot.__setstate__(plot_state)
        self.update_content()  # update plot selection combobox
        self.plot_changed.emit(plot_state)
