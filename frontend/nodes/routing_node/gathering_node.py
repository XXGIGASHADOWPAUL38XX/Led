from typing import List

import numpy as np

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class GatheringNode(CNode, AudioUpdatable):
    """Select enabled source values using a parallel boolean list.

    Configure nonempty `input_datas` and matching `input_booleans` as Elements;
    source Elements create named input terminals. Output `data` receives the
    enabled values each audio update and keeps its previous value if none
    are enabled. Selected values must fit the preallocated output shape."""

    nodeName = "Gathering"

    def __init__(
        self,
        input_datas: List[Element] = [],
        input_booleans: List[Element] = [],
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        self.input_datas = input_datas
        self.input_booleans = input_booleans
        terminals = {
            "data": {"io": "out"},
        }
        for data in self.input_datas:
            terminals[self.resolve_element_name(data)] = {"io": "in"}

        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.gathering_elements = self.init_data_and_booleans()
        self.data = AnalysableElement(self, "data",
                                      ElementValue(np.zeros_like(input_datas[0].value)))  ##!! wouldn't work for floats


    def c_update(self):
        values = np.array(list(map(lambda x: x.value, self.input_datas)))
        booleans = np.asarray(
            list(map(lambda y: y.value, self.input_booleans)),
            dtype=bool,
        ).flatten()
        true_elements = values[booleans]
        if true_elements.shape[0] > 0:
            self.data.value[:] = true_elements

    @staticmethod
    def resolve_element_name(element):
        node_name = getattr(element.node, "alias", None) or element.node.name()
        return f"{node_name}:{element.name}".lower()

    def init_data_and_booleans(self):
        elements = []

        for data in self.input_datas:
            name = self.resolve_element_name(data)
            element = Element(self, name, ElementValue(data))
            setattr(self, name, element)
            elements.append(element)

        return elements
