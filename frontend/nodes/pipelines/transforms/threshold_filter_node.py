import numpy as np

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class ThresholdFilterNode(CNode, AudioUpdatable):
    """Suppress array values below a threshold.

    Inputs `input_value` and scalar `threshold` produce same-shaped output
    `data` each audio update. Values below threshold become zero; values at
    or above threshold are retained."""

    nodeName = "ThresholdFilter"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        threshold: float = 0.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "threshold": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_value = Element(self, "input_value", ElementValue(input_value))
        self.threshold = TextEdit(self, "threshold", ElementValue(threshold))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)))

    def c_update(self):
        values = np.asarray(self.input_value.value)
        if self.data.value.shape != values.shape:
            self.data.value = np.zeros_like(values)

        self.data.value[:] = values
        self.data.value[values < float(self.threshold.value)] = 0
