from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import FREQ_BINS
from frontend.components.elements import Interval, AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class BroadcastFractionNode(CNode, AudioUpdatable):
    """Select a movable contiguous slice along the first array axis.

    Inputs `input_data`, `input`, and `interval_input` define the source and
    position; configure `fraction` as the retained proportion (0 to 1).
    Output `data` preserves trailing dimensions. Each audio update clamps
    the normalized position to [0, 1]; interval endpoints must differ."""

    nodeName = "BroadcastFractionNode"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        fraction: float = 1.,
        interval_input: tuple[int, int] = (0, 1),
        input: float = 1,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "interval_input": {"io": "in"},
            "input": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.fraction = LinearDial(self, 'fraction', 0, 1, ElementValue(fraction))
        self.interval_input = Interval(self, "interval_input", ElementValue(interval_input))
        self.input = LinearDial(self, 'input', 0, 1, ElementValue(input))

        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self._data_shape())))
        
        self.fraction.valueChanged.connect(self.on_fraction_change)

    def _data_shape(self):
        return (
            int(round(self.input_data.value.shape[0] * float(self.fraction.value))),
            *self.input_data.value.shape[1:],
        )

    def on_fraction_change(self):
        try:
            if isinstance(self.fraction.value, str):
                self.fraction.value = float(self.fraction.value)
        except (TypeError, ValueError):
            self.fraction.value = 1.
        self.data.value = np.zeros(self._data_shape())

    def c_update(self):
        if self.data.value.shape != self._data_shape():
            self.data.value = np.zeros(self._data_shape())

        scale_position = np.clip(
            (self.input.value - self.interval_input.value[0]) / (self.interval_input.value[1] - self.interval_input.value[0]),
            0,
            1
        )

        window_length = int(self.fraction.value * self.input_data.value.shape[0])
        c = int(((1 - self.fraction.value) * scale_position * self.input_data.value.shape[0]).item())
        self.data.value[:] = self.input_data.value[c:c+window_length]
