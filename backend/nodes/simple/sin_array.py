from backend.components.elements.parameters import Parameter
import numpy as np

from config import FREQ_BINS
from backend.components.elements.analysable_element import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class SinArrayNode(CNode):
    """Generate a sampled sine wave for spatial modulation.

    Inputs `number_cycle`, `number_points`, `center`, and `offset` control
    cycles, length, baseline, and amplitude. Output `data` has shape
    (number_points,) and refreshes on changes; the endpoint is excluded."""

    nodeName = "SinArray"

    def __init__(
        self,
        number_cycle: float = 2,
        number_points: int = FREQ_BINS,
        center: float = 0.5,
        offset: float = 0.1,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "number_cycle": {"io": "in"},
            "number_points": {"io": "in"},
            "center": {"io": "in"},
            "offset": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.number_cycle = Parameter(self, 'number_cycle', number_cycle, minimum=0, maximum=20)
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.center = Parameter(self, 'center', center, minimum=-1, maximum=1)
        self.offset = Parameter(self, 'offset', offset, minimum=-1, maximum=1)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.number_points.value))))

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
