"""Typed processing parameters and generation constraints."""

import numpy as np

from backend.components.elements.element import Element


def validate_shape(shape, minimum=1):
    values = np.asarray(shape)
    if values.ndim != 1 or not 1 <= values.size <= 16 or values.dtype.kind not in 'iuf' or not np.isfinite(values).all() or np.any((values < minimum) | (values > 65536) | (values != np.floor(values))):
        raise ValueError(f'Input shape must contain 1–16 integer dimensions between {minimum} and 65536')
    dimensions = tuple(int(value) for value in values)
    if np.prod(dimensions, dtype=object) > 4_194_304:
        raise ValueError('Input shape exceeds 4,194,304 elements')
    return dimensions


class DataElement(Element):
    """Signal input/output: connect a source rather than author its samples."""

    @property
    def shape(self):
        return np.shape(self.value)

    @property
    def dtype(self):
        return np.asarray(self.value).dtype


class ArrayElement(DataElement):
    """Authored array; preserve its dtype and shape when building values."""

    def __init__(self, *args, min_value=None, max_value=None, builders=("constant", "ramp", "curve"), **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        self.builders = builders
        super().__init__(*args, **kwargs)


class SequenceElement(Element):
    """Ordered values or references, described recursively by the generator."""

    input_ports = ()

    def __iter__(self):
        return iter(self.value)

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def append(self, value):
        self.value.append(value)


class ReferenceElement(Element):
    """Embedded node, callback or object: use a registered builder/default."""


class NodeReferenceElement(ReferenceElement):
    """Optional processing node supplied by another graph node."""


class Parameter(Element):
    """Processing value with type and validation metadata; no widget behavior."""

    def __init__(self, node, name, value, *, kind="number", minimum=None, maximum=None,
                 integer=False, optional=False, choices=(), **kwargs):
        self.kind = kind
        self.minimum, self.maximum = minimum, maximum
        self.integer, self.optional = integer, optional
        self.choices = {str(item): item for item in choices}
        super().__init__(node, name, value, **kwargs)
        if kind == "enum":
            self.choices = dict(type(self.value).__members__)
        elif kind == "axis":
            if type(self.value) is list:
                self.value = tuple(self.value)
            self.choices = {str(item): item for item in (None, 0, self.value)}

    def check_value(self, value):
        if value is None:
            return (True, None) if self.optional or self.kind == "axis" else (False, "A value is required")
        if self.kind == "number":
            values = np.asarray(value)
            if values.dtype.kind not in "iuf" or not np.isfinite(values).all():
                return False, "Expected finite numbers"
            if self.integer and np.any(values != np.floor(values)):
                return False, "Expected an integer"
            if self.minimum is not None and np.any(values < self.minimum):
                return False, f"Value must be at least {self.minimum}"
            if self.maximum is not None and np.any(values > self.maximum):
                return False, f"Value must be at most {self.maximum}"
        elif self.kind == "boolean" and type(value) is not bool:
            return False, "Expected a boolean"
        elif self.kind == "text" and type(value) is not str:
            return False, "Expected text"
        elif self.kind in {"interval", "color"}:
            values = np.asarray(value)
            sizes = (2,) if self.kind == "interval" else (3, 4)
            if values.ndim != 1 or values.size not in sizes or values.dtype.kind not in "iuf" or not np.isfinite(values).all():
                return False, f"Invalid {self.kind} values"
            if self.kind == "color" and np.any((values < 0) | (values > 255)):
                return False, "Color channels must be between 0 and 255"
        elif self.kind in {"enum", "choice"} and value not in self.choices.values():
            return False, "Invalid choice"
        return True, None


class RGBParameter(Parameter):
    """RGB value with optional per-channel signal inputs in [0, 255]."""

    def __init__(self, node, name, value, channels):
        self.channels = []
        self.overrides = set()
        super().__init__(node, name, value, kind='color')
        valid, error = self.check_value(Element.value.fget(self))
        if not valid:
            raise ValueError(error)
        for index, (suffix, source) in enumerate(zip(('red', 'green', 'blue'), channels)):
            channel_name = f'{name}_{suffix}'
            channel = DataElement(node, channel_name, np.array([self.value[index]]) if source is None else source)
            if np.shape(channel.value) != (1,) or not np.isfinite(channel.value).all():
                raise ValueError('RGB channel inputs require one finite value')
            self.channels.append(channel)
            if source is not None:
                self.overrides.add(channel_name)
            vars(node)[channel_name] = channel
            node.pending_terminals[channel_name] = {'io': 'in'}

    @property
    def value(self):
        value = np.clip(np.array(Element.value.fget(self), dtype=float), 0, 255)
        for index, channel in enumerate(self.channels):
            if channel._value_source is not None or channel.name in self.overrides:
                value[index] = np.clip(channel.value[0], 0, 255)
        return value

    @value.setter
    def value(self, value):
        Element.value.fset(self, value)

    def connect(self, callback):
        self.valueChanged.connect(callback)
        for channel in self.channels:
            channel.valueChanged.connect(callback)

    def check_value(self, value):
        if np.shape(value) != (3,):
            return False, 'Expected three RGB channels'
        return super().check_value(value)
