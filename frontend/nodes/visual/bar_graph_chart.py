from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement, IntegerDial
import numpy as np

from backend.updatable.updatable import VisualUpdatable
from config import FREQ_BINS
from frontend.components.elements.chart.bar_graph_chart import BarGraphChartElement
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit.textedit import TextEdit
from frontend.overrides.CNode import CNode


class BarGraphChartNode(CNode, VisualUpdatable):
    """Display a vector as a colored bar chart.

    Inputs `data` (bar heights) and `brushes` (per-bar RGBA colors) feed a
    chart each visual update; no output terminals. Configure `number_points`,
    title, axis labels, and `y_min`/`y_max` for the displayed range."""

    nodeName = "BarGraphChart"

    def __init__(
        self,
        data: np.ndarray = np.zeros(FREQ_BINS),
        title: str = "Title",
        number_points: int = FREQ_BINS,
        left_label: str = "Left label",
        bottom_label: str = "Bottom label",
        brushes: np.ndarray | object = np.zeros((FREQ_BINS, 4)),
        y_min: int | float = 0.0,
        y_max: int | float = 90.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "brushes": {"io": "in"},
            "data": {"io": "in"},
        }
        super().__init__(node_name=self.nodeName, terminals=terminals, render=render, alias=alias)
        self.title = TextEdit(self, "title", ElementValue(title))

        self.number_points = IntegerDial(self, 'number_points', 1, 4096, ElementValue(number_points))
        self.brushes = DataElement(self, 'brushes', ElementValue(brushes))
        self.left_label = TextEdit(self, 'left_label', ElementValue(left_label))
        self.bottom_label = TextEdit(self, 'bottom_label', ElementValue(bottom_label))
        self.y_min = LinearDial(self, 'y_min', -10000, 10000, ElementValue(y_min))
        self.y_max = LinearDial(self, 'y_max', -10000, 10000, ElementValue(y_max))
        self.data = DataElement(self, 'data', ElementValue(data))
        self.chart = BarGraphChartElement(
            self,
            "chart",
            data=self.data.value,
            number_points=self.number_points.value,
            left_label=self.left_label.value,
            bottom_label=self.bottom_label.value,
            brushes=self.brushes.value,
            y_min=float(self.y_min.value),
            y_max=float(self.y_max.value),
            title=self.title.value,
            link_terminal=False,
            register_in_node=True,
        )
        self.y_min.valueChanged.connect(self.on_y_range_change)
        self.y_max.valueChanged.connect(self.on_y_range_change)
        if render:
            self.draw()
            self.chart.chart_button.setChecked(True)

    def draw(self):
        return self.chart.draw()

    def on_y_range_change(self):
        try:
            self.chart.y_min = float(self.y_min.value)
            self.chart.y_max = float(self.y_max.value)
        except (TypeError, ValueError):
            return
        if self.chart.spectrogram is not None:
            self.chart.spectrogram.getViewBox().setYRange(self.chart.y_min, self.chart.y_max)

    def c_update(self):
        self.chart.data = self.data.value
        self.chart.brushes = self.brushes.value
        return self.chart.c_update()
