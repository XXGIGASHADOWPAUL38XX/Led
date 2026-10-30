from backend.components.elements.parameters import Parameter
import numpy as np

from config import FREQ_BINS

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class SingleColorNode(CNode):
    """Generate a uniform RGB strip for coloring a visualization.

    Inputs `color` (RGB tuple in [0, 255]) and `number_points` produce
    output `data` shaped (number_points, 3). Refreshes when either input changes."""

    nodeName = "SingleColor"

    def __init__(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        number_points: int = FREQ_BINS,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "color": {"io": "in"},
            "number_points": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.color = Parameter(self, 'color', color, kind='color')
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.data = AnalysableElement(self, "data",
                                      ElementValue(np.zeros((int(self.number_points.value), 3), dtype=np.uint8)))

        self.color.valueChanged.connect(self._refresh_data)
        self.number_points.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        self.data.value = np.tile(
            self.color.value,
            self.number_points.value
        ).reshape(self.number_points.value, 3)
