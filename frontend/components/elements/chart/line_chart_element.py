import numpy as np

import pyqtgraph as pg
from PyQt5 import sip

from frontend.components.elements.chart.chart_element import ChartElement


class LineChartElement(ChartElement):
    def __init__(
        self,
        node,
        name: str,
        input_data: float,
        number_points: int,
        left_label: str,
        bottom_label: str,
        title: str,
        y_min: float = 0.0,
        y_max: float = 1.0,
        link_terminal: bool = True,
        register_in_node: bool = True,
        show_chart_button: bool = True,
    ) -> None:
        self.input_data = input_data
        self.number_points = number_points
        self.data = np.zeros(number_points)
        self.left_label = left_label
        self.bottom_label = bottom_label
        self.title = title
        self.y_min = y_min
        self.y_max = y_max
        self.line = None
        super().__init__(
            node,
            name,
            link_terminal=link_terminal,
            register_in_node=register_in_node,
            show_chart_button=show_chart_button,
        )

    def draw(self):
        self.window = pg.GraphicsLayoutWidget(title=self.title)
        plot = self.window.addPlot()
        plot.setYRange(self.y_min, self.y_max)
        plot.setLabel("left", self.left_label)
        plot.setLabel("bottom", self.bottom_label)
        plot.showGrid(x=True, y=True)
        x = np.arange(self.number_points)
        values = np.asarray(self.input_data).reshape(-1) if isinstance(self.input_data, np.ndarray) else np.zeros(self.number_points)
        self.line = plot.plot(x, values if values.size == self.number_points else np.zeros(self.number_points), pen="b")
        self.window.setFixedSize(500, 150)
        self.node._elements_container.layout().addWidget(self.window)
        self.window.show()
        return self.window

    def c_update(self):
        if self.line is None:
            return
        if sip.isdeleted(self.line):
            self.line = None
            return
        if isinstance(self.input_data, np.ndarray):
            self.line.setData(np.arange(self.input_data.size), self.input_data)
            return
        self.data[:] = np.roll(self.data, -1)
        self.data[-1] = self.input_data
        self.line.setData(np.arange(len(self.data)), self.data)

    def set_input_data(self, value):
        self.input_data = value
        self.c_update()
