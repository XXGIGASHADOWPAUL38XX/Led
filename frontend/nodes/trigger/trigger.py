from frontend.components.elements.dials import LinearDial
from frontend.components.elements.parameters import DataElement, EnumElement
import numpy as np

from config import FREQ_BINS
from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.enums.gradiant.trigger_mode import TriggerMode
from frontend.overrides.CNode import CNode


class TriggerNode(CNode, AudioUpdatable):
    """Emit a one-update pulse when the last input value crosses a condition.

    Inputs `input_data` and `threshold` use configured `trigger_mode` LESS,
    EQUAL, or GREATER. Output `data` is a vector matching input's last-axis
    length: all ones when the condition changes to true, zeros otherwise.
    Samples the final flattened input value each audio update."""

    nodeName = "Trigger"

    @classmethod
    def condition_check(cls, trigger_mode, threshold, value):
        condition_check_dict = {
            TriggerMode.LESS: lambda x: x < threshold,
            TriggerMode.EQUAL: lambda x: x == threshold,
            TriggerMode.GREATER: lambda x: x > threshold,
        }

        return condition_check_dict[trigger_mode](value)

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        trigger_mode: TriggerMode = TriggerMode.EQUAL,
        threshold: float = 0.5,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "threshold": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.trigger_mode = EnumElement(self, "trigger_mode", ElementValue(trigger_mode))
        self.threshold = LinearDial(self, 'threshold', -100, 100, ElementValue(threshold))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.input_data.value.shape[-1])))
        self.block_signal = ElementValue(False)

    def c_update(self) -> None:
        input_value = np.asarray(self.input_data.value)
        value = float(np.ravel(input_value)[-1]) if input_value.size else 0.0
        condition_value = self.condition_check(self.trigger_mode.value, self.threshold.value, value)
        if condition_value != self.block_signal.value:
            self.data.value[:] = np.ones(self.data.value.shape) * int(condition_value)
            self.block_signal.value = condition_value
        else:
            self.data.value[:] = np.zeros(self.data.value.shape)
