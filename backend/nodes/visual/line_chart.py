from backend.updatable.updatable import VisualUpdatable
from backend.overrides.CNode import CNode

class LineChartNode(CNode, VisualUpdatable):
    """Base for numerical history buffers sampled during state updates."""

    def __init__(self, node_name, terminals, parent=None, alias=None):
        CNode.__init__(self, node_name, terminals, parent=parent, alias=alias)
