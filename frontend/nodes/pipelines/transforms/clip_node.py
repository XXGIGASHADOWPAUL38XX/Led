import numpy as np

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class ClipNode(CNode, AudioUpdatable):
    """Clamp an array to a fixed numeric range.

    Input `input_value` produces output `data` with the same shape each audio
    update. Configure `min_value` and `max_value`; values outside the range
    become the nearest bound."""

    nodeName = "Clip"

    def __init__(
        self,
        input_value: np.ndarray = np.zeros(0),
        min_value: float = 0.0,
        max_value: float = 1.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_value = Element(self, "input_value", ElementValue(input_value))
        self.min_value = TextEdit(self, "min_value", ElementValue(min_value))
        self.max_value = TextEdit(self, "max_value", ElementValue(max_value))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros_like(self.input_value.value)), y_min=min_value, y_max=max_value)

    def c_update(self):
        if self.data.value.shape != self.input_value.value.shape:
            self.data.value = np.zeros_like(self.input_value.value)
        self.data.value[:] = np.clip(
            self.input_value.value,
            float(self.min_value.value),
            float(self.max_value.value),
        )
