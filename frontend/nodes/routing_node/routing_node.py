from frontend.components.elements.parameters import SequenceElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class RoutingNode(CNode):
    """Placeholder for routing a configured list of operator nodes.

    Configure `operator_nodes`; a `data` output terminal is declared, but no
    data Element or routing behavior is implemented. Do not use as a working
    signal source in generated templates."""

    nodeName = "Routing"

    def __init__(
        self,
        operator_nodes: list[CNode] | None = None,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.operator_nodes = SequenceElement(self, 'operator_nodes', ElementValue(operator_nodes or []))

    def c_update(self):
        pass
