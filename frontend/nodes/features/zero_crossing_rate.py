import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class ZeroCrossingRateNode(CNode, AudioPipeline):
    """nodeName labels the graph node; this node outputs the average waveform sign-change rate."""

    nodeName = "ZeroCrossingRate"

    def __init__(self, buffer_data=np.zeros((2, 0)), render: bool = True, alias: str | None = None) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))

    def c_update(self):
        data = np.asarray(self.buffer_data.value, dtype=float)
        if data.shape[1] < 2:
            self.data.value[...] = 0.0
            return
        signs = np.signbit(data)
        crossings = np.count_nonzero(signs[:, 1:] != signs[:, :-1], axis=1)
        self.data.value[...] = np.mean(crossings / (data.shape[1] - 1))
