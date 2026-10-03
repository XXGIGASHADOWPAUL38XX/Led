import numpy as np

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class PeakFilterNode(CNode, AudioUpdatable):
    nodeName = "PeakFilter"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        peaks_to_keep: int = 20,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_value = Element(self, "input_value", ElementValue(input_value))
        self.peaks_to_keep = TextEdit(self, "peaks_to_keep", ElementValue(peaks_to_keep))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)))

    def c_update(self):
        # Keep spikes
        values = np.asarray(self.input_value.value)
        if self.data.value.shape != values.shape:
            self.data.value = np.zeros_like(values)
        self.data.value[:] = values

        mask = np.zeros(values.shape, dtype=bool)
        mask[1:] |= values[1:] < values[:-1]
        mask[:-1] |= values[:-1] < values[1:]
        self.data.value[:] = self.input_value.value
        self.data.value[mask] = 0

        # Keep top n spikes
        values = self.data.value
        peak_count = min(int(self.peaks_to_keep.value), values.size)
        if peak_count == 0:
            self.data.value[:] = 0
            return

        keep = np.argsort(values)[-peak_count:]
        mask = np.ones(values.shape, dtype=bool)
        mask[keep] = False
        self.data.value[mask] = 0
