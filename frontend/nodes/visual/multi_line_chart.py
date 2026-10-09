from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import IntegerDial, SequenceElement
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, sip

from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.chart.multi_line_chart_element import MultiLineChartElement
from frontend.components.elements.node_selector.chart_line_from_node import ChartLineNodeSelector
from frontend.components.elements.textedit.textedit import TextEdit
from frontend.nodes.visual.line_chart import LineChartNode


class MultiLineChartNode(LineChartNode):
    """Plot several selected Elements as separate scalar histories.

    Configure `node_selectors`, `number_points`, title, labels, and y bounds.
    Each visual update samples the last flattened value from each selected
    Element, or zero if absent. Lines can be added or hidden through the UI;
    there are no graph terminals."""

    nodeName = "MultiLineChart"

    def __init__(
        self,
        node_selectors=None,
        title="Title",
        number_points=100,
        left_label="Left label",
        bottom_label="Time",
        y_min=0.0,
        y_max=1.0,
        render=True,
        alias=None,
    ):
        super().__init__(self.nodeName, terminals={}, render=render, alias=alias)
        self.title = TextEdit(self, "title", ElementValue(title))
        selector_values = node_selectors or [None]
        self.node_selectors = SequenceElement(self, "node_selectors", [
            ChartLineNodeSelector(
                self,
                f"node_selector_{index}",
                ElementValue(value),
                selection_nodes=self.get_flowchart_visible_nodes,
                link_terminal=False,
            )
        for index, value in enumerate(selector_values)
        ], link_terminal=False, register_in_node=False)
        self.line_visibility = [True] * len(self.node_selectors)
        for index, selector in enumerate(self.node_selectors):
            self._add_visibility_button(index, selector)
        self.add_selector_button = QtWidgets.QPushButton("Add node selector")
        self.add_selector_button.clicked.connect(self.add_node_selector)
        self.number_points = IntegerDial(self, 'number_points', 1, 4096, ElementValue(number_points))
        self.left_label = TextEdit(self, 'left_label', ElementValue(left_label))
        self.bottom_label = TextEdit(self, 'bottom_label', ElementValue(bottom_label))
        self.y_min = LinearDial(self, 'y_min', -10000, 10000, ElementValue(y_min))
        self.y_max = LinearDial(self, 'y_max', -10000, 10000, ElementValue(y_max))
        self.chart = MultiLineChartElement(
            self,
            "chart",
            input_data=[0.0] * len(self.node_selectors),
            number_points=self.number_points.value,
            left_label=self.left_label.value,
            bottom_label=self.bottom_label.value,
            title=self.title.value,
            y_min=float(self.y_min.value),
            y_max=float(self.y_max.value),
            link_terminal=False,
            register_in_node=False,
        )
        self.y_min.valueChanged.connect(self.on_y_range_change)
        self.y_max.valueChanged.connect(self.on_y_range_change)
        if render:
            QtCore.QTimer.singleShot(0, self.draw)

    def init_all(self):
        super().init_all()
        self._elements_container.layout().insertWidget(len(self.node_selectors), self.add_selector_button)

    def add_node_selector(self):
        selector = ChartLineNodeSelector(
            self,
            f"node_selector_{len(self.node_selectors)}",
            ElementValue(None),
            selection_nodes=self.get_flowchart_visible_nodes,
            link_terminal=False,
        )
        self.node_selectors.append(selector)
        self.line_visibility.append(True)
        self._add_visibility_button(len(self.node_selectors) - 1, selector)
        self.elements.insert(len(self.node_selectors) - 1, selector)
        self._elements_container.layout().insertWidget(len(self.node_selectors) - 1, selector)
        self.chart.input_data.append(0.0)
        self.chart.data = np.vstack((self.chart.data, np.zeros(self.chart.number_points)))
        if self.chart.lines:
            x = np.arange(self.chart.number_points)
            self.chart.lines.append(self.chart.plot.plot(x, self.chart.data[-1], pen=pg.mkPen(selector.color)))
        self.chart.update_legend()

    def _add_visibility_button(self, index, selector):
        button = QtWidgets.QToolButton()
        button.setCheckable(True)
        button.setChecked(True)
        button.setText("●")
        button.setToolTip("Show/hide curve")
        button.toggled.connect(lambda visible: self.set_line_visibility(index, visible))
        selector.controls_layout.addWidget(button)

    def set_line_visibility(self, index, visible):
        self.line_visibility[index] = visible
        if index < len(self.chart.lines):
            self.chart.lines[index].setVisible(visible)

    def draw(self):
        return self.chart.draw()

    def on_y_range_change(self):
        try:
            self.chart.y_min = float(self.y_min.value)
            self.chart.y_max = float(self.y_max.value)
        except (TypeError, ValueError):
            return
        if self.chart.line is not None:
            self.chart.line.getViewBox().setYRange(self.chart.y_min, self.chart.y_max)

    def c_update(self):
        self.chart.input_data = [
            float(np.asarray(selector.selected_element.value).reshape(-1)[-1])
            if selector.selected_element is not None and np.asarray(selector.selected_element.value).size else 0.0
            for selector in self.node_selectors
        ]
        return self.chart.c_update()
