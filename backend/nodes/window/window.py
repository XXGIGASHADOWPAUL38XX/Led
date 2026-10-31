from backend.components.elements.parameters import Parameter, DataElement, SequenceElement, validate_shape
import numpy as np
from config import FREQ_BINS

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode


class WindowNode(CNode, AudioUpdatable):
    """Keep recent array frames for temporal aggregation.

    `shape` is the editable input frame shape; `data` has shape
    (length, *shape), oldest to newest. Connected input must match exactly.
    Configure positive history `length`, initial `init_value`, and frame
    delay `offset`. Each update appends a frame and aggregates the history.
    Omitted shape preserves legacy constructor references and embedded windows.
    """

    nodeName = 'Window'

    def __init__(self, input_data=None, length=1, init_value=0.0, offset=0,
                 alias: str | None = None, parent: CNode | None = None, shape=None):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias, parent=parent)
        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self._placeholder = self.input_data.value is None
        inferred = (FREQ_BINS,) if self._placeholder else np.shape(self.input_data.value)
        self.shape = Parameter(self, 'shape', validate_shape(inferred if shape is None else shape, minimum=0), minimum=0, maximum=65536, integer=True)
        if self._placeholder:
            self.input_data.value = np.zeros(self.shape.value)
        elif self.input_data._value_source is None:
            self.input_data.value = np.asarray(self.input_data.value)
        self.length = Parameter(self, 'length', length, minimum=1, maximum=1000, integer=True)
        self.offset = Parameter(self, 'offset', offset, minimum=0, maximum=1000, integer=True)
        self.init_value = Parameter(self, 'init_value', init_value, minimum=-100, maximum=100)
        self._offset_buffer = []
        self.window_fcts = SequenceElement(self, 'window_fcts', [])
        self.validate_parameters({})
        self.data = AnalysableElement(self, 'data', np.full(self._history_shape(), float(init_value)))
        self.length.valueChanged.connect(self.on_length_change)

    def connect_input(self, name, source, parameters):
        if name == 'input_data':
            parameters['shape'] = self.shape.value
        return super().connect_input(name, source, parameters)

    def validate_parameters(self, changes):
        shape = validate_shape(changes.get('shape', self.shape.value), minimum=0)
        if (not self._placeholder or self.input_data._value_source is not None) and np.shape(self.input_data.value) != shape:
            raise ValueError(f'Input shape {shape} is incompatible with input data {np.shape(self.input_data.value)}')
        if self.input_data.value.dtype.kind not in 'iufb':
            raise ValueError('Window input data must be a numeric array')
        length = int(changes.get('length', self.length.value))
        if length * np.prod(shape, dtype=object) > 4_194_304:
            raise ValueError('Window history exceeds 4,194,304 elements')

    def _history_shape(self):
        return (int(self.length.value), *validate_shape(self.shape.value, minimum=0))

    def on_length_change(self, *_args):
        self._offset_buffer.clear()
        self.data.value = np.full(self._history_shape(), float(self.init_value.value))

    def parameters_changed(self, name):
        if name == 'shape':
            if self._placeholder and self.input_data._value_source is None:
                self.input_data.value = np.zeros(validate_shape(self.shape.value, minimum=0))
            self.on_length_change()
        elif name == 'offset':
            self._offset_buffer.clear()

    def c_update(self):
        offset = int(self.offset.value)
        if offset:
            self._offset_buffer.append(np.array(self.input_data.value))
            data = self._offset_buffer.pop(0) if len(self._offset_buffer) > offset else np.zeros_like(self.input_data.value)
        else:
            data = self.input_data.value
        self.roll(data)
        for window_fct in self.window_fcts.value:
            window_fct.aggregate(self.data.value)

    def roll(self, input_data):
        self.data.value[:] = np.roll(self.data.value, -1, axis=0)
        self.data.value[-1] = input_data
