from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.overrides.array_input_node import ArrayInputNode

class ValueTransformerPipelineNode(ArrayInputNode, AudioPipeline):
    """Map numeric arrays between intervals while preserving their shape.

    Input `input_value` produces output `output_value` each audio update.
    Configure `input_value_interval` and `output_value_interval` in either direction;
    linear interpolation clamps out-of-range inputs to endpoint outputs.
    `shape` is editable and adopts the source shape on connection. Connected
    data must match that shape. Scalars become one-element arrays; vectors,
    RGB arrays, and higher dimensions retain their full shape."""

    nodeName = "ValueTransformer"

    def __init__(
            self,
            input_value: np.ndarray | None = None,
            output_value_interval: tuple[int | float, int | float] = (0, 1),
            input_value_interval: tuple[int | float, int | float] = (0, 1),
            alias: str | None = None,
            shape=None,
    ) -> None:
        terminals = {
            "input_value": {"io": "in"},
            "output_value": {"io": "out"},
        }

        super().__init__(node_name=self.nodeName, terminals=terminals, alias=alias)

        if np.isscalar(input_value):
            input_value = np.atleast_1d(input_value)
        self.init_array_input('input_value', input_value, shape, (1,), output_name='output_value')
        self.input_value_interval = Parameter(self, 'input_value_interval', input_value_interval, kind='interval')
        self.output_value_interval = Parameter(self, 'output_value_interval', output_value_interval, kind='interval')
        self.output_value = DataElement(self, 'output_value', np.zeros(self.shape.value))

    def c_update(self):
        inputs = self.input_value_interval.value
        outputs = self.output_value_interval.value
        if inputs[0] > inputs[1]:
            inputs, outputs = inputs[::-1], outputs[::-1]
        self.output_value.value[:] = np.interp(
            self.input_value.value,
            inputs,
            outputs
        )
