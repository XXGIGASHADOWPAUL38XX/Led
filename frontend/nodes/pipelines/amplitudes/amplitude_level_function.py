import numpy as np

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.dials import LinearDial
from frontend.overrides.CNode import CNode


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
        render: bool = True
    ) -> None:
        terminals = {
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render)

        self.arange = Element(self, "arange", ElementValue(np.arange(number_points)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(number_points)), link_terminal=False, y_min=-1.0, y_max=2.0)

        self.offset = LinearDial(self, "offset", 0.0, 1.5, offset)

        self.drop = LinearDial(self, "drop", 0.0, 1.0, drop)
        self.drop_center = LinearDial(self, "drop_center", 0, number_points // 2, drop_center)
        self.drop_width = LinearDial(self, "drop_width", 1, max(10, number_points // 5), drop_width)

        self.rise = LinearDial(self, "rise", 0.0, 0.5, rise)
        self.rise_center = LinearDial(self, "rise_center", number_points // 2, number_points, rise_center)
        self.rise_width = LinearDial(self, "rise_width", 1, max(10, number_points // 5), rise_width)

    def fct(self, amplitudes_data):
        self.data.value[:] = amplitudes_data * (
            self.offset.value
            - self.drop.value / (1 + np.exp(-(self.arange.value - self.drop_center.value) / self.drop_width.value))
            + self.rise.value / (1 + np.exp(-(self.arange.value - self.rise_center.value) / self.rise_width.value))
        )
        return self.data.value
