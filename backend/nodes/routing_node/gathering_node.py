from backend.components.elements.parameters import DataElement, SequenceElement
from typing import List

import numpy as np

from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class GatheringNode(CNode, AudioUpdatable):
    """Select enabled source values using a parallel boolean list.

    Configure nonempty `input_datas` and matching `input_booleans` as Elements;
    source Elements create named input terminals. Output `data` receives the
    first enabled value each audio update and keeps its previous value if
    none are enabled. Sources must have matching shapes."""

    nodeName = "Gathering"

    def __init__(
        self,
        input_datas: List[Element] = [],
        input_booleans: List[Element] = [],
        alias: str | None = None,
    ) -> None:
        if len(input_datas) != len(input_booleans):
            raise ValueError("Provide one enable source per data source")
        terminals = {
            "data": {"io": "out"},
        }
        for data in input_datas:
            terminals[self.resolve_element_name(data)] = {"io": "in"}

        super().__init__(self.nodeName, terminals, alias=alias)

        self.input_datas = SequenceElement(self, "input_datas", input_datas, register_in_node=False)
        self.input_booleans = SequenceElement(self, "input_booleans", input_booleans, register_in_node=False)
        self.gathering_elements = self.init_data_and_booleans()
        self.enable_elements = []
        for index, source in enumerate(self.input_booleans):
            name = f'enabled_{index}'
            enabled = DataElement(self, name, source if source is not None else np.zeros(1))
            vars(self)[name] = enabled
            self.pending_terminals[name] = {'io': 'in'}
            self.enable_elements.append(enabled)
        self.data = AnalysableElement(self, "data",
                                      ElementValue(np.zeros_like(input_datas[0].value) if input_datas else np.zeros(0)))
        self.validate_parameters({})

    def validate_parameters(self, changes):
        if any(np.shape(source.value) != self.data.value.shape for source in self.gathering_elements):
            raise ValueError('Gathering sources must have matching shapes')
        if any(np.size(source.value) != 1 for source in self.enable_elements):
            raise ValueError('Gathering enable inputs must each provide one value')

    def c_update(self):
        for source, enabled in zip(self.gathering_elements, self.enable_elements):
            if np.asarray(enabled.value).item():
                self.data.value[:] = source.value
                return

    def connect_input(self, name, source, parameters):
        if name.startswith('enabled_'):
            parameters['input_booleans'][int(name.removeprefix('enabled_'))] = source
            return name, {}
        return super().connect_input(name, source, parameters)

    def disconnect_input(self, name, parameters):
        if name.startswith('enabled_'):
            parameters['input_booleans'][int(name.removeprefix('enabled_'))] = None
            return ()
        return super().disconnect_input(name, parameters)

    @staticmethod
    def resolve_element_name(element):
        return f"{element.node.name()}:{element.name}".lower()

    def init_data_and_booleans(self):
        elements = []

        for data in self.input_datas:
            name = self.resolve_element_name(data)
            element = DataElement(self, name, ElementValue(data))
            vars(self)[name] = element
            elements.append(element)

        return elements
