from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement, IntegerDial, IntegerExpDial, SequenceElement
import numpy as np
from config import FREQ_BINS

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class WindowNode(CNode, AudioUpdatable):
    """Keep recent vector frames for temporal aggregation.

    Input `input_data` shaped (N,) produces output `data` shaped (length, N),
    oldest to newest. Configure positive integer `length`, initial
    `init_value`, and nonnegative `offset` in audio updates. Each update
    appends one delayed frame and calls registered window functions."""

    nodeName = "Window"

    def __init__(
        self,
        input_data: np.ndarray | object = np.zeros(FREQ_BINS),
        length: int | float = 1,
        init_value: float = 0.0,
        offset: int = 0,
        render: bool = True,
        alias: str | None = None,
            parent: CNode | None = None,
    ) -> None:
        self.should_process = False
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"}
        }

        super().__init__(self.nodeName, terminals, render=render, alias=alias, parent=parent)

        self.length = IntegerExpDial(self, "length", 1, 1000, ElementValue(length))
        self.input_data = DataElement(self, 'input_data', ElementValue(input_data)) # Data to aggregate
        self.offset = IntegerDial(self, 'offset', 0, 1000, ElementValue(offset))
        self.init_value = LinearDial(self, "init_value", -100, 100, init_value)
        input_shape = self.input_data.value.shape[0]
        self.data = AnalysableElement(self, "data", ElementValue((np
                                                                  .repeat(init_value, self.length.value * input_shape)
                                                                  .reshape(self.length.value, input_shape))
                                                                 ))
        self._offset_buffer = []
        self.window_fcts = SequenceElement(self, 'window_fcts', ElementValue([]))

        self.length.valueChanged.connect(self.on_length_change)
        self.should_process = True

    def on_length_change(self):
        self.should_process = False

        input_shape = self.input_data.value.shape[0]
        int_length = int(self.length.value)
        self.data.value = np.repeat(0.0, int_length * input_shape).reshape(int_length, input_shape)

        self.should_process = True

    def c_update(self):
        if not self.should_process:
            return
        input_shape = self.input_data.value.shape[0]
        if self.data.value.shape[0] != int(self.length.value) or self.data.value.shape[1] != input_shape:
            self._resize_data(input_shape)
        offset = int(self.offset.value)
        if offset:
            self._offset_buffer.append(self.input_data.value.copy())
            input_data = self._offset_buffer.pop(0) if len(self._offset_buffer) > offset else np.zeros_like(self.input_data.value)
        else:
            self._offset_buffer.clear()
            input_data = self.input_data.value
        self.roll(input_data)
        for window_fct in self.window_fcts.value:
            window_fct.aggregate(self.data.value)

    def roll(self, input_data):
        try:
            self.data.value[:] = np.roll(self.data.value, -1, axis=0)
            self.data.value[-1] = input_data
        except (IndexError, ValueError):
            pass
