"""Point-sized signals with editable counts and validated source shapes."""
import numpy as np

from config import FREQ_BINS
from backend.components.elements.element_value import ElementValue
from backend.components.elements.parameters import DataElement, Parameter
from backend.overrides.CNode import CNode


class PointCountNode(CNode):
    def init_points(self, number_points, **inputs):
        self._point_inputs = {}
        self.input_shapes = {name: (0, *channels) for name, (_, channels) in inputs.items()}
        for name, (value, channels) in inputs.items():
            element = DataElement(self, name, ElementValue(value))
            vars(self)[name] = element
            self._point_inputs[name] = (element.value is None, channels)
        supplied = [vars(self)[name].value for name, (placeholder, _) in self._point_inputs.items() if not placeholder]
        if supplied and not np.shape(supplied[0]):
            raise ValueError("Point inputs must have a point axis")
        count = np.shape(supplied[0])[0] if supplied else FREQ_BINS
        self.number_points = Parameter(self, 'number_points', count if number_points is None else number_points,
                                       minimum=1, maximum=4096, integer=True)
        valid, error = self.number_points.check_value(self.number_points.value)
        if not valid:
            raise ValueError(error)
        for name, (placeholder, channels) in self._point_inputs.items():
            element = vars(self)[name]
            if placeholder:
                element.value = np.zeros((int(self.number_points.value), *channels))
            elif element._value_source is None:
                element.value = np.asarray(element.value)
            self.pending_terminals[name]['adaptiveShape'] = True
        PointCountNode.validate_parameters(self, {})

    def validate_parameters(self, changes):
        count = changes.get('number_points', self.number_points.value)
        for name, (placeholder, channels) in self._point_inputs.items():
            element = vars(self)[name]
            if not placeholder or element._value_source is not None:
                if np.shape(element.value) != (count, *channels):
                    raise ValueError(f'{name} shape {np.shape(element.value)} must match {count} points with trailing shape {channels}')
            if element.value.dtype.kind not in 'biuf':
                raise ValueError('Point inputs must be numeric arrays')

    def connect_input(self, name, source, parameters):
        if name in self._point_inputs:
            node = next(node for node in self.get_nodes() if node.name() == source['nodeId'])
            shape = np.shape(vars(node)[node.terminal_element_name(source['element'])].value)
            if not shape or shape[1:] != self._point_inputs[name][1]:
                raise ValueError(f'{name} requires trailing shape {self._point_inputs[name][1]}')
            parameters['number_points'] = shape[0]
            parameters.pop(name, None)
        return super().connect_input(name, source, parameters)

    def parameters_changed(self, name):
        if name == 'number_points':
            for field, (placeholder, channels) in self._point_inputs.items():
                element = vars(self)[field]
                if placeholder and element._value_source is None:
                    element.value = np.zeros((int(self.number_points.value), *channels))
            self.resize_points()

    def resize_points(self):
        self.data.value = np.zeros((int(self.number_points.value), *self.data.value.shape[1:]), dtype=self.data.value.dtype)
