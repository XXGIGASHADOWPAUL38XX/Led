"""Numeric array input with an editable shape that adapts on connection."""
import numpy as np

from backend.components.elements.element_value import ElementValue
from backend.components.elements.parameters import DataElement, Parameter, validate_shape
from backend.overrides.CNode import CNode


class ArrayInputNode(CNode):
    def init_array_input(self, name, value, shape, default_shape):
        self.array_input = name
        element = DataElement(self, name, ElementValue(value))
        vars(self)[name] = element
        self._placeholder = element.value is None
        inferred = default_shape if self._placeholder else np.shape(element.value)
        self.shape = Parameter(self, 'shape', validate_shape(inferred if shape is None else shape),
                               minimum=1, maximum=65536, integer=True)
        if self._placeholder:
            element.value = np.zeros(self.shape.value)
        elif element._value_source is None:
            element.value = np.asarray(element.value)
        self.pending_terminals[name]['adaptiveShape'] = True
        ArrayInputNode.validate_parameters(self, {})

    def validate_parameters(self, changes):
        shape = validate_shape(changes.get('shape', self.shape.value))
        element = vars(self)[self.array_input]
        if (not self._placeholder or element._value_source is not None) and np.shape(element.value) != shape:
            raise ValueError(f'Input shape {shape} is incompatible with input data {np.shape(element.value)}')
        if element.value.dtype.kind not in 'biuf':
            raise ValueError('Input must be a numeric array')

    def connect_input(self, name, source, parameters):
        if name == self.array_input:
            node = next(node for node in self.get_nodes() if node.name() == source['nodeId'])
            parameters['shape'] = validate_shape(np.shape(vars(node)[node.terminal_element_name(source['element'])].value))
            parameters.pop(name, None)
        return super().connect_input(name, source, parameters)

    def output_shape(self):
        return self.shape.value

    def parameters_changed(self, name):
        if name == 'shape':
            element = vars(self)[self.array_input]
            if self._placeholder and element._value_source is None:
                element.value = np.zeros(validate_shape(self.shape.value))
            self.data.value = np.zeros(self.output_shape())
