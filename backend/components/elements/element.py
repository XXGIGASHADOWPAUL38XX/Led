"""Plain processing values and live connections, independent of presentation."""
import numpy as np
from backend.components.elements.element_value import ElementValue
from backend.components.elements.signal import Signal


class ObservableArray(np.ndarray):
    def __new__(cls, array, on_mutation):
        result = np.asarray(array).view(cls)
        result._on_mutation = on_mutation
        return result

    def __array_finalize__(self, source):
        self._on_mutation = source._on_mutation if type(source) is ObservableArray else None

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self._on_mutation is not None:
            self._on_mutation()


class Element:
    def __init__(self, node, name, value, register_in_node=True):
        self.node, self.name = node, name
        self._value = None
        self._value_ref = value if isinstance(value, ElementValue) else None
        self._value_source = None
        self.valueChanged = Signal()
        self.value = value.value if self._value_ref is not None else value
        if register_in_node:
            node.elements.append(self)

    @property
    def value(self):
        return self._value_ref.value if self._value_ref is not None else self._value

    @value.setter
    def value(self, value):
        if self._value_source is not None:
            self._value_source.valueChanged.disconnect(self._forward_value_changed)
            self._value_source = None
            self._value_ref = None
        if isinstance(value, Element):
            self._value_source = value
            self._value_ref = value
            value.valueChanged.connect(self._forward_value_changed)
        else:
            self._value = ObservableArray(value, self._array_changed) if isinstance(value, np.ndarray) else value
            if self._value_ref is not None:
                self._value_ref.value = self._value
        self.valueChanged.emit(self.value)

    def _forward_value_changed(self, value):
        self.valueChanged.emit(value)

    def _array_changed(self):
        self.valueChanged.emit(self.value)

    def check_value(self, value):
        return True, None

    def close(self):
        if self._value_source is not None:
            self._value_source.valueChanged.disconnect(self._forward_value_changed)
            self._value_source = None
            self._value_ref = None
