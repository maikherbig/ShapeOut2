import dclab
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

from ... import plot_cache

from .. import pipeline_plot
from ..simple_plot_widget import SimplePlotWidget, SimpleViewBox


class QuickViewScatterWidget(SimplePlotWidget):
    def __init__(self, *args, **kwargs):
        self._view_box = QuickViewViewBox()
        super(QuickViewScatterWidget, self).__init__(viewBox=self._view_box,
                                                     *args, **kwargs)
        self.scatter = RTDCScatterPlot()
        self.select = pg.PlotDataItem(x=[1], y=[2], symbol="o")
        #: List of isoelasticity line plots
        self.isoelastics = []
        self.addItem(self.scatter)
        self.addItem(self.select)
        self.select.hide()
        self.xscale = "linear"
        self.yscale = "linear"
        #: Boolean array identifying the plotted events w.r.t. the full
        #: dataset
        self.events_plotted = None
        #: Unfiltered and not-downsampled x component of current scatter plot
        self.data_x = None
        #: Unfiltered and not-downsampled y component of current scatter plot
        self.data_y = None

        # polygon editing ROI
        self.poly_line_roi = None

        # Signals for mouse click
        # let view box update the selected event in the scatter plot
        self._view_box.set_scatter_point.connect(self.scatter.set_point)
        # let view box update self.poly_line_roi
        self._view_box.add_poly_vertex.connect(self.add_poly_vertex)

    def add_poly_vertex(self, pos):
        state = self.poly_line_roi.getState()
        state["points"].append([pos.x(), pos.y()])
        self.poly_line_roi.setState(state)

    def plot_data(self, rtdc_ds, slot, xax="area_um", yax="deform",
                  xscale="linear", yscale="linear",  downsample=False,
                  isoelastics=False):
        self.rtdc_ds = rtdc_ds
        self.slot = slot
        self.xax = xax
        self.yax = yax
        x, y, kde, idx = plot_cache.get_scatter_data(
            rtdc_ds=self.rtdc_ds,
            downsample=downsample,
            xax=self.xax,
            yax=self.yax,
            xscale=self.xscale,
            yscale=self.yscale)
        self.events_plotted = idx
        #: unfiltered x data
        self.data_x = self.rtdc_ds[self.xax]
        #: unfiltered y data
        self.data_y = self.rtdc_ds[self.yax]
        # define colormap
        # TODO: improve speed?
        brush = []
        kde -= kde.min()
        kde /= kde.max()
        num_hues = 500
        for k in kde:
            color = pg.intColor(int(k*num_hues), num_hues)
            brush.append(color)
        # convert to log-scale if applicable
        if xscale == "log":
            x = np.log10(x)
        if yscale == "log":
            y = np.log10(y)
        # set data
        self.scatter.setData(x=x, y=y, brush=brush)
        # set log mode
        self.plotItem.setLogMode(x=xscale == "log",
                                 y=yscale == "log")
        # reset range (in case user modified it manually)
        # (For some reason, we have to do this twice...)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)
        # set axes labels (replace with user-defined flourescence names)
        left = dclab.dfn.feature_name2label[self.yax]
        bottom = dclab.dfn.feature_name2label[self.xax]
        for key in self.slot.fl_name_dict:
            if key in left:
                left = left.replace(key, self.slot.fl_name_dict[key])
                break
        for key in self.slot.fl_name_dict:
            if key in bottom:
                bottom = bottom.replace(key, self.slot.fl_name_dict[key])
                break
        self.plotItem.setLabels(left=left, bottom=bottom)

        # Force updating the plot item size, otherwise axes labels
        # may have an offset.
        s = self.plotItem.size()
        self.plotItem.resize(s.width()+1, s.height())
        self.plotItem.resize(s)

        # Isoelastics
        # remove old isoelastics
        for lp in self.isoelastics:
            self.removeItem(lp)
        if isoelastics:
            cfg = self.rtdc_ds.config
            self.isoelastics = pipeline_plot.add_isoelastics(
                plot_item=self.plotItem,
                axis_x=self.xax,
                axis_y=self.yax,
                channel_width=cfg["setup"]["channel width"],
                pixel_size=cfg["imaging"]["pixel size"])

    def set_mouse_click_mode(self, mode):
        allowed = ["scatter", "poly-create", "poly-modify"]
        if mode not in allowed:
            raise ValueError("Invalid mouse mode: {}, ".format(mode)
                             + "expected one of {}".format(allowed))
        if mode in ["poly-create", "poly-modify"]:
            if self.poly_line_roi is None:
                raise ValueError("Please set self.poly_line_roi before "
                                 + "setting the click mode!")
        self._view_box.mode = mode

    def setSelection(self, event_index):
        x = self.data_x[event_index]
        y = self.data_y[event_index]
        # workaround, because ScatterPlotItem does somehow not support
        # logarithmic scaling. Surprisingly, this works very well when
        # the log-scaling is changed (data is rescaled).
        if self.xscale == "log":
            x = 10**x
        if self.yscale == "log":
            y = 10**y
        self.select.setData([x], [y])


class QuickViewViewBox(SimpleViewBox):
    set_scatter_point = QtCore.pyqtSignal(QtCore.QPointF)
    add_poly_vertex = QtCore.pyqtSignal(QtCore.QPointF)

    #: allowed right-click menu options with new name
    right_click_actions = {"Export...": "Advanced Export",
                           "View All": "View All Content",
                           "Mouse Mode": "Change Mouse mode",
                           }

    def __init__(self, *args, **kwds):
        super(QuickViewViewBox, self).__init__(*args, **kwds)
        self.mode = "scatter"

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            pos = self.mapToView(ev.pos())
            if self.mode == "scatter":
                self.set_scatter_point.emit(pos)
            elif self.mode == "poly-create":
                self.add_poly_vertex.emit(pos)
            ev.accept()
        else:
            # right mouse button shows menu
            super(QuickViewViewBox, self).mouseClickEvent(ev)


class RTDCScatterPlot(pg.ScatterPlotItem):
    def __init__(self, size=3, pen=pg.mkPen(color=(0, 0, 0, 0)),
                 brush=pg.mkBrush("k"),
                 *args, **kwargs):
        super(RTDCScatterPlot, self).__init__(size=size,
                                              pen=pen,
                                              brush=brush,
                                              symbol="s",
                                              *args,
                                              **kwargs)
        self.setData(x=range(10), y=range(10))

    def pointAt(self, pos):
        """Unlike `ScatterPlotItem.pointsAt`, return the closest point"""
        x = pos.x()
        y = pos.y()
        pw = self.pixelWidth()
        ph = self.pixelHeight()
        p = self.points()[0]
        d = np.inf
        for s in self.points():
            sp = s.pos()
            di = ((sp.x() - x)/pw)**2 + ((sp.y() - y)/ph)**2
            if di < d:
                p = s
                d = di
        return p

    def set_point(self, view_pos):
        pos = self.mapFromView(view_pos)
        pt = self.pointAt(pos)
        self.ptClicked = pt
        self.sigClicked.emit(self, self.ptClicked)

    def mouseClickEvent(self, ev):
        """Override that does not handle events"""
        ev.ignore()  # clicks are handles by CustomViewBox
