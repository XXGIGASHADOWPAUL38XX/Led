from frontend.components.elements.parameters import IntegerDial
import numpy as np

from config import FREQ_BINS
from frontend.components.elements.color_picker import ColorPicker
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class SingleColorNode(CNode):
    """Generate a uniform RGB strip for coloring a visualization.

    Inputs `color` (RGB tuple in [0, 255]) and `number_points` produce
    output `data` shaped (number_points, 3). Refreshes when either input changes."""

    nodeName = "SingleColor"

    def __init__(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        number_points: int = FREQ_BINS,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "color": {"io": "in"},
            "number_points": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)


        self.color = ColorPicker(self, "color", ElementValue(color))
        self.number_points = IntegerDial(self, 'number_points', 1, 4096, ElementValue(number_points))
        self.data = AnalysableElement(self, "data",
                                      ElementValue(np.zeros((int(self.number_points.value), 3), dtype=np.uint8)), y_max=255.0)

        self.color.valueChanged.connect(self._refresh_data)
        self.number_points.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        self.data.value = np.tile(
            self.color.value,
            self.number_points.value
        ).reshape(self.number_points.value, 3)
