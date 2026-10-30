from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue

from backend.overrides.CNode import CNode

class AmplitudesLevelFunction(CNode, AudioUpdatable):
    """Provide a frequency-index gain curve to an amplitude transformer.

    Configure `number_points`, `offset`, and sigmoid `drop`/`rise` magnitudes,
    centers, and widths. Calling `fct(amplitudes_data)` multiplies a matching
    vector by the curve and returns `data` shaped (number_points,).
    Processing requires a caller; the declared data terminal is not linked."""

    nodeName = "AmplitudeLevelFunction"

    def __init__(
        self,
        number_points: int,
        offset: float = 0.85,
        drop: float = 0.6,
        drop_center: int = 75,
        drop_width: int = 10,
        rise: float = 0.15,
        rise_center: int = 225,
        rise_width: int = 10,

    ) -> None:
        terminals = {
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals)

        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.arange = DataElement(self, 'arange', ElementValue(np.arange(number_points)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(number_points)))

        self.offset = Parameter(self, 'offset', offset, minimum=0.0, maximum=1.5)

        self.drop = Parameter(self, 'drop', drop, minimum=0.0, maximum=1.0)
        self.drop_center = Parameter(self, 'drop_center', drop_center, minimum=0, maximum=number_points // 2, integer=True)
        self.drop_width = Parameter(self, 'drop_width', drop_width, minimum=1, maximum=max(10, number_points // 5), integer=True)

        self.rise = Parameter(self, 'rise', rise, minimum=0.0, maximum=0.5)
        self.rise_center = Parameter(self, 'rise_center', rise_center, minimum=number_points // 2, maximum=number_points, integer=True)
        self.rise_width = Parameter(self, 'rise_width', rise_width, minimum=1, maximum=max(10, number_points // 5), integer=True)

    def fct(self, amplitudes_data):
        self.data.value[:] = amplitudes_data * (
            self.offset.value
            - self.drop.value / (1 + np.exp(-(self.arange.value - self.drop_center.value) / self.drop_width.value))
            + self.rise.value / (1 + np.exp(-(self.arange.value - self.rise_center.value) / self.rise_width.value))
        )
        return self.data.value
