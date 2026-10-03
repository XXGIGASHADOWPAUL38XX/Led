import numpy as np

from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.chart.line_chart_element import LineChartElement
from frontend.components.elements.node_selector.chart_line_from_node import ChartLineNodeSelector
from frontend.components.elements.textedit import TextEdit
from frontend.nodes.visual.line_chart import LineChartNode


class SingleLineChartNode(LineChartNode):
    nodeName = "SingleLineChart"

    def __init__(
        self,
        node_selector=None,
        input_data=None,
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
        self.node_selector = node_selector or ChartLineNodeSelector(
            self,
            "node_selector",
            ElementValue(input_data),
            selection_nodes=self.get_flowchart_visible_nodes,
            link_terminal=False,
        )
        if self.node_selector not in self.elements:
            self.elements.append(self.node_selector)
        self.title = ElementValue(title)
        self.number_points = ElementValue(number_points)
        self.y_min = TextEdit(self, "y_min", ElementValue(y_min))
        self.y_max = TextEdit(self, "y_max", ElementValue(y_max))
        self.chart = LineChartElement(
            self,
            "chart",
            0.0,
            int(number_points),
            left_label,
            bottom_label,
            title,
            float(self.y_min.value),
            float(self.y_max.value),
            link_terminal=False,
            register_in_node=True,
        )

        self.y_min.valueChanged.connect(self.on_y_range_change)
        self.y_max.valueChanged.connect(self.on_y_range_change)

    def on_y_range_change(self):
        try:
            self.chart.y_min = float(self.y_min.value)
            self.chart.y_max = float(self.y_max.value)
        except (TypeError, ValueError):
            return
        if self.chart.line is not None:
            self.chart.line.getViewBox().setYRange(self.chart.y_min, self.chart.y_max)

    def draw(self):
        return self.chart.draw()

    def c_update(self):
        selected = self.node_selector.selected_element
        value = np.asarray(selected.value).reshape(-1) if selected is not None else np.zeros(0)
        self.chart.input_data = float(value[-1]) if value.size else 0.0
        return self.chart.c_update()
