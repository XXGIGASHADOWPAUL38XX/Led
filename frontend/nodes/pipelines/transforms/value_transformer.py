import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.interval import Interval
from frontend.overrides.CNode import CNode


class ValueTransformerPipelineNode(CNode, AudioPipeline):
    """Map scalar or vector values between numeric intervals.

    Input `input_value` produces output `output_value` each audio update.
    Configure ascending `input_value_interval` and `output_value_interval`;
    linear interpolation clamps out-of-range inputs to endpoint outputs.
    A scalar produces a one-element array; use 1D arrays for vector input."""

    nodeName = "ValueTransformer"

    @staticmethod
    def _compute_input_interval(values):
        min_value = float(np.min(values))
        max_value = float(np.max(values))
        if min_value == max_value:
            max_value += 1e-12
        return [min_value, max_value]

    @staticmethod
    def _compute_input_value_shape(value):
        if isinstance(value, np.ndarray):
            return value.shape[-1]
        if isinstance(value, (float, int)):
            return 1
        raise TypeError(f"Unsupported input value type: {type(value).__name__}")

    def __init__(
            self,
            input_value: np.ndarray = np.zeros(1),
            output_value_interval: tuple[int | float, int | float] = (0, 1),
            input_value_interval: tuple[int | float, int | float] = (0, 1),
            render: bool = True,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "output_value": {"io": "out"},
        }

        super().__init__(node_name=self.nodeName, terminals=terminals, render=render, alias=alias)

        self.input_value = Element(self, "input_value", ElementValue(input_value))
        self.input_value_interval = Interval(self, "input_value_interval", ElementValue(input_value_interval))
        self.output_value_interval = Interval(self, "output_value_interval", ElementValue(output_value_interval))
        self.output_value = Element(self, "output_value", ElementValue(
            np.zeros(self._compute_input_value_shape(self.input_value.value)))
        )


    def c_update(self):
        self.output_value.value[:] = np.interp(
            self.input_value.value,
            self.input_value_interval.value,
            self.output_value_interval.value
        )
