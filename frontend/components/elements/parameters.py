"""Typed parameter rows; generation choices are built outside the UI."""

import numpy as np

from frontend.components.elements.dials import ExpDial, LinearDial
from frontend.components.elements.dropbox.dropbox import Dropbox
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue


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

    def _set_child_parent(self, value):
        # Membership in a collection does not embed or reparent its nodes.
        pass

    def build_value_widget(self, value, font):
        return super().build_value_widget(self.format_value(value), font)

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


class IntegerDial(LinearDial):
    """A linear dial whose UI always emits integer values."""

    def map_value(self, ratio):
        return int(round(super().map_value(ratio)))


class IntegerExpDial(ExpDial):
    """An exponential dial for positive integer counts."""

    def map_value(self, ratio):
        return int(round(super().map_value(ratio)))


class OptionalDial(LinearDial):
    """A numeric input which can retain an absent default or a source array."""

    def __init__(self, node, name, min_value, max_value, value=None, **kwargs):
        initial = value.value if isinstance(value, ElementValue) else value
        super().__init__(node, name, min_value, max_value, min_value if initial is None else value, **kwargs)
        if initial is None:
            self.value = None
            self.sync_controls()

    def to_dial(self):
        return 0 if self.value is None else super().to_dial()

    def check_value(self, value):
        return (True, None) if value is None else super().check_value(value)


class EnumElement(Dropbox):
    """Offer Enum members by name while retaining the actual Enum value."""

    def __init__(self, node, name, value, **kwargs):
        member = value.value if isinstance(value, ElementValue) else value
        self.enum_type = type(member)
        super().__init__(node, name, value, items=list(self.enum_type.__members__), **kwargs)
        self.combobox.blockSignals(True)
        self.combobox.setCurrentText(member.name)
        self.combobox.blockSignals(False)

    def on_item_changed(self, item):
        self.value = self.enum_type[item]


class AxisElement(Dropbox):
    """Typed reduction axes, including all axes and an existing tuple."""

    def __init__(self, node, name, value=0, **kwargs):
        axis = value.value if isinstance(value, ElementValue) else value
        self.choices = {str(item): item for item in (None, 0, axis)}
        super().__init__(node, name, value, items=list(self.choices), **kwargs)

    def on_item_changed(self, item):
        self.value = self.choices[item]
