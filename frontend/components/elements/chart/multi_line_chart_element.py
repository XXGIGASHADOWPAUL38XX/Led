import numpy as np

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, sip

from frontend.components.elements.chart.line_chart_element import LineChartElement


class MultiLineChartElement(LineChartElement):
    def __init__(self, *args, input_data: list[float], **kwargs) -> None:
        super().__init__(*args, input_data=0.0, **kwargs)
        self.input_data = input_data
        self.data = np.zeros((len(input_data), self.number_points))
        self.lines = []
        self.legend = None

    def draw(self):
        self.node.window = pg.GraphicsLayoutWidget(title=self.title)
        plot = self.node.window.addPlot()
        self.plot = plot
        plot.setMouseEnabled(x=False, y=False)
        plot.setMenuEnabled(False)
        plot.setYRange(self.y_min, self.y_max)
        plot.setLabel("left", self.left_label)
        plot.setLabel("bottom", self.bottom_label)
        plot.showGrid(x=True, y=True)
        self.legend = pg.LegendItem(colCount=1)
        self.node.window.addItem(self.legend, row=1, col=0)
        x = np.arange(self.number_points)
        self.lines = [
            plot.plot(x, data, pen=pg.mkPen(selector.color))
            for selector, data in zip(self.node.node_selectors, self.data)
        ]
        for index, line in enumerate(self.lines):
            line.setVisible(self.node.line_visibility[index])
        self.line = self.lines[0] if self.lines else None
        self.update_legend()
        self.node.window.setFixedSize(600, 260)
        self.node.window.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.node._elements_container.layout().addWidget(
            self.node.window,
            alignment=QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop,
        )
        self.node.window.show()
        return self.node.window

    def c_update(self):
        if not self.lines:
            return
        for index, value in enumerate(self.input_data):
            self.data[index] = np.roll(self.data[index], -1)
            self.data[index, -1] = value
            if not sip.isdeleted(self.lines[index]):
                self.lines[index].setPen(pg.mkPen(self.node.node_selectors[index].color))
                self.lines[index].setData(np.arange(self.number_points), self.data[index])
        self.update_legend()

    def update_legend(self):
        if self.legend is None:
            return
        self.legend.clear()
        for selector, line in zip(self.node.node_selectors, self.lines):
            element = selector.selected_element
            label = "null" if element is None else f"{element.node.name()}: {element.name}"
            self.legend.addItem(line, label)
