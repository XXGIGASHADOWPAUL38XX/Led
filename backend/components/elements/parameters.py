"""Typed processing parameters and generation constraints."""

import numpy as np

from backend.components.elements.element import Element


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
