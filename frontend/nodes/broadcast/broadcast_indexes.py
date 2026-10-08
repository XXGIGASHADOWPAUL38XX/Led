import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class BroadcastIndexesNode(CNode, AudioUpdatable):
    """Sample a vector using normalized positions.

    Inputs `input_data` (1D) and `indexes` produce output `data` with the
    indexes shape. Each audio update converts indexes * source length to
    integers and clamps them to valid positions; use indexes in [0, 1]."""

    nodeName = "BroadcastIndexesNode"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        indexes: np.ndarray = np.zeros(FREQ_BINS),
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "indexes": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_data = Element(self, "input_data", ElementValue(input_data))
        self.indexes = Element(self, "indexes", ElementValue(indexes))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.indexes.value, dtype=float)))
        self.current_indexes = np.empty_like(self.indexes.value, dtype=np.int16)

    def c_update(self):
        input_data = self.input_data.value
        indexes = self.indexes.value
        size = input_data.shape[-1]

        np.multiply(indexes, size, out=self.current_indexes, casting="unsafe")
        np.clip(self.current_indexes, 0, size - 1, out=self.current_indexes)
        self.data.value[...] = input_data[self.current_indexes]
