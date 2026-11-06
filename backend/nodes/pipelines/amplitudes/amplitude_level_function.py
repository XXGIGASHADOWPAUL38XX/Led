from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from config import FREQ_BINS

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue

from backend.overrides.CNode import CNode

class AmplitudesLevelFunction(CNode):
    """Provide a frequency-index gain curve to an amplitude transformer.

    Configure `number_points`, `offset`, and sigmoid `drop`/`rise` magnitudes,
    centers, and widths. Output `data` is the gain curve shaped
    (number_points,), regenerated on parameter changes. Calling
    `fct(amplitudes_data)` returns a matching vector multiplied by the curve
    without changing the curve itself."""

    nodeName = "AmplitudeLevelFunction"
    ui = {
        "title": "Amplitude Level Function",
        "description": "Provide a frequency-index gain curve to an amplitude transformer.",
        "category": "amplitudes",
        "fields": [
            {"name": "number_points", "control": "slider", "label": "Points", "rebuild": True},
            {"name": "offset", "control": "slider"},
            {"name": "drop", "control": "slider"},
            {
                "name": "drop_center",
                "control": "slider",
                "bounds": {"from": "number_points", "min": 0, "max": 0.5},
            },
            {"name": "drop_width", "control": "slider"},
            {"name": "rise", "control": "slider"},
            {
                "name": "rise_center",
                "control": "slider",
                "bounds": {"from": "number_points", "min": 0.5, "max": 1},
            },
            {"name": "rise_width", "control": "slider"},
        ],
        "views": [{"kind": "bars", "data": "data", "label": "Data", "open": True}],
    }

    def __init__(
        self,
        number_points: int = FREQ_BINS,
        offset: float = 0.85,
        drop: float = 0.6,
        drop_center: int | None = None,
        drop_width: int = 10,
        rise: float = 0.15,
        rise_center: int | None = None,
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
        self.drop_center = Parameter(self, 'drop_center', number_points // 4 if drop_center is None else drop_center, minimum=0, maximum=number_points // 2, integer=True)
        self.drop_width = Parameter(self, 'drop_width', drop_width, minimum=1, maximum=max(10, number_points // 5), integer=True)

        self.rise = Parameter(self, 'rise', rise, minimum=0.0, maximum=0.5)
        self.rise_center = Parameter(self, 'rise_center', number_points * 3 // 4 if rise_center is None else rise_center, minimum=number_points // 2, maximum=number_points, integer=True)
        self.rise_width = Parameter(self, 'rise_width', rise_width, minimum=1, maximum=max(10, number_points // 5), integer=True)

        for parameter in (self.number_points, self.offset, self.drop, self.drop_center,
                          self.drop_width, self.rise, self.rise_center, self.rise_width):
            parameter.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args):
        self.arange.value = np.arange(self.number_points.value)
        self.data.value = (
            self.offset.value
            - self.drop.value / (1 + np.exp(-(self.arange.value - self.drop_center.value) / self.drop_width.value))
            + self.rise.value / (1 + np.exp(-(self.arange.value - self.rise_center.value) / self.rise_width.value))
        )

    def fct(self, amplitudes_data):
        return amplitudes_data * self.data.value
