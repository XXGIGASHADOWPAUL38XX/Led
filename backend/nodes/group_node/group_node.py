from __future__ import annotations
from backend.components.elements.parameters import SequenceElement
from collections.abc import Iterable
from backend.overrides.CNode import CNode

class GroupNode(CNode):
    """Own related processing nodes and expose their pipeline outputs.

    `nodes` contains child pipelines; `start()` starts `auto_start_nodes`.
    Grouping does not render or position nodes."""
    nodeName = 'GroupNode'
    is_group_node = True

    def __init__(self, nodes: Iterable[CNode] | None=None, auto_start_nodes: Iterable[CNode] | None=None, terminals: dict | None=None, alias: str | None=None) -> None:
        super().__init__(self.nodeName, terminals=terminals or {}, alias=alias)
        self.nodes = SequenceElement(self, 'nodes', list(nodes or []), register_in_node=False)
        self.auto_start_nodes = SequenceElement(self, 'auto_start_nodes', list(auto_start_nodes or []), register_in_node=False)

    def start(self):
        for node in self.auto_start_nodes:
            node.start()

    def close(self):
        for node in reversed(self.nodes.value):
            if node.parent is self:
                node.close()
        super().close()

    def set_nodes(self, nodes):
        """Concrete pipelines own their children; generic groups only reference nodes."""
        for node in nodes:
            node.parent = self
        self.nodes.value = nodes
