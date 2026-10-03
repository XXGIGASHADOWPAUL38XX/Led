from backend.updatable.updatable import VisualUpdatable
from frontend.overrides.CNode import CNode


class LineChartNode(CNode, VisualUpdatable):
    def __init__(self, node_name, terminals, render=True, parent=None, alias=None):
        CNode.__init__(self, node_name, terminals, render=render, parent=parent, alias=alias)
        VisualUpdatable.__init__(self)

    def c_update(self):
        return self.chart.c_update()
