from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue


class NodeSelector(Element):
    """An optional reference to another processing node's Element."""
    def __init__(self, node, name, value=None, selection_nodes=(), selection_elements=(), **kwargs):
        self.selection_nodes = ElementValue(selection_nodes)
        self.selection_elements = ElementValue(selection_elements)
        super().__init__(node, name, value, **kwargs)

    @property
    def selected_element(self):
        return self._value_source

    def set_default_element(self, element):
        self.value = element
