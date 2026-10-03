import numpy as np

from config import FREQ_BINS
from frontend.components.elements.analysable_element import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class SinArrayNode(CNode):
    nodeName = "SinArray"

    def __init__(
        self,
        number_cycle: float = 2,
        number_points: int = FREQ_BINS,
        center: float = 0.5,
        offset: float = 0.1,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "number_cycle": {"io": "in"},
            "number_points": {"io": "in"},
            "center": {"io": "in"},
            "offset": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.number_cycle = Element(self, "number_cycle", ElementValue(number_cycle))
        self.number_points = Element(self, "number_points", ElementValue(number_points))
        self.center = Element(self, "center", ElementValue(center))
        self.offset = Element(self, "offset", ElementValue(offset))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.number_points.value))), y_min=min(0.0, center - abs(offset)), y_max=max(1.0, center + abs(offset)))

        self.number_cycle.valueChanged.connect(self._refresh_data)
        self.number_points.valueChanged.connect(self._refresh_data)
        self.center.valueChanged.connect(self._refresh_data)
        self.offset.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        target_len = int(self.number_points.value)
        if target_len <= 0:
            self.data.value = np.zeros(max(0, target_len))
            return

        x = np.linspace(0, 2 * np.pi * float(self.number_cycle.value), target_len, endpoint=False)
        self.data.value = self.center.value + (self.offset.value * np.sin(x))
