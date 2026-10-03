import numpy as np
from PyQt5 import QtCore, QtWidgets

from frontend.components.elements.element import Element
from frontend.components.elements.textedit import TextEdit
from frontend.components.elements.chart.line_chart_element import LineChartElement
from frontend.components.elements.chart.bar_graph_chart import BarGraphChartElement

class AnalysableElement(Element):
    _refresh_timer = None

    def __init__(self, *args, chart_open: bool | None = None, y_min: float = 0.0, y_max: float = 1.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.y_min = TextEdit(self.node, "y_min", y_min, link_terminal=False, register_in_node=False)
        self.y_max = TextEdit(self.node, "y_max", y_max, link_terminal=False, register_in_node=False)
        self._analysis_chart = None
        self._analysis_chart_is_line = None
        self.analysis_button = None
        if not isinstance(self.value, np.ndarray):
            raise TypeError("Analysable element should be array")
        self.analysis_button = QtWidgets.QToolButton()
        self.analysis_button.setText("📈")
        self.analysis_button.setCheckable(True)
        self.analysis_button.setToolTip("Show data over time")
        self.analysis_button.toggled.connect(self._toggle_analysis_chart)
        self.container_vchange_layout.addWidget(self.analysis_button)
        if chart_open is None:
            chart_open = self.value.size == 1
        QtCore.QTimer.singleShot(0, lambda: self._initialize_analysis_chart(chart_open))

    def _initialize_analysis_chart(self, open):
        value = np.asarray(self.value)
        if value.ndim not in (1, 2) or value.size == 0:
            return
        self._analysis_chart_is_line = value.size == 1

        if self._analysis_chart_is_line:
            self._analysis_chart = LineChartElement(
                self.node,
                f"{self.name}_chart",
                float(value.reshape(-1)[-1]),
                100,
                "Value",
                "Time",
                self.name,
                y_min=float(self.y_min.value),
                y_max=float(self.y_max.value),
                link_terminal=False,
                register_in_node=False,
                show_chart_button=False,
            )
        else:
            self._analysis_chart = BarGraphChartElement(
                self.node,
                f"{self.name}_chart",
                value.reshape(-1),
                value.size,
                "Value",
                "Index",
                None,
                float(self.y_min.value),
                float(self.y_max.value),
                self.name,
                link_terminal=False,
                register_in_node=False,
                show_chart_button=False,
            )

        self.node._elements_container.layout().insertWidget(
            self.node._elements_container.layout().indexOf(self) + 1,
            self._analysis_chart,
        )
        layout = self.node._elements_container.layout()
        for offset, control in enumerate((self.y_min, self.y_max), start=1):
            layout.insertWidget(layout.indexOf(self._analysis_chart) + offset, control)
            control.valueChanged.connect(self._update_y_range)
        if AnalysableElement._refresh_timer is None:
            AnalysableElement._refresh_timer = QtCore.QTimer(QtWidgets.QApplication.instance())
            AnalysableElement._refresh_timer.start(50)
        AnalysableElement._refresh_timer.timeout.connect(self._update_analysis_chart)
        self._analysis_chart.draw()
        self._analysis_chart.window.setFixedSize(500, 150)
        plot = self._analysis_chart.window.getItem(0, 0)
        plot.setMouseEnabled(x=False, y=False)
        plot.setMenuEnabled(False)
        self._update_y_range()
        self.analysis_button.setChecked(open)
        self._toggle_analysis_chart(open)

    def _toggle_analysis_chart(self, visible):
        if self._analysis_chart is None:
            return
        self._analysis_chart.setVisible(visible)
        self._analysis_chart.window.setVisible(visible)
        self.y_min.setVisible(visible)
        self.y_max.setVisible(visible)

    def _update_y_range(self):
        try:
            y_min = float(self.y_min.value)
            y_max = float(self.y_max.value)
        except (TypeError, ValueError):
            return
        if not np.isfinite(y_min) or not np.isfinite(y_max) or y_min >= y_max:
            return
        self._analysis_chart.y_min = y_min
        self._analysis_chart.y_max = y_max
        self._analysis_chart.window.getItem(0, 0).setYRange(y_min, y_max, padding=0)

    def _update_analysis_chart(self):
        if not self._analysis_chart.window.isVisible():
            return
        value = np.asarray(self.value)
        if value.size:
            if self._analysis_chart_is_line:
                self._analysis_chart.set_input_data(float(value.reshape(-1)[-1]))
            else:
                self._analysis_chart.data = value.reshape(-1)
                self._analysis_chart.c_update()
