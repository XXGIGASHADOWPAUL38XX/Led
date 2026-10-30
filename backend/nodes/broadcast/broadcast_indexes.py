from backend.components.elements.parameters import ArrayElement, DataElement, Parameter, validate_shape
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import FREQ_BINS
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode


class BroadcastIndexesNode(CNode, AudioUpdatable):
    """Sample an array's first axis using normalized positions.

    Input `input_data` can be a vector or rows such as (180, 3) RGB colors.
    `indexes` in [0, 1] select rows; output `data` has shape
    indexes.shape + input_data.shape[1:]. `shape` describes the input:
    editable for an unconnected placeholder and required to match connected
    or authored input data exactly. Indexes are clamped.
    """

    nodeName = 'BroadcastIndexesNode'

    def __init__(self, input_data=None, indexes: np.ndarray = np.zeros(FREQ_BINS),
                 alias: str | None = None, shape=(FREQ_BINS,)):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'indexes': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self._placeholder = self.input_data.value is None
        self.shape = Parameter(self, 'shape', validate_shape(shape), minimum=1, maximum=65536, integer=True)
        if self._placeholder:
            self.input_data.value = np.zeros(validate_shape(self.shape.value))
        elif self.input_data._value_source is None:
            self.input_data.value = np.asarray(self.input_data.value)
        self.indexes = ArrayElement(self, 'indexes', ElementValue(indexes), min_value=0, max_value=1)
        self.validate_parameters({})
        self.data = AnalysableElement(self, 'data', np.zeros(self._output_shape()))
        self.current_indexes = np.empty(self.indexes.value.shape, dtype=np.intp)

    def validate_parameters(self, changes):
        shape = validate_shape(changes.get('shape', self.shape.value))
        data = changes.get('input_data', self.input_data.value)
        if (not self._placeholder or self.input_data._value_source is not None) and np.shape(data) != shape:
            raise ValueError(f'Input shape {shape} is incompatible with input data {np.shape(data)}')
        if self.input_data.value.ndim < 1 or self.input_data.value.dtype.kind not in 'iufb':
            raise ValueError('Input data must be a nonempty numeric array')

    def parameters_changed(self, name):
        if name == 'shape' and self._placeholder and self.input_data._value_source is None:
            self.input_data.value = np.zeros(validate_shape(self.shape.value))
        self._resize_data()

    def _output_shape(self):
        return self.indexes.value.shape + self.input_data.value.shape[1:]

    def _resize_data(self):
        shape = self._output_shape()
        if self.data.value.shape != shape:
            self.data.value = np.zeros(shape)
        if self.current_indexes.shape != self.indexes.value.shape:
            self.current_indexes = np.empty(self.indexes.value.shape, dtype=np.intp)

    def c_update(self):
        self._resize_data()
        size = self.input_data.value.shape[0]
        np.multiply(self.indexes.value, size, out=self.current_indexes, casting='unsafe')
        np.clip(self.current_indexes, 0, size - 1, out=self.current_indexes)
        self.data.value[...] = self.input_data.value[self.current_indexes]
